from functools import wraps

from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied

from store.models import AccessRole
from store.rbac import has_role


class WayuuAdminSite(AdminSite):
    def admin_view(self, view, cacheable=False):
        protected_view = super().admin_view(view, cacheable=cacheable)

        @wraps(view)
        def role_checked_view(request, *args, **kwargs):
            if request.user.is_authenticated and not self.has_permission(request):
                raise PermissionDenied('Tu cuenta no tiene acceso al administrador.')
            return protected_view(request, *args, **kwargs)

        return role_checked_view

    def has_permission(self, request):
        return request.user.is_active and has_role(
            request.user,
            AccessRole.Code.ADMIN,
            AccessRole.Code.SUPERADMIN,
        )