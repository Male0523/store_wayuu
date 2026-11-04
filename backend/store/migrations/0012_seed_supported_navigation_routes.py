from django.db import migrations


def seed_supported_navigation_routes(apps, schema_editor):
    AccessRole = apps.get_model('store', 'AccessRole')
    NavigationItem = apps.get_model('store', 'NavigationItem')

    definitions = (
        # Cliente: estas tres opciones alimentan las pestañas configurables de “Mi cuenta”.
        ('Mis pedidos', 'customer.orders', 'Consulta el historial y el estado de tus compras.', 10, ('customer',)),
        ('Mis diseños', 'customer.designs', 'Consulta tus mantas personalizadas y su estado.', 20, ('customer',)),
        ('Mi perfil', 'customer.profile', 'Consulta y actualiza tus datos personales.', 30, ('customer',)),
        # Tejedora.
        ('Panel principal', 'craftswoman.dashboard', 'Resumen del taller, productos y pedidos asignados.', 10, ('craftswoman',)),
        ('Mis productos', 'craftswoman.products', 'Registra y consulta las piezas de tu taller.', 20, ('craftswoman',)),
        ('Inventario', 'craftswoman.inventory', 'Consulta las existencias de tus productos.', 30, ('craftswoman',)),
        ('Mis pedidos', 'craftswoman.orders', 'Consulta los pedidos relacionados con tu taller.', 40, ('craftswoman',)),
        # Administración de tienda y superadministración.
        ('Panel principal', 'admin.dashboard', 'Resumen de la operación comercial.', 10, ('admin', 'superadmin')),
        ('Productos', 'admin.products', 'Revisa y administra los productos de la tienda.', 20, ('admin', 'superadmin')),
        ('Pedidos', 'admin.orders', 'Consulta y gestiona los pedidos de clientes.', 30, ('admin', 'superadmin')),
        ('Categorías', 'admin.categories', 'Organiza las categorías del catálogo.', 40, ('admin', 'superadmin')),
    )

    for label, route_name, description, order, role_codes in definitions:
        item = NavigationItem.objects.filter(route_name=route_name).order_by('pk').first()
        if item is None:
            item = NavigationItem.objects.create(
                label=label,
                route_name=route_name,
                description=description,
                order=order,
                active=True,
            )
        else:
            # No sobrescribir nombres, visibilidad ni orden que el superadmin ya configuró.
            if not item.description:
                item.description = description
                item.save(update_fields=['description'])
        item.roles.set(AccessRole.objects.filter(code__in=role_codes))


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_userpermissiongrant_delegation'),
    ]

    operations = [
        migrations.RunPython(seed_supported_navigation_routes, migrations.RunPython.noop),
    ]
