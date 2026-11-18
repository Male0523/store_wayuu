from django.db import migrations


def grant_self_profile_access(apps, schema_editor):
    Role = apps.get_model('store', 'AccessRole')
    Capability = apps.get_model('store', 'RBACCapability')
    Grant = apps.get_model('store', 'RBACGrant')
    database = schema_editor.connection.alias
    role = Role.objects.using(database).get(code='craftswoman')

    for action_code in ('view', 'edit'):
        capability = Capability.objects.using(database).get(
            resource__code='craftswomen', action__code=action_code,
        )
        Grant.objects.using(database).get_or_create(
            role=role,
            capability=capability,
            defaults={'effect': 'allow'},
        )


class Migration(migrations.Migration):
    dependencies = [('store', '0021_product_image')]

    operations = [
        migrations.RunPython(grant_self_profile_access, migrations.RunPython.noop),
    ]
