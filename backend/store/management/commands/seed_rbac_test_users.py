import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils.text import slugify

from store.models import AccessRole, Craftswoman, Customer, UserRole


ACCOUNTS = (
    ('Maleja', AccessRole.Code.SUPERADMIN),
    ('Oscar', AccessRole.Code.ADMIN),
    ('Matthew', AccessRole.Code.ADMIN),
    ('Dayana', AccessRole.Code.CRAFTSWOMAN),
    ('Thania', AccessRole.Code.CRAFTSWOMAN),
    ('Zharik', AccessRole.Code.CRAFTSWOMAN),
    ('Sarith', AccessRole.Code.CRAFTSWOMAN),
    ('Ana', AccessRole.Code.CRAFTSWOMAN),
    ('Gabriel', AccessRole.Code.CUSTOMER),
    ('Sneider', AccessRole.Code.CUSTOMER),
    ('Carmen', AccessRole.Code.CUSTOMER),
    ('Cleotilde', AccessRole.Code.CUSTOMER),
)


def account_data(name, role_code):
    username = f'{slugify(name)}.{role_code}'
    return {
        'name': name,
        'role_code': role_code,
        'username': username,
        'email': f'{username}@store-wayuu-test.example.invalid',
        'password': f'{name[0].upper()}{name[1:].lower()}12345',
    }


class Command(BaseCommand):
    help = 'Crea cuentas RBAC de prueba en wayuu_dev; usa --dry-run por defecto.'

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--dry-run', action='store_false', dest='apply')
        mode.add_argument('--apply', action='store_true', dest='apply')
        parser.set_defaults(apply=False)

    def handle(self, *args, **options):
        self.assert_local_database()
        apply_changes = options['apply']
        role_rows = {role.code: role for role in AccessRole.objects.all()}
        expected_counts = {
            AccessRole.Code.SUPERADMIN: 1,
            AccessRole.Code.ADMIN: 2,
            AccessRole.Code.CRAFTSWOMAN: 5,
            AccessRole.Code.CUSTOMER: 4,
        }
        planned_counts = {code: sum(role == code for _, role in ACCOUNTS) for code in expected_counts}
        if planned_counts != expected_counts:
            raise CommandError('La distribución interna de cuentas de prueba no coincide con la especificada.')
        missing_roles = sorted(set(expected_counts) - set(role_rows))
        if missing_roles:
            raise CommandError(f'Faltan roles persistidos requeridos: {", ".join(missing_roles)}.')

        plans = [self.inspect_account(account_data(name, role_code), role_rows[role_code]) for name, role_code in ACCOUNTS]
        self.stdout.write('Destino verificado: PostgreSQL local 127.0.0.1 / wayuu_dev.')
        self.stdout.write('Resumen: 1 superadmin, 2 admin, 5 tejedoras activas, 4 clientes.')
        for plan in plans:
            self.stdout.write(f'{plan["status"]}: {plan["username"]} | {plan["name"]} | {plan["role_name"]}')

        conflicts = [plan for plan in plans if plan['conflict']]
        if conflicts:
            details = '; '.join(f'{plan["username"]}: {plan["conflict"]}' for plan in conflicts)
            if apply_changes:
                raise CommandError(f'Hay conflictos; no se modificó ninguna cuenta: {details}')
            self.stdout.write(self.style.WARNING(f'Conflictos detectados; dry-run no modificó cuentas: {details}'))
            return

        new_accounts = [plan['data'] for plan in plans if plan['status'] == 'CREAR']
        if not apply_changes:
            self.stdout.write('Dry-run: no se crearon ni modificaron usuarios.')
            return
        if not new_accounts:
            self.stdout.write('Las 12 cuentas ya existen con sus roles/perfiles correctos; no se modificó ninguna.')
            return

        credentials_path = Path(settings.BASE_DIR) / '.local' / 'rbac-test-users.json'
        staged_credentials = self.stage_credentials(credentials_path, new_accounts)
        try:
            with transaction.atomic():
                for data in new_accounts:
                    user = User.objects.create_user(
                        username=data['username'],
                        email=data['email'],
                        password=data['password'],
                        first_name=data['name'],
                        is_staff=False,
                        is_superuser=False,
                    )
                    if data['role_code'] == AccessRole.Code.CRAFTSWOMAN:
                        Craftswoman.objects.create(user=user, name=data['name'], active=True)
                    elif data['role_code'] == AccessRole.Code.CUSTOMER:
                        Customer.objects.create(user=user, name=data['name'], email=data['email'])
                    UserRole.objects.create(user=user, role=role_rows[data['role_code']])
                os.replace(staged_credentials, credentials_path)
                os.chmod(credentials_path, 0o600)
        except Exception as error:
            if os.path.exists(staged_credentials):
                os.unlink(staged_credentials)
            if credentials_path.exists() and credentials_path.is_symlink():
                raise CommandError('La ruta local de credenciales no puede ser un enlace simbólico.') from error
            raise CommandError(
                'Falló la creación o el guardado local de credenciales; consulta el error subyacente antes de reintentar.'
            ) from error

        self.stdout.write(self.style.SUCCESS(f'{len(new_accounts)} cuentas creadas en wayuu_dev.'))
        self.stdout.write(f'Credenciales guardadas localmente con modo 0600: {credentials_path}')
        self.stdout.write('No se imprimieron contraseñas; las cuentas existentes no se sobrescribieron.')

    @staticmethod
    def assert_local_database():
        if os.environ.get('DATABASE_URL'):
            raise CommandError('DATABASE_URL está prohibida; solo se permite DEV_DATABASE_URL local.')
        test_database = connection.settings_dict
        test_name = str(test_database.get('NAME', ''))
        if (
            'test' in sys.argv
            and test_database.get('ENGINE', '').endswith('sqlite3')
            and (test_name == ':memory:' or 'mode=memory' in test_name)
        ):
            return
        if getattr(settings, 'DJANGO_ENV', None) != 'development':
            raise CommandError('Se requiere DJANGO_ENV=development.')
        if getattr(settings, 'DB_ENGINE', None) != 'postgresql':
            raise CommandError('Se requiere DB_ENGINE=postgresql para wayuu_dev.')
        config = settings.DATABASES['default']
        if config['ENGINE'] != 'django.db.backends.postgresql':
            raise CommandError('La conexión Django no es PostgreSQL.')
        if config['HOST'] not in ('localhost', '127.0.0.1', '::1') or config['NAME'] != 'wayuu_dev':
            raise CommandError('Destino rechazado: se requiere host loopback y base wayuu_dev.')
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database(), current_user')
            database, user = cursor.fetchone()
        if database != 'wayuu_dev' or user != 'wayuu_dev':
            raise CommandError('El servidor PostgreSQL no confirma identidad local wayuu_dev.')

    @staticmethod
    def inspect_account(data, role):
        plan = {
            'data': data,
            'name': data['name'],
            'username': data['username'],
            'role_name': role.name,
            'status': 'CREAR',
            'conflict': '',
        }
        usernames = list(User.objects.filter(username__iexact=data['username']))
        email_users = list(User.objects.filter(email__iexact=data['email']))
        if len(usernames) > 1 or len(email_users) > 1:
            plan.update(status='CONFLICTO', conflict='username/email ambiguos')
            return plan
        existing = usernames[0] if usernames else None
        if email_users and (existing is None or email_users[0].pk != existing.pk):
            plan.update(status='CONFLICTO', conflict='correo ya pertenece a otra cuenta')
            return plan

        name_users = User.objects.filter(first_name__iexact=data['name'])
        if existing:
            name_users = name_users.exclude(pk=existing.pk)
        if name_users.exists():
            plan.update(status='CONFLICTO', conflict='nombre ya pertenece a otro usuario')
            return plan

        craft_profiles = Craftswoman.objects.filter(name__iexact=data['name'])
        customer_profiles = Customer.objects.filter(name__iexact=data['name'])
        if existing:
            craft_profiles = craft_profiles.exclude(user_id=existing.pk)
            customer_profiles = customer_profiles.exclude(user_id=existing.pk)
        if craft_profiles.exists() or customer_profiles.exists():
            plan.update(status='CONFLICTO', conflict='nombre ya pertenece a otro perfil')
            return plan

        email_profiles = Customer.objects.filter(email__iexact=data['email'])
        if existing:
            email_profiles = email_profiles.exclude(user_id=existing.pk)
        if email_profiles.exists():
            plan.update(status='CONFLICTO', conflict='correo ya pertenece a otro perfil de cliente')
            return plan

        if existing is None:
            return plan

        assignment = UserRole.objects.filter(user=existing).select_related('role').first()
        if (
            existing.first_name != data['name']
            or existing.email.casefold() != data['email'].casefold()
            or assignment is None
            or assignment.role.code != data['role_code']
        ):
            plan.update(status='CONFLICTO', conflict='cuenta existente no coincide; no se sobrescribe')
            return plan
        if data['role_code'] == AccessRole.Code.CRAFTSWOMAN:
            profile = Craftswoman.objects.filter(user=existing).first()
            if profile is None or profile.name != data['name'] or not profile.active:
                plan.update(status='CONFLICTO', conflict='perfil de tejedora existente no coincide o está inactivo')
                return plan
        elif data['role_code'] == AccessRole.Code.CUSTOMER:
            profile = Customer.objects.filter(user=existing).first()
            if profile is None or profile.name != data['name'] or profile.email.casefold() != data['email'].casefold():
                plan.update(status='CONFLICTO', conflict='perfil de cliente existente no coincide')
                return plan
        plan.update(status='SIN CAMBIOS', conflict='')
        return plan

    @staticmethod
    def stage_credentials(credentials_path, new_accounts):
        if credentials_path.is_symlink():
            raise CommandError('La ruta local de credenciales no puede ser un enlace simbólico.')
        directory = credentials_path.parent
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(directory, 0o700)

        existing_entries = []
        if credentials_path.exists():
            os.chmod(credentials_path, 0o600)
            try:
                existing_entries = json.loads(credentials_path.read_text(encoding='utf-8')).get('accounts', [])
            except (OSError, json.JSONDecodeError, AttributeError) as error:
                raise CommandError('El archivo local de credenciales existente no es válido; no se sobrescribirá.') from error
        entries_by_username = {entry['username']: entry for entry in existing_entries}
        for data in new_accounts:
            current = entries_by_username.get(data['username'])
            if current and current.get('password') != data['password']:
                raise CommandError('El archivo local ya contiene credenciales distintas para una cuenta a crear.')
            entries_by_username[data['username']] = {
                'name': data['name'],
                'username': data['username'],
                'email': data['email'],
                'role': data['role_code'],
                'password': data['password'],
            }

        descriptor, temporary_path = tempfile.mkstemp(prefix='.rbac-test-users-', suffix='.tmp', dir=directory)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as credentials_file:
                json.dump(
                    {'scope': 'solo desarrollo local; no usar en producción', 'accounts': list(entries_by_username.values())},
                    credentials_file,
                    ensure_ascii=False,
                    indent=2,
                )
                credentials_file.write('\n')
                credentials_file.flush()
                os.fsync(credentials_file.fileno())
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
        return temporary_path