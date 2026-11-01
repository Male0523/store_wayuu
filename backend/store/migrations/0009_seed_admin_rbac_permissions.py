from django.db import migrations


ROLE_BASELINE_PERMISSIONS = {
    'admin': {
        'product': ('view_product', 'add_product', 'change_product'),
        'category': ('view_category', 'add_category', 'change_category'),
        'order': ('view_order', 'change_order'),
    },
    'customer': {
        'customer': ('view_customer', 'change_customer'),
        'order': ('view_order', 'add_order'),
        'customdesign': ('view_customdesign', 'add_customdesign'),
        'order_cart': ('view_cart', 'add_cart', 'change_cart', 'delete_cart'),
    },
    'craftswoman': {
        'order': ('view_order', 'change_order'),
        'customdesign': ('view_customdesign', 'change_customdesign'),
    },
}


def seed_admin_permissions(apps, schema_editor):
    AccessRole = apps.get_model('store', 'AccessRole')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    RolePermission = apps.get_model('store', 'RolePermission')
    database = schema_editor.connection.alias
    for role_code, resources in ROLE_BASELINE_PERMISSIONS.items():
        role = AccessRole.objects.using(database).filter(code=role_code, active=True).first()
        if not role:
            continue
        for model_key, codenames in resources.items():
            model = 'order' if model_key == 'order_cart' else model_key
            content_type, _ = ContentType.objects.using(database).get_or_create(
                app_label='store',
                model=model,
            )
            for codename in codenames:
                permission, _ = Permission.objects.using(database).get_or_create(
                    content_type=content_type,
                    codename=codename,
                    defaults={'name': codename.replace('_', ' ').capitalize()},
                )
                RolePermission.objects.using(database).get_or_create(
                    role=role,
                    permission=permission,
                )


def remove_admin_permissions(apps, schema_editor):
    RolePermission = apps.get_model('store', 'RolePermission')
    database = schema_editor.connection.alias
    for role_code, resources in ROLE_BASELINE_PERMISSIONS.items():
        RolePermission.objects.using(database).filter(
            role__code=role_code,
            permission__content_type__app_label='store',
            permission__codename__in=tuple(
                codename
                for codenames in resources.values()
                for codename in codenames
            ),
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0008_accessrole_active_auditevent_permissiondelegation_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_admin_permissions, remove_admin_permissions),
    ]