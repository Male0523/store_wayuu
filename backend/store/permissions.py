from rest_framework.permissions import BasePermission

from .models import AccessRole, Craftswoman
from .rbac import role_for_user


class RolePermission(BasePermission):
    role_codes = ()
    message = 'Tu cuenta no tiene permiso para esta operación.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = role_for_user(request.user)
        return role is not None and role.code in self.role_codes


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