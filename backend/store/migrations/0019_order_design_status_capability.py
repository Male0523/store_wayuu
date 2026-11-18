from django.db import migrations


def seed_order_design_status_capability(apps, schema_editor):
    Resource = apps.get_model('store', 'RBACResource')
    Action = apps.get_model('store', 'RBACAction')
    Capability = apps.get_model('store', 'RBACCapability')
    Grant = apps.get_model('store', 'RBACGrant')
    Role = apps.get_model('store', 'AccessRole')
    database = schema_editor.connection.alias

    resource = Resource.objects.using(database).get(code='orders')
    action, _ = Action.objects.using(database).get_or_create(
        code='manage_design_status',
        defaults={
            'name': 'Gestionar estado de diseños desde pedidos',
            'description': 'Permite sincronizar el estado de un diseño personalizado al cambiar el estado de su pedido.',
            'active': True,
        },
    )
    capability, _ = Capability.objects.using(database).get_or_create(
        resource=resource,
        action=action,
    )
    admin_role = Role.objects.using(database).filter(code='admin', active=True).first()
    if admin_role:
        Grant.objects.using(database).get_or_create(
            role=admin_role,
            capability=capability,
            defaults={'effect': 'allow'},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0018_category_internal'),
    ]

    operations = [
        migrations.RunPython(seed_order_design_status_capability, migrations.RunPython.noop),
    ]
