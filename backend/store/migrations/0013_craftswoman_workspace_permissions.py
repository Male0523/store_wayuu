from django.db import migrations


def grant_craftswoman_workspace_permissions(apps, schema_editor):
    AccessRole = apps.get_model('store', 'AccessRole')
    RolePermission = apps.get_model('store', 'RolePermission')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    role = AccessRole.objects.filter(code='craftswoman').first()
    if not role:
        return

    permissions_by_model = {
        'product': ('view_product', 'add_product', 'change_product'),
        'order': ('view_order', 'change_order'),
        'customdesign': ('view_customdesign', 'change_customdesign'),
    }
    for model_name, codenames in permissions_by_model.items():
        content_type, _ = ContentType.objects.get_or_create(
            app_label='store',
            model=model_name,
        )
        for codename in codenames:
            Permission.objects.get_or_create(
                content_type=content_type,
                codename=codename,
                defaults={'name': codename.replace('_', ' ').title()},
            )
            permission = Permission.objects.get(content_type=content_type, codename=codename)
            RolePermission.objects.get_or_create(role=role, permission=permission)


def reverse_craftswoman_workspace_permissions(apps, schema_editor):
    # Keep any role-permission adjustments made after this migration.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0012_persistent_customer_cart'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            grant_craftswoman_workspace_permissions,
            reverse_craftswoman_workspace_permissions,
        ),
    ]
