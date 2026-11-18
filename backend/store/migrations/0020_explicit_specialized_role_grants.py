from django.db import migrations


ROLE_ACTIONS = {
    'admin': {
        'products': ('publish', 'unpublish'),
        'categories': ('publish', 'unpublish'),
        'orders': ('approve', 'cancel'),
    },
    'craftswoman': {
        'orders': ('assign',),
    },
}

FORBIDDEN_BASE_ROLE_ACTIONS = {
    'admin': {'orders': ('assign',)},
    'craftswoman': {
        'products': ('publish', 'unpublish'),
        'orders': ('approve', 'cancel'),
    },
}


def configure_explicit_specialized_role_grants(apps, schema_editor):
    Role = apps.get_model('store', 'AccessRole')
    Capability = apps.get_model('store', 'RBACCapability')
    Grant = apps.get_model('store', 'RBACGrant')
    RolePermission = apps.get_model('store', 'RolePermission')
    database = schema_editor.connection.alias

    for role_code, resources in FORBIDDEN_BASE_ROLE_ACTIONS.items():
        for resource_code, action_codes in resources.items():
            for action_code in action_codes:
                capability = Capability.objects.using(database).filter(
                    resource__code=resource_code,
                    action__code=action_code,
                ).first()
                if capability:
                    Grant.objects.using(database).filter(
                        role__code=role_code,
                        capability=capability,
                        effect='allow',
                    ).delete()
                model_name = {
                    'products': 'product',
                    'categories': 'category',
                    'orders': 'order',
                }[resource_code]
                permission_codename = f'{action_code}_{model_name}'
                RolePermission.objects.using(database).filter(
                    role__code=role_code,
                    permission__content_type__app_label='store',
                    permission__content_type__model=model_name,
                    permission__codename=permission_codename,
                ).delete()

    for role_code, resources in ROLE_ACTIONS.items():
        role = Role.objects.using(database).filter(code=role_code).first()
        if not role:
            continue
        for resource_code, action_codes in resources.items():
            for action_code in action_codes:
                capability = Capability.objects.using(database).filter(
                    resource__code=resource_code,
                    action__code=action_code,
                ).first()
                if capability:
                    Grant.objects.using(database).get_or_create(
                        role=role,
                        capability=capability,
                        defaults={'effect': 'allow'},
                    )


class Migration(migrations.Migration):
    dependencies = [('store', '0019_order_design_status_capability')]

    operations = [
        migrations.RunPython(
            configure_explicit_specialized_role_grants,
            migrations.RunPython.noop,
        ),
    ]
