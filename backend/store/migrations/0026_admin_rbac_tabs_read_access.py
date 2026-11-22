from django.db import migrations


ADMIN_TAB_READ_CAPABILITIES = (
    ('roles', 'view'),
    ('users', 'view'),
    ('navigation', 'view'),
    ('permissions', 'view'),
    ('audit', 'view'),
)


def grant_admin_tab_read_access(apps, schema_editor):
    AccessRole = apps.get_model('store', 'AccessRole')
    RBACCapability = apps.get_model('store', 'RBACCapability')
    RBACGrant = apps.get_model('store', 'RBACGrant')
    NavigationItem = apps.get_model('store', 'NavigationItem')
    database = schema_editor.connection.alias

    admin_role = AccessRole.objects.using(database).filter(code='admin', active=True).first()
    if admin_role is None:
        return

    for resource_code, action_code in ADMIN_TAB_READ_CAPABILITIES:
        capability = RBACCapability.objects.using(database).filter(
            resource__code=resource_code,
            action__code=action_code,
            resource__active=True,
            action__active=True,
        ).first()
        if capability is not None:
            RBACGrant.objects.using(database).get_or_create(
                role=admin_role,
                capability=capability,
                defaults={'effect': 'allow'},
            )

    access_item = NavigationItem.objects.using(database).filter(route_name='admin.access').first()
    if access_item is not None:
        through = NavigationItem._meta.get_field('roles').remote_field.through
        through.objects.using(database).get_or_create(
            navigationitem_id=access_item.pk,
            accessrole_id=admin_role.pk,
        )


class Migration(migrations.Migration):
    dependencies = [('store', '0025_craftswoman_profile_navigation')]

    operations = [
        migrations.RunPython(grant_admin_tab_read_access, migrations.RunPython.noop),
    ]
