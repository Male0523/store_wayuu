from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from .models import (
    AccessRole,
    AuditEvent,
    PermissionDelegation,
    RBACAction,
    RBACCapability,
    RBACGrant,
    RBACRecordScopeGrant,
    RBACResource,
    RolePermission,
    UserPermissionGrant,
    UserRole,
)


PERMISSION_RESOURCES = {
    'cart': ('store', 'order'),
    'favorites': ('store', 'customerfavorite'),
    'products': ('store', 'product'),
    'categories': ('store', 'category'),
    'orders': ('store', 'order'),
    'designs': ('store', 'customdesign'),
    'craftswomen': ('store', 'craftswoman'),
    'customers': ('store', 'customer'),
    'users': ('auth', 'user'),
    'roles': ('store', 'accessrole'),
    'role_assignments': ('store', 'userrole'),
    'permissions': ('store', 'rolepermission'),
    'delegations': ('store', 'permissiondelegation'),
    'navigation': ('store', 'navigationitem'),
    'audit': ('store', 'auditevent'),
}
PERMISSION_ACTIONS = ('view', 'create', 'edit', 'delete', 'approve', 'reject', 'publish', 'unpublish', 'assign', 'cancel', 'export', 'manage', 'manage_design_status')


def _permission_codename(resource, action, model):
    if resource == 'cart':
        return f'{action}_cart'
    return f'{action}_{model}'


def role_for_user(user):
    """Returns only the persisted role assignment; missing assignments fail closed."""
    if not user or not user.is_authenticated:
        return None
    assignment = UserRole.objects.select_related('role').filter(user_id=user.pk).first()
    return assignment.role if assignment and assignment.role.active else None


def assign_role(user, role_code, actor=None):
    """Assign a persisted role, restricting interactive changes to superadmins."""
    role = AccessRole.objects.get(code=role_code)
    if actor is not None:
        actor_role = role_for_user(actor)
        if (
            not actor_role
            or actor_role.code != AccessRole.Code.SUPERADMIN
            or is_explicitly_denied(actor, 'role_assignments', 'change')
        ):
            record_audit(actor, 'assign_role', 'role_assignments', user, AuditEvent.Result.DENIED)
            raise PermissionDenied('Solo un superadmin puede cambiar el rol de otra cuenta.')
    if not role.active:
        raise ValidationError('No se puede asignar un rol inactivo.')
    try:
        with transaction.atomic():
            previous = UserRole.objects.select_related('role').filter(user=user).first()
            if (
                previous
                and previous.role.code == AccessRole.Code.ADMIN
                and role.code != AccessRole.Code.ADMIN
            ):
                revoke_admin_delegations(user, actor)
            assignment, _ = UserRole.objects.update_or_create(user=user, defaults={'role': role})
            record_audit(actor, 'assign_role', 'role_assignments', user, details={'role': role.code}, instance=assignment)
    except ValidationError:
        record_audit(
            actor,
            'assign_role',
            'role_assignments',
            affected_user=user,
            result=AuditEvent.Result.DENIED,
            details={'role': role.code},
        )
        raise
    return assignment.role


def has_role(user, *role_codes):
    role = role_for_user(user)
    return role is not None and role.code in role_codes


def permission_for(resource, action):
    """Resolve a resource/action pair to Django's canonical Permission row."""
    action = canonical_action(action)
    model_key = PERMISSION_RESOURCES.get(resource)
    if model_key is None or action not in PERMISSION_ACTIONS:
        return None
    app_label, model = model_key
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model)
        return Permission.objects.get(
            content_type=content_type,
            codename=_permission_codename(resource, {'create': 'add', 'edit': 'change'}.get(action, action), model),
        )
    except (ContentType.DoesNotExist, Permission.DoesNotExist):
        return None


def canonical_action(action):
    return {'add': 'create', 'change': 'edit'}.get(action, action)


def capability_for(resource, action):
    return RBACCapability.objects.select_related('resource', 'action').filter(
        resource__code=resource,
        resource__active=True,
        action__code=canonical_action(action),
        action__active=True,
    ).first()


def role_has_permission(role, resource, action):
    """Check a role-level grant for navigation gating, without user overrides."""
    if role is None or not role.active:
        return False
    if role.code == AccessRole.Code.SUPERADMIN:
        return True
    action = canonical_action(action)
    capability = capability_for(resource, action)
    if capability is None:
        return False
    grant = RBACGrant.objects.filter(role=role, capability=capability).first()
    if grant:
        return grant.effect == RBACGrant.Effect.ALLOW
    permission = permission_for(resource, action)
    return bool(permission and RolePermission.objects.filter(role=role, permission=permission).exists())


def record_scope_for(user, resource):
    """Return the explicit record scope; custom roles default to no records."""
    role = role_for_user(user)
    if role is None:
        return RBACRecordScopeGrant.Scope.NONE
    if role.code == AccessRole.Code.SUPERADMIN:
        return RBACRecordScopeGrant.Scope.ALL
    user_scope = RBACRecordScopeGrant.objects.filter(user=user, resource__code=resource).values_list('scope', flat=True).first()
    if user_scope:
        return user_scope
    role_scope = RBACRecordScopeGrant.objects.filter(role=role, resource__code=resource).values_list('scope', flat=True).first()
    if role_scope:
        return role_scope
    if role.code == AccessRole.Code.ADMIN:
        return RBACRecordScopeGrant.Scope.ALL
    if role.code == AccessRole.Code.CUSTOMER and resource in ('orders', 'designs', 'customers', 'cart'):
        return 'own'
    if role.code == AccessRole.Code.CRAFTSWOMAN and resource in ('orders', 'designs', 'products'):
        return 'assigned'
    return RBACRecordScopeGrant.Scope.NONE


def permission_catalog():
    return [{
        'resource': capability.resource.code,
        'resource_name': capability.resource.name,
        'action': capability.action.code,
        'action_name': capability.action.name,
        'codename': f'{capability.resource.code}_{capability.action.code}',
        'name': f'{capability.action.name} · {capability.resource.name}',
    } for capability in RBACCapability.objects.select_related('resource', 'action').filter(
        resource__active=True, action__active=True,
    ).order_by('resource__name', 'action__name')]


def permission_key(permission):
    app_label = permission.content_type.app_label
    model = permission.content_type.model
    for resource, (resource_app, resource_model) in PERMISSION_RESOURCES.items():
        if (app_label, model) != (resource_app, resource_model):
            continue
        for action in PERMISSION_ACTIONS:
            legacy_action = {'create': 'add', 'edit': 'change'}.get(action, action)
            if permission.codename == _permission_codename(resource, legacy_action, model):
                return resource, action
    return None


def effective_permission_keys(user):
    role = role_for_user(user)
    if role is None:
        return []

    capabilities = list(RBACCapability.objects.select_related('resource', 'action').filter(
        resource__active=True, action__active=True,
    ))
    role_grants = {
        grant.capability_id: grant.effect
        for grant in RBACGrant.objects.filter(role=role, capability__in=capabilities)
    }
    user_grants = {
        grant.capability_id: grant.effect
        for grant in RBACGrant.objects.filter(user=user, capability__in=capabilities)
    }
    configured_capabilities = {
        grant.capability_id
        for grant in RBACGrant.objects.filter(
            Q(role=role) | Q(user=user), capability__in=capabilities,
        )
    }
    effective = []
    for capability in capabilities:
        user_effect = user_grants.get(capability.pk)
        role_effect = role_grants.get(capability.pk)
        denied = RBACGrant.Effect.DENY in (user_effect, role_effect)
        allowed = RBACGrant.Effect.ALLOW in (user_effect, role_effect)
        if role.code == AccessRole.Code.SUPERADMIN or (allowed and not denied):
            key = f'{capability.resource.code}.{capability.action.code}'
            effective.append(key)
            if capability.action.code == 'create':
                effective.append(f'{capability.resource.code}.add')
            elif capability.action.code == 'edit':
                effective.append(f'{capability.resource.code}.change')
    # Legacy Django permission grants remain readable during the transition.
    content_types = {}
    for app_label, model in PERMISSION_RESOURCES.values():
        content_type = ContentType.objects.filter(app_label=app_label, model=model).first()
        if content_type:
            content_types[(app_label, model)] = content_type
    permissions = Permission.objects.select_related('content_type').filter(
        content_type_id__in=[content_type.pk for content_type in content_types.values()],
    )
    permission_by_key = {}
    for resource, (app_label, model) in PERMISSION_RESOURCES.items():
        content_type = content_types.get((app_label, model))
        if not content_type:
            continue
        for action in PERMISSION_ACTIONS:
            codename = _permission_codename(resource, {'create': 'add', 'edit': 'change'}.get(action, action), model)
            permission = next((
                item for item in permissions
                if item.content_type_id == content_type.pk and item.codename == codename
            ), None)
            if permission:
                permission_by_key[(resource, action)] = permission

    individual = dict(
        UserPermissionGrant.objects.filter(user=user).values_list('permission_id', 'effect')
    )
    denied_ids = {
        permission_id for permission_id, effect in individual.items()
        if effect == UserPermissionGrant.Effect.DENY
    }
    allowed_ids = {
        permission_id for permission_id, effect in individual.items()
        if effect == UserPermissionGrant.Effect.ALLOW
    }
    role_permission_ids = set(RolePermission.objects.filter(role=role).values_list('permission_id', flat=True))
    delegated_ids = set(PermissionDelegation.objects.filter(admin=user).values_list('permission_id', flat=True))
    django_permissions = user.get_all_permissions() if user.is_authenticated and not user.is_superuser else set()

    def add_effective_key(resource, action):
        effective.append(f'{resource}.{action}')
        if action == 'create':
            effective.append(f'{resource}.add')
        elif action == 'edit':
            effective.append(f'{resource}.change')

    for (resource, action), permission in permission_by_key.items():
        action = canonical_action(action)
        capability = next((item for item in capabilities if item.resource.code == resource and item.action.code == action), None)
        if capability and capability.pk in configured_capabilities:
            continue
        if any(key in (f'{resource}.{action}', f'{resource}.{("add" if action == "create" else "change" if action == "edit" else action)}') for key in effective):
            continue
        if permission.pk in denied_ids:
            continue
        if role.code == AccessRole.Code.SUPERADMIN:
            add_effective_key(resource, action)
            continue
        if permission.pk in allowed_ids and (
            role.code != AccessRole.Code.ADMIN or permission.pk in delegated_ids
        ):
            add_effective_key(resource, action)
            continue
        if permission.pk in role_permission_ids:
            add_effective_key(resource, action)
            continue
        django_key = f'{permission.content_type.app_label}.{permission.codename}'
        if role.code == AccessRole.Code.ADMIN:
            if permission.pk in delegated_ids and django_key in django_permissions:
                add_effective_key(resource, action)
        elif django_key in django_permissions:
            add_effective_key(resource, action)
    return effective


def has_permission(user, resource, action, obj=None):
    """Evaluate explicit denies before individual, role, or Django grants."""
    role = role_for_user(user)
    if role is None:
        return False
    action = canonical_action(action)
    permission = permission_for(resource, action)
    capability = capability_for(resource, action)
    if capability is None:
        return False
    if role.code == AccessRole.Code.SUPERADMIN:
        return True
    legacy_individual = UserPermissionGrant.objects.filter(user=user, permission=permission).first() if permission else None
    if legacy_individual and legacy_individual.effect == UserPermissionGrant.Effect.DENY:
        return False
    individual_grant = RBACGrant.objects.filter(user=user, capability=capability).first()
    if individual_grant and individual_grant.effect == RBACGrant.Effect.DENY:
        return False
    role_grant = RBACGrant.objects.filter(role=role, capability=capability).first()
    if role_grant and role_grant.effect == RBACGrant.Effect.DENY:
        return False
    if individual_grant and individual_grant.effect == RBACGrant.Effect.ALLOW:
        return True
    if legacy_individual and legacy_individual.effect == UserPermissionGrant.Effect.ALLOW:
        if role.code != AccessRole.Code.ADMIN or (permission and PermissionDelegation.objects.filter(
            admin=user, permission=permission,
        ).exists()):
            return True
    if role_grant:
        return role_grant.effect == RBACGrant.Effect.ALLOW
    if permission is None:
        return False
    if RolePermission.objects.filter(role=role, permission=permission).exists():
        return True
    if role.code == AccessRole.Code.ADMIN:
        return PermissionDelegation.objects.filter(admin=user, permission=permission).exists() and _has_django_permission(
            user, permission,
        )
    return _has_django_permission(user, permission)


def _has_django_permission(user, permission):
    if not user.is_authenticated or user.is_superuser:
        return False
    return user.has_perm(f'{permission.content_type.app_label}.{permission.codename}')


def is_explicitly_denied(user, resource, action):
    if has_role(user, AccessRole.Code.SUPERADMIN):
        return False
    capability = capability_for(resource, action)
    if capability and RBACGrant.objects.filter(
        Q(user=user) | Q(role=role_for_user(user)),
        capability=capability,
        effect=RBACGrant.Effect.DENY,
    ).exists():
        return True
    permission = permission_for(resource, action)
    return bool(permission and UserPermissionGrant.objects.filter(
        user=user,
        permission=permission,
        effect=UserPermissionGrant.Effect.DENY,
    ).exists())


def can_manage_permission(actor, target, permission):
    role = role_for_user(actor)
    if not role:
        return False
    if is_explicitly_denied(actor, 'permissions', 'change'):
        return False
    if role.code == AccessRole.Code.SUPERADMIN:
        return True
    if role.code != AccessRole.Code.ADMIN or actor.pk == target.pk:
        return False
    if UserPermissionGrant.objects.filter(
        user=actor,
        permission=permission,
        effect=UserPermissionGrant.Effect.DENY,
    ).exists():
        return False
    target_role = role_for_user(target)
    return bool(
        target_role
        and target_role.code in (AccessRole.Code.CUSTOMER, AccessRole.Code.CRAFTSWOMAN)
        and PermissionDelegation.objects.filter(admin=actor, permission=permission).exists()
    )


@transaction.atomic
def revoke_admin_delegations(admin_user, actor=None):
    dynamic_grants = list(RBACGrant.objects.filter(granted_by=admin_user).select_related(
        'user', 'capability__resource', 'capability__action',
    ))
    for grant in dynamic_grants:
        record_audit(
            actor,
            'revoke_user_permission',
            grant.capability.resource.code,
            affected_user=grant.user,
            details={
                'action': grant.capability.action.code,
                'effect': grant.effect,
                'reason': 'admin_scope_revoked',
            },
        )
    RBACGrant.objects.filter(granted_by=admin_user, user__isnull=False).delete()
    grants = list(
        UserPermissionGrant.objects.filter(granted_by=admin_user).select_related(
            'user', 'permission__content_type',
        )
    )
    for grant in grants:
        key = permission_key(grant.permission)
        record_audit(
            actor,
            'revoke_user_permission',
            key[0] if key else 'permissions',
            affected_user=grant.user,
            details={
                'action': key[1] if key else grant.permission.codename,
                'effect': grant.effect,
                'reason': 'admin_scope_revoked',
            },
        )
    delegations = list(
        PermissionDelegation.objects.filter(admin=admin_user).select_related('permission__content_type')
    )
    for delegation in delegations:
        key = permission_key(delegation.permission)
        record_audit(
            actor,
            'revoke_permission_delegation',
            key[0] if key else 'delegations',
            affected_user=admin_user,
            details={'action': key[1] if key else delegation.permission.codename},
        )
    UserPermissionGrant.objects.filter(granted_by=admin_user).delete()
    PermissionDelegation.objects.filter(admin=admin_user).delete()


def set_role_permission(actor, role_code, resource, action, allowed=None, effect=None):
    if (
        not has_role(actor, AccessRole.Code.SUPERADMIN)
        or is_explicitly_denied(actor, 'roles', 'change')
    ):
        record_audit(actor, 'set_role_permission', resource, result=AuditEvent.Result.DENIED)
        raise PermissionDenied('Solo un superadmin puede configurar permisos por rol.')
    with transaction.atomic():
        role = AccessRole.objects.select_for_update().get(code=role_code)
        if role.code == AccessRole.Code.SUPERADMIN:
            raise ValidationError('El superadmin tiene permisos globales y su matriz es solo informativa.')
        permission = permission_for(resource, action)
        capability = capability_for(resource, action)
        next_effect = effect or (RBACGrant.Effect.ALLOW if allowed else None)
        if not role.active or not capability or next_effect not in (None, *RBACGrant.Effect.values):
            raise ValidationError('El rol o el permiso no está disponible.')
        if next_effect:
            RBACGrant.objects.update_or_create(
                role=role,
                capability=capability,
                defaults={'effect': next_effect, 'granted_by': actor},
            )
        else:
            RBACGrant.objects.filter(role=role, capability=capability).delete()
        if permission and next_effect == RBACGrant.Effect.ALLOW:
            RolePermission.objects.update_or_create(
                role=role,
                permission=permission,
                defaults={'granted_by': actor},
            )
        elif permission:
            RolePermission.objects.filter(role=role, permission=permission).delete()
        record_audit(
            actor,
            'set_role_permission',
            resource,
            details={'role': role.code, 'action': canonical_action(action), 'effect': next_effect},
        )


def set_user_permission(actor, target, resource, action, effect):
    permission = permission_for(resource, action)
    capability = capability_for(resource, action)
    if effect not in UserPermissionGrant.Effect.values or capability is None:
        raise ValidationError('El efecto o permiso no es válido.')
    actor_role = role_for_user(actor)
    target_role = role_for_user(target)
    if target_role and target_role.code == AccessRole.Code.SUPERADMIN:
        raise PermissionDenied('No se pueden cambiar permisos individuales de un superadministrador.')
    may_manage = bool(actor_role and actor_role.code == AccessRole.Code.SUPERADMIN)
    if not may_manage and permission is not None:
        may_manage = can_manage_permission(actor, target, permission)
    if not may_manage:
        record_audit(
            actor,
            'set_user_permission',
            resource,
            affected_user=target,
            result=AuditEvent.Result.DENIED,
            details={'action': action, 'effect': effect},
        )
        raise PermissionDenied('No tienes delegación para modificar este permiso o usuario.')
    with transaction.atomic():
        delegation = None
        actor_role = role_for_user(actor)
        if actor_role and actor_role.code == AccessRole.Code.ADMIN:
            delegation = PermissionDelegation.objects.get(admin=actor, permission=permission)
        RBACGrant.objects.update_or_create(
            user=target,
            capability=capability,
            defaults={
                'effect': effect,
                'granted_by': actor,
            },
        )
        if permission:
            UserPermissionGrant.objects.update_or_create(
                user=target,
                permission=permission,
                defaults={'effect': effect, 'granted_by': actor, 'delegation': delegation},
            )
        record_audit(
            actor,
            'set_user_permission',
            resource,
            affected_user=target,
            details={'action': action, 'effect': effect},
        )


def remove_user_permission(actor, target, resource, action):
    permission = permission_for(resource, action)
    capability = capability_for(resource, action)
    if capability is None:
        raise ValidationError('El permiso solicitado no existe.')
    actor_role = role_for_user(actor)
    may_manage = bool(actor_role and actor_role.code == AccessRole.Code.SUPERADMIN)
    if not may_manage and permission is not None:
        may_manage = can_manage_permission(actor, target, permission)
    if not may_manage:
        record_audit(
            actor,
            'remove_user_permission',
            resource,
            affected_user=target,
            result=AuditEvent.Result.DENIED,
            details={'action': action},
        )
        raise PermissionDenied('No tienes delegación para modificar este permiso o usuario.')
    with transaction.atomic():
        RBACGrant.objects.filter(user=target, capability=capability).delete()
        if permission:
            UserPermissionGrant.objects.filter(user=target, permission=permission).delete()
        record_audit(
            actor,
            'remove_user_permission',
            resource,
            affected_user=target,
            details={'action': action},
        )


def set_permission_delegation(actor, admin_user, resource, action, allowed):
    if (
        not has_role(actor, AccessRole.Code.SUPERADMIN)
        or is_explicitly_denied(actor, 'delegations', 'add')
    ):
        record_audit(actor, 'set_permission_delegation', resource, result=AuditEvent.Result.DENIED)
        raise PermissionDenied('Solo un superadmin puede delegar permisos.')
    if not has_role(admin_user, AccessRole.Code.ADMIN):
        raise ValidationError('Las delegaciones solo se pueden asignar a cuentas admin activas.')
    permission = permission_for(resource, action)
    if permission is None:
        raise ValidationError('El permiso solicitado no existe.')
    with transaction.atomic():
        if allowed:
            PermissionDelegation.objects.update_or_create(
                admin=admin_user,
                permission=permission,
                defaults={'granted_by': actor},
            )
        else:
            PermissionDelegation.objects.filter(admin=admin_user, permission=permission).delete()
            UserPermissionGrant.objects.filter(
                granted_by=admin_user,
                permission=permission,
            ).delete()
        record_audit(
            actor,
            'set_permission_delegation',
            resource,
            affected_user=admin_user,
            details={'action': action, 'allowed': bool(allowed)},
        )


def record_audit(
    actor,
    action,
    resource,
    affected_user=None,
    result=AuditEvent.Result.SUCCESS,
    details=None,
    instance=None,
):
    safe_details = details if isinstance(details, dict) else {}
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        action=action,
        resource=resource,
        affected_user=affected_user,
        object_type=instance._meta.label if instance else '',
        object_id=str(instance.pk) if instance and instance.pk else '',
        result=result,
        details=safe_details,
    )
