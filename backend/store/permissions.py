from rest_framework.permissions import BasePermission

from .models import AccessRole, Craftswoman
from .rbac import has_permission as has_rbac_permission, record_audit, role_for_user


class RolePermission(BasePermission):
    role_codes = ()
    message = 'Tu cuenta no tiene permiso para esta operación.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = role_for_user(request.user)
        if role is None or role.code not in self.role_codes:
            return False
        resource = getattr(view, 'rbac_resource', None)
        if resource:
            default_action = {
                'GET': 'view',
                'HEAD': 'view',
                'OPTIONS': 'view',
                'POST': 'add',
                'PUT': 'change',
                'PATCH': 'change',
                'DELETE': 'delete',
            }.get(request.method)
            action = getattr(view, 'rbac_actions', {}).get(request.method, default_action)
            allowed = action is not None and has_rbac_permission(request.user, resource, action)
            if not allowed:
                record_audit(
                    request.user,
                    f'denied_{request.method.lower()}',
                    resource,
                    result='denied',
                )
            return allowed
        return True


class HasAssignedRole(RolePermission):
    role_codes = tuple(AccessRole.Code.values)
    message = 'Tu cuenta no tiene un rol de acceso asignado.'


class OrderAccess(RolePermission):
    role_codes = tuple(AccessRole.Code.values)
    message = 'Tu rol no tiene acceso a pedidos.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        role = role_for_user(request.user)
        return role.code != AccessRole.Code.CRAFTSWOMAN or Craftswoman.objects.filter(
            user=request.user,
            active=True,
        ).exists()


class CustomerOnly(RolePermission):
    role_codes = (AccessRole.Code.CUSTOMER,)
    message = 'Esta operación solo está disponible para clientes.'


class CraftswomanOnly(RolePermission):
    role_codes = (AccessRole.Code.CRAFTSWOMAN,)
    message = 'Esta operación solo está disponible para tejedoras.'

    def has_permission(self, request, view):
        return super().has_permission(request, view) and Craftswoman.objects.filter(
            user=request.user,
            active=True,
        ).exists()


class AdminOrSuperadmin(RolePermission):
    role_codes = (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN)
    message = 'Esta operación requiere rol de administración.'


class SuperadminOnly(RolePermission):
    role_codes = (AccessRole.Code.SUPERADMIN,)
    message = 'Esta operación solo está disponible para superadministración.'

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        if request.user and request.user.is_authenticated:
            role = role_for_user(request.user)
            if role is None or role.code not in self.role_codes:
                record_audit(
                    request.user,
                    f'denied_{request.method.lower()}',
                    getattr(view, 'rbac_resource', 'superadmin'),
                    result='denied',
                )
        return False