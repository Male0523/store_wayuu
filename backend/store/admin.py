from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.actions import delete_selected
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import AccessRole, Category, Craftswoman, CustomDesign, Customer, NavigationItem, Order, OrderItem, Product, UserRole


@admin.action(description='Eliminar seleccionados')
def eliminar_seleccionados(modeladmin, request, queryset):
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
            return queryset.filter(is_superuser=True)
        if self.value() == 'admin':
            return queryset.filter(is_staff=True, is_superuser=False)
        if self.value() == 'usuario':
            return queryset.filter(is_staff=False)
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

    @admin.display(description='Nivel de acceso', ordering='is_superuser')
    def nivel_de_acceso(self, obj):
        if obj.is_superuser:
            return 'Superadministrador'
        if obj.is_staff:
            return 'Administrador'
        return 'Usuario / cliente'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        # Un administrador nunca puede editar ni eliminar cuentas administrativas.
        return queryset.filter(is_staff=False, is_superuser=False)

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
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

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(AccessRole)
class AccessRoleAdmin(SuperadminOnlyAdmin):
    list_display = ('name', 'code', 'priority', 'users_count')
    list_editable = ('priority',)
    search_fields = ('name', 'code', 'description')
    ordering = ('priority', 'name')

    @admin.display(description='Usuarios asignados')
    def users_count(self, obj):
        return obj.users.count()


@admin.register(UserRole)
class UserRoleAdmin(SuperadminOnlyAdmin):
    list_display = ('user', 'role', 'updated_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'user__first_name')
    list_select_related = ('user', 'role')

    def has_delete_permission(self, request, obj=None):
        # El rol no se borra aisladamente: se cambia para mantener permisos coherentes.
        return False


@admin.register(NavigationItem)
class NavigationItemAdmin(SuperadminOnlyAdmin):
    list_display = ('label', 'route_name', 'roles_visible', 'active', 'order')
    list_editable = ('active', 'order')
    list_filter = ('active', 'roles')
    search_fields = ('label', 'route_name', 'description')
    filter_horizontal = ('roles',)
    ordering = ('order', 'label')
    fieldsets = (
        ('Vista y enlace', {'fields': ('label', 'description', 'route_name', 'anchor')}),
        ('Quién puede verla', {'fields': ('roles',), 'description': 'Selecciona los roles que verán esta opción en el menú.'}),
        ('Publicación', {'fields': ('active', 'order')}),
    )

    @admin.display(description='Roles con acceso')
    def roles_visible(self, obj):
        return ', '.join(obj.roles.values_list('name', flat=True)) or 'Sin roles asignados'


@admin.register(Craftswoman)
class CraftswomanAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'community', 'region', 'phone', 'active')
    list_filter = ('active', 'region')
    search_fields = ('name', 'community', 'region', 'phone')
    actions = (eliminar_seleccionados,)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    list_filter = ('active',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'size', 'region', 'category', 'craftswoman', 'custom_design', 'price', 'stock', 'active')
    list_editable = ('price', 'stock', 'active')
    list_filter = ('active', 'category', 'craftswoman')
    search_fields = ('sku', 'name', 'description')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'email', 'phone', 'city')
    search_fields = ('name', 'email', 'phone')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'craftswoman', 'status', 'payment_method', 'order_total', 'created_at')
    list_filter = ('status', 'payment_method', 'craftswoman', 'created_at')
    search_fields = ('customer__name', 'customer__email')
    readonly_fields = ('created_at', 'updated_at', 'order_total')
    inlines = [OrderItemInline]

    @admin.display(description='Total (COP)')
    def order_total(self, obj):
        return obj.total


@admin.register(CustomDesign)
class CustomDesignAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'pattern', 'size', 'quantity', 'estimated_price', 'craftswoman', 'status', 'created_at')
    list_filter = ('status', 'size', 'craftswoman', 'created_at')
    search_fields = ('customer__name', 'customer__email', 'pattern')
