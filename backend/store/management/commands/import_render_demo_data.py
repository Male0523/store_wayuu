from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from store.models import (
    AccessRole,
    AuditEvent,
    Category,
    Craftswoman,
    Customer,
    CustomerCartItem,
    CustomDesign,
    NavigationItem,
    Order,
    OrderItem,
    PermissionDelegation,
    Product,
    RolePermission,
    UserPermissionGrant,
    UserRole,
)


class Command(BaseCommand):
    help = (
        "Importa un fixture de demo en una base PostgreSQL de producción recién creada, "
        "reemplazando únicamente los registros iniciales de RBAC sembrados por las migraciones."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            required=True,
            help="Ruta absoluta del JSON exportado con dumpdata. Mantén este archivo fuera de Git.",
        )

    def handle(self, *args, **options):
        if getattr(settings, "DJANGO_ENV", "") != "production":
            raise CommandError("Por seguridad, este comando solo se permite con DJANGO_ENV=production.")

        if connection.vendor != "postgresql":
            raise CommandError("La importación solo se permite en PostgreSQL; no se modificará SQLite.")

        fixture_path = Path(options["fixture"]).expanduser().resolve()
        if not fixture_path.is_file():
            raise CommandError(f"No se encontró el archivo fixture: {fixture_path}")

        repository_root = settings.BASE_DIR.parent.resolve()
        if fixture_path.is_relative_to(repository_root):
            raise CommandError(
                "El fixture debe permanecer fuera del repositorio para evitar publicar datos personales."
            )

        User = get_user_model()

        # Las migraciones crean roles, permisos base y elementos de menú. Se aplican
        # primero y luego se sustituyen esos registros semilla por los del fixture.
        call_command("migrate", interactive=False, verbosity=0)

        existing_business_data = {
            "usuarios": User.objects.exists(),
            "tejedoras": Craftswoman.objects.exists(),
            "clientes": Customer.objects.exists(),
            "categorias": Category.objects.exists(),
            "productos": Product.objects.exists(),
            "pedidos": Order.objects.exists(),
            "detalles de pedido": OrderItem.objects.exists(),
            "auditoría": AuditEvent.objects.exists(),
            "diseños": CustomDesign.objects.exists(),
            "carritos": CustomerCartItem.objects.exists(),
            "delegaciones": PermissionDelegation.objects.exists(),
            "permisos individuales": UserPermissionGrant.objects.exists(),
        }
        populated = [name for name, exists in existing_business_data.items() if exists]
        if populated:
            raise CommandError(
                "La base destino ya contiene datos de negocio y no se tocará: "
                + ", ".join(populated)
                + ". Esta importación está diseñada para una base nueva."
            )

        with transaction.atomic():
            # Elimina solo los registros de arranque generados por las migraciones.
            # La transacción revierte estas eliminaciones si loaddata falla.
            NavigationItem.objects.all().delete()
            UserRole.objects.all().delete()
            RolePermission.objects.all().delete()
            AccessRole.objects.all().delete()

            call_command("loaddata", str(fixture_path), verbosity=1)

            expected_counts = {
                "usuarios": (User.objects.count(), 13),
                "roles": (AccessRole.objects.count(), 4),
                "asignaciones de rol": (UserRole.objects.count(), 13),
                "tejedoras": (Craftswoman.objects.count(), 6),
                "clientes": (Customer.objects.count(), 4),
                "categorías": (Category.objects.count(), 1),
                "productos": (Product.objects.count(), 8),
                "pedidos": (Order.objects.count(), 1),
                "detalles de pedido": (OrderItem.objects.count(), 3),
                "carritos": (CustomerCartItem.objects.count(), 2),
                "permisos de roles": (RolePermission.objects.count(), 31),
                "elementos de navegación": (NavigationItem.objects.count(), 16),
                "eventos de auditoría": (AuditEvent.objects.count(), 36),
            }
            mismatches = [
                f"{name}: esperados {expected}, encontrados {actual}"
                for name, (actual, expected) in expected_counts.items()
                if actual != expected
            ]
            if mismatches:
                raise CommandError(
                    "La importación no coincide con el respaldo verificado; se revertirá: "
                    + "; ".join(mismatches)
                )

        self.stdout.write(self.style.SUCCESS("Importación completada correctamente."))
        self.stdout.write(f"Usuarios: {User.objects.count()}")
        self.stdout.write(f"Roles: {AccessRole.objects.count()}")
        self.stdout.write(f"Tejedoras: {Craftswoman.objects.count()}")
        self.stdout.write(f"Clientes: {Customer.objects.count()}")
        self.stdout.write(f"Productos: {Product.objects.count()}")
        self.stdout.write(f"Pedidos: {Order.objects.count()}")
        self.stdout.write(f"Permisos de roles: {RolePermission.objects.count()}")
        self.stdout.write(f"Elementos de navegación: {NavigationItem.objects.count()}")
