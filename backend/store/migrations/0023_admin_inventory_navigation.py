from django.db import migrations


def add_inventory_navigation(apps, schema_editor):
    AccessRole = apps.get_model('store', 'AccessRole')
    NavigationItem = apps.get_model('store', 'NavigationItem')
    Resource = apps.get_model('store', 'RBACResource')
    Action = apps.get_model('store', 'RBACAction')
    Capability = apps.get_model('store', 'RBACCapability')
    database = schema_editor.connection.alias

    products_resource = Resource.objects.using(database).get(code='products')
    export_action = Action.objects.using(database).get(code='export')
    Capability.objects.using(database).get_or_create(resource=products_resource, action=export_action)

    if NavigationItem.objects.using(database).filter(route_name='admin.inventory').exists():
        return

    item = NavigationItem.objects.using(database).create(
        label='Inventario',
        route_name='admin.inventory',
        description='Consulta existencias y movimientos registrados.',
        order=25,
        active=True,
    )
    item.roles.set(AccessRole.objects.using(database).filter(code__in=('admin', 'superadmin')))


class Migration(migrations.Migration):
    dependencies = [('store', '0022_craftswoman_self_profile_permissions')]

    operations = [
        migrations.RunPython(add_inventory_navigation, migrations.RunPython.noop),
    ]
