from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from store.models import AccessRole, UserRole


class Command(BaseCommand):
    help = 'Reporta cuentas sin UserRole; asigna roles solo con confirmación explícita.'

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--dry-run', action='store_false', dest='apply')
        mode.add_argument('--apply', action='store_true', dest='apply')
        parser.set_defaults(apply=False)
        parser.add_argument(
            '--assign',
            action='append',
            default=[],
            metavar='USER_ID:ROLE',
            help='Asignación explícita; puede repetirse. Roles: customer, craftswoman, admin, superadmin.',
        )
        parser.add_argument(
            '--confirm-user',
            action='append',
            type=int,
            default=[],
            metavar='USER_ID',
            help='Confirma individualmente cada ID cuando se usa --apply.',
        )

    def handle(self, *args, **options):
        assignments = self.parse_assignments(options['assign'])
        confirmed_ids = set(options['confirm_user'])
        apply_changes = options['apply']

        if apply_changes and not assignments:
            raise CommandError('--apply requiere al menos una opción --assign USER_ID:ROLE.')
        if not apply_changes and confirmed_ids:
            raise CommandError('--confirm-user solo se permite junto con --apply.')

        users_without_role = User.objects.filter(access_profile__isnull=True).order_by('id')
        self.stdout.write(f'Cuentas sin UserRole: {users_without_role.count()}')
        for user in users_without_role.iterator():
            self.stdout.write(f'ID={user.pk} username={user.get_username()}')

        if not assignments:
            self.stdout.write('No se modificaron cuentas.')
            return

        users = {}
        for user_id, role_code in assignments.items():
            user = User.objects.filter(pk=user_id).first()
            if user is None:
                raise CommandError(f'No existe la cuenta con ID={user_id}.')
            role = AccessRole.objects.filter(code=role_code).first()
            if role is None:
                valid_roles = ', '.join(AccessRole.Code.values)
                raise CommandError(f'Rol desconocido "{role_code}". Roles válidos: {valid_roles}.')
            current = UserRole.objects.filter(user=user).select_related('role').first()
            current_code = current.role.code if current else 'sin rol'
            users[user_id] = (user, role, current_code)
            self.stdout.write(
                f'PROPUESTA: ID={user_id} username={user.get_username()} '
                f'{current_code} -> {role.code}'
            )

        if not apply_changes:
            self.stdout.write('Dry-run completado; no se modificaron cuentas.')
            return

        requested_ids = set(users)
        if confirmed_ids != requested_ids:
            missing = ', '.join(str(user_id) for user_id in sorted(requested_ids - confirmed_ids))
            extra = ', '.join(str(user_id) for user_id in sorted(confirmed_ids - requested_ids))
            raise CommandError(
                f'Confirma exactamente cada ID asignado con --confirm-user. Faltan: [{missing}]; sobrantes: [{extra}].'
            )

        self.stdout.write('Aplicando únicamente las asignaciones explícitas y confirmadas.')
        with transaction.atomic():
            for user, role, _ in users.values():
                UserRole.objects.update_or_create(user=user, defaults={'role': role})
        self.stdout.write(self.style.SUCCESS(f'{len(users)} asignación(es) guardada(s).'))

    @staticmethod
    def parse_assignments(values):
        assignments = {}
        for value in values:
            try:
                raw_id, role_code = value.split(':', 1)
                user_id = int(raw_id)
            except (ValueError, TypeError):
                raise CommandError(f'Formato inválido "{value}"; usa USER_ID:ROLE.') from None
            if user_id in assignments:
                raise CommandError(f'La cuenta ID={user_id} aparece más de una vez.')
            assignments[user_id] = role_code
        return assignments