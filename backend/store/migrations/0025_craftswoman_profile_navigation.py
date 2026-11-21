from django.db import migrations


def add_craftswoman_profile_navigation(apps, schema_editor):
    AccessRole = apps.get_model('store', 'AccessRole')
    NavigationItem = apps.get_model('store', 'NavigationItem')
    database = schema_editor.connection.alias

    role = AccessRole.objects.using(database).get(code='craftswoman')
    item = NavigationItem.objects.using(database).filter(route_name='craftswoman.profile').first()
    if item is None:
        item = NavigationItem.objects.using(database).create(
            label='Mi perfil',
            route_name='craftswoman.profile',
            description='Consulta y actualiza tu información personal y de taller.',
            order=40,
            active=True,
        )
    through = NavigationItem._meta.get_field('roles').remote_field.through
    through.objects.using(database).get_or_create(navigationitem_id=item.pk, accessrole_id=role.pk)


class Migration(migrations.Migration):
    dependencies = [('store', '0024_orderitem_assigned_at_orderitem_assigned_by_and_more')]

    operations = [
        migrations.RunPython(add_craftswoman_profile_navigation, migrations.RunPython.noop),
    ]
