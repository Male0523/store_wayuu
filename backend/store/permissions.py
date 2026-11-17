from rest_framework.permissions import BasePermission

from .models import AccessRole, Category, Craftswoman, Product
from .rbac import has_permission as has_rbac_permission, record_audit, record_scope_for, role_for_user


class RolePermission(BasePermission):
    role_codes = ()
    message = 'Tu cuenta no tiene permiso para esta operación.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = role_for_user(request.user)
        if role is None or (self.role_codes and role.code not in self.role_codes):
            return False
        resource = getattr(view, 'rbac_resource', None)
        if resource:
            default_action = {
                'GET': 'view',
                'HEAD': 'view',
                'OPTIONS': 'view',
                'POST': 'create',
                'PUT': 'edit',
                'PATCH': 'edit',
                'DELETE': 'delete',
            }.get(request.method)
            action = getattr(view, 'rbac_actions', {}).get(request.method, default_action)
            if callable(action):
                action = action(request, view)
            actions = action if isinstance(action, (tuple, list)) else (action,)
            allowed = bool(actions) and all(has_rbac_permission(request.user, resource, required) for required in actions)
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
    role_codes = ()
    message = 'Tu cuenta no tiene un rol de acceso asignado.'


class OrderAccess(RolePermission):
    role_codes = ()
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
    role_codes = ()
    message = 'Esta operación requiere rol de administración.'

    def has_permission(self, request, view):
        role = role_for_user(request.user) if request.user and request.user.is_authenticated else None
        if role is None:
            return False
        resource = getattr(view, 'rbac_resource', None)
        # Persona permissions describe their own records; they must never
        # authorize an administrative collection endpoint.
        if role.code in (AccessRole.Code.CUSTOMER, AccessRole.Code.CRAFTSWOMAN):
            return False
        # A capability alone never grants cross-account access to private rows.
        # Custom roles must also receive an explicit all-records scope.
        if resource in {'orders', 'designs', 'products', 'customers', 'users', 'craftswomen'} and record_scope_for(
            request.user, resource,
        ) != 'all':
            return False
        if role.code not in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN) and not resource:
            return False
        if resource:
            return super().has_permission(request, view)
        return role.code in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN)


def product_publish_action(request, view):
    if 'active' not in request.data:
        return 'edit'
    product = Product.objects.filter(pk=view.kwargs.get('product_id')).only('active').first()
    if product and bool(request.data.get('active')) == product.active:
        return 'edit'
    visibility_action = 'publish' if request.data.get('active') else 'unpublish'
    return ('edit', visibility_action) if set(request.data.keys()) - {'active'} else visibility_action


def category_visibility_action(request, view):
    if 'active' not in request.data:
        return 'edit'
    category = Category.objects.filter(pk=view.kwargs.get('category_id')).only('active').first()
    if category and bool(request.data.get('active')) == category.active:
        return 'edit'
    visibility_action = 'publish' if request.data.get('active') else 'unpublish'
    return ('edit', visibility_action) if set(request.data.keys()) - {'active'} else visibility_action


def order_admin_action(request, view):
    next_status = request.data.get('status')
    if next_status == 'cancelled':
        return 'cancel'
    if next_status == 'paid':
        return 'approve'
    return 'edit'


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
