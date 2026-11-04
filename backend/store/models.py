from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.contrib.auth.models import User


class AccessRole(models.Model):
    """Rol persistente usado para mostrar menús y vistas según la cuenta."""

    class Code(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Superadministrador'
        ADMIN = 'admin', 'Administrador'
        CUSTOMER = 'customer', 'Usuario o cliente'
        CRAFTSWOMAN = 'craftswoman', 'Tejedora'

    code = models.CharField('código', max_length=30, choices=Code.choices, unique=True)
    name = models.CharField('nombre', max_length=80)
    description = models.TextField('descripción', blank=True)
    priority = models.PositiveSmallIntegerField('prioridad', default=10)
    active = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'rol de acceso'
        verbose_name_plural = 'roles de acceso'
        ordering = ('priority', 'name')

    def save(self, *args, **kwargs):
            if self.code not in self.Code.values:
                raise ValidationError('Solo se permiten los cuatro roles fijos del sistema.')
            with transaction.atomic():
                if self.pk:
                    previous = AccessRole.objects.select_for_update().filter(pk=self.pk).first()
                    if previous and previous.code != self.code:
                        raise ValidationError('El código de un rol existente no se puede cambiar.')
                    if previous and previous.active and not self.active and UserRole.objects.filter(
                        role=self,
                        user__is_active=True,
                    ).exists():
                        raise ValidationError('No se puede desactivar un rol con cuentas activas asignadas.')
                super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.code in self.Code.values:
            raise ValidationError('Los roles fijos no se pueden eliminar.')
        if self.users.exists():
            raise ValidationError('No se puede eliminar un rol que tenga usuarios asignados.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """Vincula cada cuenta a un rol modificable por el superadministrador."""

    user = models.OneToOneField(User, verbose_name='usuario', on_delete=models.CASCADE, related_name='access_profile')
    role = models.ForeignKey(AccessRole, verbose_name='rol', on_delete=models.PROTECT, related_name='users')
    updated_at = models.DateTimeField('actualizado', auto_now=True)

    class Meta:
        verbose_name = 'asignación de rol'
        verbose_name_plural = 'asignaciones de roles'

    def save(self, *args, **kwargs):
        """El rol almacenado gobierna los privilegios base de Django."""
        with transaction.atomic():
            if not self.role.active:
                raise ValidationError('No se puede asignar un rol inactivo.')
            previous = UserRole.objects.select_for_update().select_related('role').filter(user_id=self.user_id).first()
            if previous and previous.role.code == AccessRole.Code.SUPERADMIN and self.role.code != AccessRole.Code.SUPERADMIN:
                if self.user.is_active and not UserRole.objects.select_for_update().filter(
                    role__code=AccessRole.Code.SUPERADMIN,
                    role__active=True,
                    user__is_active=True,
                ).exclude(user_id=self.user_id).exists():
                    raise ValidationError('No se puede retirar el rol del último superadministrador activo.')
            if (
                previous
                and previous.role.code == AccessRole.Code.ADMIN
                and self.role.code != AccessRole.Code.ADMIN
            ):
                revoke_admin_scope(self.user_id)
            super().save(*args, **kwargs)
            is_superadmin = self.role.code == AccessRole.Code.SUPERADMIN
            is_admin = self.role.code == AccessRole.Code.ADMIN
            User.objects.filter(pk=self.user_id).update(
                is_staff=is_superadmin or is_admin,
                is_superuser=is_superadmin,
            )

    def delete(self, *args, **kwargs):
        raise ValidationError('La asignación de rol no se elimina; debe cambiarse por otra asignación.')

    def __str__(self):
        return f'{self.user.username} · {self.role.name}'


class RolePermission(models.Model):
    role = models.ForeignKey(AccessRole, on_delete=models.CASCADE, related_name='permission_grants')
    permission = models.ForeignKey('auth.Permission', on_delete=models.CASCADE, related_name='wayuu_role_grants')
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='role_permission_changes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('role', 'permission'), name='unique_role_permission_grant')]
        ordering = ('role__code', 'permission__content_type__app_label', 'permission__codename')


class UserPermissionGrant(models.Model):
    class Effect(models.TextChoices):
        ALLOW = 'allow', 'Permitir'
        DENY = 'deny', 'Denegar'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wayuu_permission_grants')
    permission = models.ForeignKey('auth.Permission', on_delete=models.CASCADE, related_name='wayuu_user_grants')
    delegation = models.ForeignKey(
        'PermissionDelegation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='user_grants',
    )
    effect = models.CharField(max_length=5, choices=Effect.choices)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='individual_permission_changes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('user', 'permission'), name='unique_user_permission_grant')]
        ordering = ('user__username', 'permission__content_type__app_label', 'permission__codename')


class PermissionDelegation(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_delegations')
    permission = models.ForeignKey('auth.Permission', on_delete=models.CASCADE, related_name='wayuu_delegations')
    granted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='delegations_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('admin', 'permission'), name='unique_admin_permission_delegation')]
        ordering = ('admin__username', 'permission__content_type__app_label', 'permission__codename')

    def save(self, *args, **kwargs):
        if not UserRole.objects.filter(
            user=self.admin,
            role__code=AccessRole.Code.ADMIN,
            role__active=True,
            user__is_active=True,
        ).exists():
            raise ValidationError('Solo se puede delegar a una cuenta admin activa.')
        return super().save(*args, **kwargs)


class AuditEvent(models.Model):
    class Result(models.TextChoices):
        SUCCESS = 'success', 'Correcto'
        DENIED = 'denied', 'Denegado'

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='wayuu_audit_actions')
    action = models.CharField(max_length=80)
    resource = models.CharField(max_length=80)
    affected_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='wayuu_audit_events')
    object_type = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.SUCCESS)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Los registros de auditoría son inmutables.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Los registros de auditoría no se pueden eliminar.')


def revoke_admin_scope(admin_user_id):
    grants = list(
        UserPermissionGrant.objects.filter(granted_by_id=admin_user_id).select_related(
            'user', 'permission__content_type',
        )
    )
    for grant in grants:
        AuditEvent.objects.create(
            action='revoke_user_permission',
            resource='permissions',
            affected_user=grant.user,
            details={
                'permission': grant.permission.codename,
                'effect': grant.effect,
                'reason': 'admin_scope_revoked',
            },
        )
    delegations = list(PermissionDelegation.objects.filter(admin_id=admin_user_id))
    for delegation in delegations:
        AuditEvent.objects.create(
            action='revoke_permission_delegation',
            resource='delegations',
            affected_user_id=admin_user_id,
            details={'permission_id': delegation.permission_id, 'reason': 'admin_scope_revoked'},
        )
    UserPermissionGrant.objects.filter(granted_by_id=admin_user_id).delete()
    PermissionDelegation.objects.filter(admin_id=admin_user_id).delete()


class NavigationItem(models.Model):
    """Vista editable que aparece en el menú de los roles autorizados."""

    label = models.CharField('nombre de la vista', max_length=80)
    route_name = models.CharField('nombre de ruta Django', max_length=120, help_text='Ejemplo: store:cart o admin:index')
    anchor = models.CharField('sección opcional', max_length=80, blank=True, help_text='Ejemplo: catalogo o historia')
    description = models.CharField('descripción', max_length=220, blank=True)
    roles = models.ManyToManyField(AccessRole, verbose_name='roles que pueden verla', related_name='navigation_items')
    permission = models.ForeignKey(
        'auth.Permission',
        verbose_name='permiso requerido',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='navigation_items',
    )
    order = models.PositiveSmallIntegerField('orden', default=10)
    active = models.BooleanField('visible', default=True)

    class Meta:
        verbose_name = 'vista y menú'
        verbose_name_plural = 'vistas y menús'
        ordering = ('order', 'label')

    def __str__(self):
        return self.label


class Craftswoman(models.Model):
    user = models.OneToOneField(User, verbose_name='cuenta de acceso', on_delete=models.SET_NULL, null=True, blank=True, related_name='craftswoman_profile')
    name = models.CharField('nombre', max_length=150)
    community = models.CharField('comunidad', max_length=150, blank=True)
    region = models.CharField('región', max_length=100, blank=True)
    phone = models.CharField('teléfono', max_length=30, blank=True)
    biography = models.TextField('biografía', blank=True)
    active = models.BooleanField('activa', default=True)
    created_at = models.DateTimeField('creada el', auto_now_add=True)

    class Meta:
        verbose_name = 'artesana'
        verbose_name_plural = 'artesanas'
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField('nombre', max_length=100, unique=True)
    description = models.TextField('descripción', blank=True)
    active = models.BooleanField('activa', default=True)

    class Meta:
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField('referencia', max_length=50, unique=True)
    name = models.CharField('nombre', max_length=180)
    category = models.ForeignKey(Category, verbose_name='categoría', on_delete=models.PROTECT, related_name='products')
    craftswoman = models.ForeignKey(Craftswoman, verbose_name='artesana', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    custom_design = models.OneToOneField('CustomDesign', verbose_name='diseño personalizado', on_delete=models.SET_NULL, null=True, blank=True, related_name='product')
    description = models.TextField('descripción', blank=True)
    region = models.CharField('región de origen', max_length=100, blank=True)
    color = models.CharField('colores', max_length=150, blank=True)
    size = models.CharField('talla', max_length=30, default='M')
    production_time = models.CharField('tiempo de elaboración', max_length=100, blank=True)
    price = models.DecimalField('precio (COP)', max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal('0'))])
    stock = models.PositiveIntegerField('unidades disponibles', default=0)
    # También admite las imágenes base64 del prototipo inicial.
    image_url = models.TextField('URL o imagen', blank=True)
    made_to_order = models.BooleanField('se elabora por pedido', default=False)
    active = models.BooleanField('publicado', default=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        verbose_name = 'producto'
        verbose_name_plural = 'productos'
        ordering = ['name']

    def __str__(self):
        return f'{self.sku} · {self.name}'


class Customer(models.Model):
    user = models.OneToOneField(User, verbose_name='cuenta de acceso', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_profile')
    name = models.CharField('nombre completo', max_length=150)
    email = models.EmailField('correo', unique=True)
    phone = models.CharField('teléfono', max_length=30, blank=True)
    address = models.TextField('dirección', blank=True)
    city = models.CharField('ciudad', max_length=100, blank=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)

    class Meta:
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomerCartItem(models.Model):
    """Producto guardado en el carrito persistente de una cuenta de cliente."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='customer_cart_items')
    quantity = models.PositiveIntegerField('cantidad', validators=[MinValueValidator(1)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'producto del carrito'
        verbose_name_plural = 'productos de los carritos'
        ordering = ('updated_at',)
        constraints = [
            models.UniqueConstraint(fields=('customer', 'product'), name='unique_customer_cart_product'),
        ]

    def __str__(self):
        return f'{self.customer} · {self.product} × {self.quantity}'


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        ACCEPTED = 'accepted', 'Aceptado por tejedora'
        WEAVING = 'weaving', 'En tejido'
        COMPLETED = 'completed', 'Tejido terminado'
        PAID = 'paid', 'Pagado'
        PREPARING = 'preparing', 'En preparación'
        SHIPPED = 'shipped', 'Enviado'
        DELIVERED = 'delivered', 'Entregado'
        CANCELLED = 'cancelled', 'Cancelado'

    class PaymentMethod(models.TextChoices):
        CONTACT = 'contact', 'Pago por acordar'
        NEQUI = 'nequi', 'Nequi'
        DAVIPLATA = 'daviplata', 'Daviplata'
        BANCOLOMBIA = 'bancolombia', 'Bancolombia'
        WHATSAPP = 'whatsapp', 'WhatsApp'

    customer = models.ForeignKey(Customer, verbose_name='cliente', on_delete=models.PROTECT, related_name='orders')
    craftswoman = models.ForeignKey(Craftswoman, verbose_name='tejedora asignada', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    status = models.CharField('estado', max_length=15, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField('método de pago', max_length=15, choices=PaymentMethod.choices, default=PaymentMethod.CONTACT)
    shipping_address = models.TextField('dirección de entrega')
    notes = models.TextField('notas', blank=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        verbose_name = 'pedido'
        verbose_name_plural = 'pedidos'
        ordering = ['-created_at']
        permissions = [
            ('view_cart', 'Can view shopping cart'),
            ('add_cart', 'Can add items to shopping cart'),
            ('change_cart', 'Can change shopping cart'),
            ('delete_cart', 'Can remove items from shopping cart'),
        ]

    @property
    def total(self):
        return sum((item.subtotal for item in self.items.all()), Decimal('0'))

    def __str__(self):
        return f'Pedido #{self.pk} · {self.customer}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name='pedido', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, verbose_name='producto', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField('cantidad', validators=[MinValueValidator(1)])
    unit_price = models.DecimalField('precio unitario (COP)', max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal('0'))])

    class Meta:
        verbose_name = 'producto del pedido'
        verbose_name_plural = 'productos del pedido'
        constraints = [models.UniqueConstraint(fields=['order', 'product'], name='unique_product_per_order')]

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.product} × {self.quantity}'


class CustomDesign(models.Model):
    """Solicitud de una manta configurada por el cliente."""

    class Size(models.TextChoices):
        S = 'S', 'S'
        M = 'M', 'M'
        L = 'L', 'L'
        XL = 'XL', 'XL'

    customer = models.ForeignKey(Customer, verbose_name='cliente', on_delete=models.PROTECT, related_name='custom_designs')
    pattern = models.CharField('patrón', max_length=80)
    base_color = models.CharField('color base', max_length=20)
    accent_color_one = models.CharField('color de acento 1', max_length=20)
    accent_color_two = models.CharField('color de acento 2', max_length=20)
    size = models.CharField('talla', max_length=2, choices=Size.choices, default=Size.M)
    quantity = models.PositiveIntegerField('cantidad', default=1, validators=[MinValueValidator(1)])
    notes = models.TextField('indicaciones', blank=True)
    estimated_price = models.DecimalField('precio estimado (COP)', max_digits=12, decimal_places=0)
    status = models.CharField('estado', max_length=15, choices=Order.Status.choices, default=Order.Status.PENDING)
    craftswoman = models.ForeignKey(Craftswoman, verbose_name='tejedora asignada', on_delete=models.SET_NULL, null=True, blank=True, related_name='custom_designs')
    created_at = models.DateTimeField('creado el', auto_now_add=True)

    class Meta:
        verbose_name = 'diseño personalizado'
        verbose_name_plural = 'diseños personalizados'
        ordering = ['-created_at']

    def __str__(self):
        return f'Diseño #{self.pk} · {self.customer}'
