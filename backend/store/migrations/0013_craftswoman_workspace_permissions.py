from django.db import migrations


def grant_craftswoman_workspace_permissions(apps, schema_editor):
    AccessRole = apps.get_model('store', 'AccessRole')
    RolePermission = apps.get_model('store', 'RolePermission')
    Permission = apps.get_model('auth', 'Permission')

    role = AccessRole.objects.filter(code='craftswoman').first()
    if not role:
        return

    permission_codenames = (
        'view_product', 'add_product', 'change_product',
        'view_order', 'change_order',
        'view_customdesign', 'change_customdesign',
    )
    permissions = Permission.objects.filter(
        content_type__app_label='store',
        codename__in=permission_codenames,
    )
    for permission in permissions:
        RolePermission.objects.get_or_create(role=role, permission=permission)


def revoke_craftswoman_workspace_permissions(apps, schema_editor):
    AccessRole = apps.get_model('store', 'AccessRole')
    RolePermission = apps.get_model('store', 'RolePermission')
    Permission = apps.get_model('auth', 'Permission')

    role = AccessRole.objects.filter(code='craftswoman').first()
    if not role:
        return
    permissions = Permission.objects.filter(
        content_type__app_label='store',
        codename__in=(
            'view_product', 'add_product', 'change_product',
            'view_order', 'change_order',
            'view_customdesign', 'change_customdesign',
        ),
    )
    RolePermission.objects.filter(role=role, permission__in=permissions).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0012_persistent_customer_cart'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            grant_craftswoman_workspace_permissions,
            revoke_craftswoman_workspace_permissions,
        ),
    ]
