from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.actions import delete_selected
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import (
    AccessRole,
    AuditEvent,
    Category,
    Craftswoman,
    CustomDesign,
    Customer,
    NavigationItem,
    Order,
    OrderItem,
    PermissionDelegation,
    Product,
    RolePermission,
    UserPermissionGrant,
    UserRole,
)
from .rbac import (
    has_permission as has_rbac_permission,
    has_role,
    permission_key,
    record_audit,
    revoke_admin_delegations,
    role_for_user,
)


@admin.action(description='Eliminar seleccionados')
def eliminar_seleccionados(modeladmin, request, queryset):
    if modeladmin.model is User:
        protected = queryset.filter(access_profile__role__code=AccessRole.Code.SUPERADMIN).count()
        if protected:
            messages.warning(request, 'Las cuentas superadmin protegidas no se eliminaron.')
        queryset = queryset.exclude(access_profile__role__code=AccessRole.Code.SUPERADMIN)
    return delete_selected(modeladmin, request, queryset)


class NivelDeAccesoFilter(SimpleListFilter):
    title = 'nivel de acceso'
    parameter_name = 'nivel'

    def lookups(self, request, model_admin):
        return (
            ('superadmin', 'Superadministrador'),
            ('admin', 'Administrador'),
            ('usuario', 'Usuario o cliente'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'superadmin':
            return queryset.filter(access_profile__role__code=AccessRole.Code.SUPERADMIN)
        if self.value() == 'admin':
            return queryset.filter(access_profile__role__code=AccessRole.Code.ADMIN)
        if self.value() == 'usuario':
            return queryset.filter(access_profile__role__code=AccessRole.Code.CUSTOMER)
        return queryset


# Permite administrar y eliminar usuarios desde el mismo panel de Wayuuwaa.
admin.site.unregister(User)


@admin.register(User)
class WayuuUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'nivel_de_acceso', 'is_active', 'date_joined')
    list_filter = (NivelDeAccesoFilter, 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    actions = (eliminar_seleccionados,)
    fieldsets = (
        ('Cuenta de usuario', {
            'fields': ('username', 'password'),
            'description': 'Puedes editar los datos de esta cuenta sin conocer su contraseña. Usa el enlace de contraseña para asignar una nueva cuando sea necesario.',
        }),
        ('Información personal', {'fields': ('first_name', 'last_name', 'email')}),
        ('Controles, recursos y permisos', {
            'fields': ('is_active', 'groups', 'user_permissions'),
            'description': 'El nivel de acceso se asigna en “Asignaciones de roles”. Aquí puedes definir grupos y permisos específicos para administradores.',
        }),
        ('Registro de actividad', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        ('Crear una cuenta', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_active'),
        }),
    )

    @admin.display(description='Nivel de acceso', ordering='access_profile__role__priority')
    def nivel_de_acceso(self, obj):
        role = role_for_user(obj)
        return role.name if role else 'Sin rol asignado'

    def has_module_permission(self, request):
        return any(
            has_rbac_permission(request.user, 'users', action)
            for action in ('view', 'add', 'change', 'delete')
        )

    def has_view_permission(self, request, obj=None):
        if not has_rbac_permission(request.user, 'users', 'view'):
            return False
        if has_role(request.user, AccessRole.Code.SUPERADMIN):
            return True
        return obj is None or self._admin_target(request, obj)

    def has_add_permission(self, request):
        return has_rbac_permission(request.user, 'users', 'add')

    def has_change_permission(self, request, obj=None):
        if not has_rbac_permission(request.user, 'users', 'change'):
            return False
        return has_role(request.user, AccessRole.Code.SUPERADMIN) or obj is None or self._admin_target(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not has_rbac_permission(request.user, 'users', 'delete'):
            return False
        if obj and has_role(obj, AccessRole.Code.SUPERADMIN):
            return False
        return has_role(request.user, AccessRole.Code.SUPERADMIN) or obj is None or self._admin_target(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and has_role(obj, AccessRole.Code.SUPERADMIN):
            readonly.append('is_active')
        return tuple(readonly)

    @staticmethod
    def _admin_target(request, obj):
        return (
            has_role(request.user, AccessRole.Code.ADMIN)
            and request.user.pk != obj.pk
            and has_role(obj, AccessRole.Code.CUSTOMER, AccessRole.Code.CRAFTSWOMAN)
        )

    def save_model(self, request, obj, form, change):
        was_active_admin = False
        if change:
            previous = User.objects.filter(pk=obj.pk).first()
            was_active_admin = bool(
                previous
                and previous.is_active
                and has_role(previous, AccessRole.Code.ADMIN)
            )
        if was_active_admin and not obj.is_active:
            revoke_admin_delegations(obj, request.user)
        if has_role(obj, AccessRole.Code.SUPERADMIN) and not obj.is_active:
            raise ValidationError('La cuenta superadmin protegida no se puede desactivar.')
        super().save_model(request, obj, form, change)
        record_audit(
            request.user,
            'update_user' if change else 'create_user',
            'users',
            affected_user=obj,
            instance=obj,
        )

    def delete_queryset(self, request, queryset):
        protected = queryset.filter(access_profile__role__code=AccessRole.Code.SUPERADMIN)
        queryset = queryset.exclude(pk__in=protected.values('pk'))
        for user in queryset:
            if has_role(user, AccessRole.Code.ADMIN):
                revoke_admin_delegations(user, request.user)
            record_audit(
                request.user,
                'delete_user',
                'users',
                affected_user=user,
                details={'username': user.get_username()},
                instance=user,
            )
        queryset.delete()

    def delete_model(self, request, obj):
        if has_role(obj, AccessRole.Code.ADMIN):
            revoke_admin_delegations(obj, request.user)
        record_audit(
            request.user,
            'delete_user',
            'users',
            affected_user=obj,
            details={'username': obj.get_username()},
            instance=obj,
        )
        super().delete_model(request, obj)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if has_role(request.user, AccessRole.Code.SUPERADMIN):
            return queryset
        if has_role(request.user, AccessRole.Code.ADMIN):
            return queryset.filter(
                access_profile__role__code__in=(AccessRole.Code.CUSTOMER, AccessRole.Code.CRAFTSWOMAN),
            ).exclude(pk=request.user.pk)
        return queryset.none()

    def get_fieldsets(self, request, obj=None):
        if has_role(request.user, AccessRole.Code.SUPERADMIN):
            return self.add_fieldsets if obj is None else self.fieldsets
        if obj is None:
            return (
                ('Crear usuario o cliente', {
                    'classes': ('wide',),
                    'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_active'),
                }),
            )
        return (
            ('Cuenta de usuario', {
                'fields': ('username', 'password'),
                'description': 'Puedes actualizar los datos de usuarios o clientes sin conocer su contraseña. El enlace de contraseña permite asignar una nueva.',
            }),
            ('Información personal', {'fields': ('first_name', 'last_name', 'email')}),
            ('Estado de la cuenta', {'fields': ('is_active',)}),
        )


class SuperadminOnlyAdmin(admin.ModelAdmin):
    """La configuración de roles y vistas nunca queda disponible para administradores comunes."""

    rbac_resource = ''

    def _allowed(self, request, action):
        if not has_role(request.user, AccessRole.Code.SUPERADMIN):
            return False
        return not self.rbac_resource or has_rbac_permission(request.user, self.rbac_resource, action)

    def has_module_permission(self, request):
        return any(self._allowed(request, action) for action in ('view', 'add', 'change', 'delete'))

    def has_view_permission(self, request, obj=None):
        return self._allowed(request, 'view')

    def has_add_permission(self, request):
        return self._allowed(request, 'add')

    def has_change_permission(self, request, obj=None):
        return self._allowed(request, 'change')

    def has_delete_permission(self, request, obj=None):
        return self._allowed(request, 'delete')


class ScopedRBACModelAdmin(admin.ModelAdmin):
    rbac_resource = ''

    def has_module_permission(self, request):
        return any(
            has_rbac_permission(request.user, self.rbac_resource, action)
            for action in ('view', 'add', 'change', 'delete')
        )

    def has_view_permission(self, request, obj=None):
        return has_rbac_permission(request.user, self.rbac_resource, 'view', obj)

    def has_add_permission(self, request):
        return has_rbac_permission(request.user, self.rbac_resource, 'add')

    def has_change_permission(self, request, obj=None):
        return has_rbac_permission(request.user, self.rbac_resource, 'change', obj)

    def has_delete_permission(self, request, obj=None):
        return has_rbac_permission(request.user, self.rbac_resource, 'delete', obj)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        record_audit(
            request.user,
            f'{"update" if change else "create"}_{self.rbac_resource}',
            self.rbac_resource,
            instance=obj,
        )

    def delete_model(self, request, obj):
        record_audit(request.user, f'delete_{self.rbac_resource}', self.rbac_resource, instance=obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            record_audit(request.user, f'delete_{self.rbac_resource}', self.rbac_resource, instance=obj)
        queryset.delete()

@admin.register(AccessRole)
class AccessRoleAdmin(SuperadminOnlyAdmin):
    rbac_resource = 'roles'
    list_display = ('name', 'code', 'priority', 'users_count')
    list_editable = ('priority',)
    search_fields = ('name', 'code', 'description')
    ordering = ('priority', 'name')

    @admin.display(description='Usuarios asignados')
    def users_count(self, obj):
        return obj.users.count()

    def get_readonly_fields(self, request, obj=None):
        readonly = ['code']
        if obj and obj.users.filter(user__is_active=True).exists():
            readonly.append('active')
        return tuple(readonly)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        record_audit(
            request.user,
            'update_role' if change else 'create_role',
            'roles',
            details={'role': obj.code, 'active': obj.active},
            instance=obj,
        )

    def has_delete_permission(self, request, obj=None):
        return False


class ProtectedUserRoleForm(forms.ModelForm):
    class Meta:
        model = UserRole
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:
            return cleaned_data
        previous = UserRole.objects.select_related('role').get(pk=self.instance.pk)
        next_role = cleaned_data.get('role')
        user = cleaned_data.get('user')
        if (
            next_role
            and next_role.code != AccessRole.Code.SUPERADMIN
            and previous.role.code == AccessRole.Code.SUPERADMIN
            and user
            and user.is_active
            and not UserRole.objects.filter(
                role__code=AccessRole.Code.SUPERADMIN,
                role__active=True,
                user__is_active=True,
            ).exclude(user_id=user.pk).exists()
        ):
            raise forms.ValidationError('No se puede retirar el rol del último superadministrador activo.')
        return cleaned_data


@admin.register(UserRole)
class UserRoleAdmin(SuperadminOnlyAdmin):
    rbac_resource = 'role_assignments'
    form = ProtectedUserRoleForm
    list_display = ('user', 'role', 'updated_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'user__first_name')
    list_select_related = ('user', 'role')

    def has_delete_permission(self, request, obj=None):
        # El rol no se borra aisladamente: se cambia para mantener permisos coherentes.
        return False

    def save_model(self, request, obj, form, change):
        previous = UserRole.objects.select_related('role').filter(user=obj.user).first()
        if (
            previous
            and previous.role.code == AccessRole.Code.ADMIN
            and obj.role.code != AccessRole.Code.ADMIN
        ):
            revoke_admin_delegations(obj.user, request.user)
        super().save_model(request, obj, form, change)
        record_audit(
            request.user,
            'assign_role',
            'role_assignments',
            affected_user=obj.user,
            details={'role': obj.role.code},
            instance=obj,
        )


@admin.register(NavigationItem)
class NavigationItemAdmin(SuperadminOnlyAdmin):
    rbac_resource = 'navigation'
    list_display = ('label', 'route_name', 'roles_visible', 'permission', 'active', 'order')
    list_editable = ('active', 'order')
    list_filter = ('active', 'roles')
    search_fields = ('label', 'route_name', 'description')
    filter_horizontal = ('roles',)
    ordering = ('order', 'label')
    fieldsets = (
        ('Vista y enlace', {'fields': ('label', 'description', 'route_name', 'anchor')}),
        ('Quién puede verla', {'fields': ('roles', 'permission'), 'description': 'El rol limita el acceso; el permiso opcional oculta el enlace cuando la acción no está autorizada.'}),
        ('Publicación', {'fields': ('active', 'order')}),
    )

    @admin.display(description='Roles con acceso')
    def roles_visible(self, obj):
        return ', '.join(obj.roles.values_list('name', flat=True)) or 'Sin roles asignados'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        record_audit(
            request.user,
            'update_navigation' if change else 'create_navigation',
            'navigation',
            details={'route_name': obj.route_name},
            instance=obj,
        )


@admin.register(RolePermission)
class RolePermissionAdmin(SuperadminOnlyAdmin):
    rbac_resource = 'permissions'
    list_display = ('role', 'permission', 'granted_by', 'created_at')
    list_filter = ('role', 'permission__content_type__app_label')
    search_fields = ('role__name', 'permission__codename', 'permission__name')
    readonly_fields = ('created_at',)

    def save_model(self, request, obj, form, change):
        obj.granted_by = request.user
        super().save_model(request, obj, form, change)
        record_audit(request.user, 'set_role_permission', 'permissions', details={
            'role': obj.role.code,
            'permission': obj.permission.codename,
            'allowed': True,
        })

    def delete_model(self, request, obj):
        record_audit(request.user, 'revoke_role_permission', 'permissions', details={
            'role': obj.role.code,
            'permission': obj.permission.codename,
        })
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for grant in queryset.select_related('role', 'permission'):
            record_audit(request.user, 'revoke_role_permission', 'permissions', details={
                'role': grant.role.code,
                'permission': grant.permission.codename,
            })
        queryset.delete()


@admin.register(UserPermissionGrant)
class UserPermissionGrantAdmin(SuperadminOnlyAdmin):
    rbac_resource = 'permissions'
    list_display = ('user', 'permission', 'effect', 'granted_by', 'updated_at')
    list_filter = ('effect', 'permission__content_type__app_label')
    search_fields = ('user__username', 'permission__codename', 'permission__name')
    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        obj.granted_by = request.user
        super().save_model(request, obj, form, change)
        record_audit(request.user, 'set_user_permission', 'permissions', affected_user=obj.user, details={
            'permission': obj.permission.codename,
            'effect': obj.effect,
        })

    def delete_model(self, request, obj):
        record_audit(request.user, 'remove_user_permission', 'permissions', affected_user=obj.user, details={
            'permission': obj.permission.codename,
        })
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for grant in queryset.select_related('user', 'permission'):
            record_audit(request.user, 'remove_user_permission', 'permissions', affected_user=grant.user, details={
                'permission': grant.permission.codename,
            })
        queryset.delete()


@admin.register(PermissionDelegation)
class PermissionDelegationAdmin(SuperadminOnlyAdmin):
    rbac_resource = 'delegations'
    list_display = ('admin', 'permission', 'granted_by', 'created_at')
    list_filter = ('permission__content_type__app_label',)
    search_fields = ('admin__username', 'permission__codename', 'permission__name')
    readonly_fields = ('created_at',)

    def save_model(self, request, obj, form, change):
        obj.granted_by = request.user
        super().save_model(request, obj, form, change)
        record_audit(request.user, 'set_permission_delegation', 'delegations', affected_user=obj.admin, details={
            'permission': obj.permission.codename,
            'allowed': True,
        })

    def delete_model(self, request, obj):
        for grant in obj.user_grants.select_related('user', 'permission__content_type'):
            key = permission_key(grant.permission)
            record_audit(
                request.user,
                'revoke_user_permission',
                key[0] if key else 'permissions',
                affected_user=grant.user,
                details={
                    'action': key[1] if key else grant.permission.codename,
                    'effect': grant.effect,
                    'reason': 'delegation_revoked',
                },
            )
        record_audit(request.user, 'revoke_permission_delegation', 'delegations', affected_user=obj.admin, details={
            'permission': obj.permission.codename,
        })
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for delegation in list(queryset.select_related('admin', 'permission__content_type')):
            self.delete_model(request, delegation)

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditEvent)
class AuditEventAdmin(SuperadminOnlyAdmin):
    rbac_resource = 'audit'
    list_display = ('created_at', 'actor', 'action', 'resource', 'affected_user', 'result')
    list_filter = ('result', 'resource', 'action', 'created_at')
    search_fields = ('actor__username', 'affected_user__username', 'action', 'resource')
    readonly_fields = (
        'actor', 'action', 'resource', 'affected_user', 'object_type', 'object_id',
        'result', 'details', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Craftswoman)
class CraftswomanAdmin(ScopedRBACModelAdmin):
    rbac_resource = 'craftswomen'
    list_display = ('name', 'user', 'community', 'region', 'phone', 'active')
    list_filter = ('active', 'region')
    search_fields = ('name', 'community', 'region', 'phone')
    actions = (eliminar_seleccionados,)


@admin.register(Category)
class CategoryAdmin(ScopedRBACModelAdmin):
    rbac_resource = 'categories'
    list_display = ('name', 'active')
    list_filter = ('active',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(ScopedRBACModelAdmin):
    rbac_resource = 'products'
    list_display = ('sku', 'name', 'size', 'region', 'category', 'craftswoman', 'custom_design', 'price', 'stock', 'active')
    list_editable = ('price', 'stock', 'active')
    list_filter = ('active', 'category', 'craftswoman')
    search_fields = ('sku', 'name', 'description')


@admin.register(Customer)
class CustomerAdmin(ScopedRBACModelAdmin):
    rbac_resource = 'customers'
    list_display = ('name', 'user', 'email', 'phone', 'city')
    search_fields = ('name', 'email', 'phone')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

    def has_view_permission(self, request, obj=None):
        return has_rbac_permission(request.user, 'orders', 'view', obj)

    def has_add_permission(self, request, obj=None):
        return has_rbac_permission(request.user, 'orders', 'change', obj)

    def has_change_permission(self, request, obj=None):
        return has_rbac_permission(request.user, 'orders', 'change', obj)

    def has_delete_permission(self, request, obj=None):
        return has_rbac_permission(request.user, 'orders', 'change', obj)


@admin.register(Order)
class OrderAdmin(ScopedRBACModelAdmin):
    rbac_resource = 'orders'
    list_display = ('id', 'customer', 'craftswoman', 'status', 'payment_method', 'order_total', 'created_at')
    list_filter = ('status', 'payment_method', 'craftswoman', 'created_at')
    search_fields = ('customer__name', 'customer__email')
    readonly_fields = ('created_at', 'updated_at', 'order_total')
    inlines = [OrderItemInline]

    @admin.display(description='Total (COP)')
    def order_total(self, obj):
        return obj.total


@admin.register(CustomDesign)
class CustomDesignAdmin(ScopedRBACModelAdmin):
    rbac_resource = 'designs'
    list_display = ('id', 'customer', 'pattern', 'size', 'quantity', 'estimated_price', 'craftswoman', 'status', 'created_at')
    list_filter = ('status', 'size', 'craftswoman', 'created_at')
    search_fields = ('customer__name', 'customer__email', 'pattern')
