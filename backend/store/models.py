from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
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

    class Meta:
        verbose_name = 'rol de acceso'
        verbose_name_plural = 'roles de acceso'
        ordering = ('priority', 'name')

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
        super().save(*args, **kwargs)
        is_superadmin = self.role.code == AccessRole.Code.SUPERADMIN
        is_admin = self.role.code == AccessRole.Code.ADMIN
        User.objects.filter(pk=self.user_id).update(
            is_staff=is_superadmin or is_admin,
            is_superuser=is_superadmin,
        )

    def __str__(self):
        return f'{self.user.username} · {self.role.name}'


class NavigationItem(models.Model):
    """Vista editable que aparece en el menú de los roles autorizados."""

    label = models.CharField('nombre de la vista', max_length=80)
    route_name = models.CharField('nombre de ruta Django', max_length=120, help_text='Ejemplo: store:cart o admin:index')
    anchor = models.CharField('sección opcional', max_length=80, blank=True, help_text='Ejemplo: catalogo o historia')
    description = models.CharField('descripción', max_length=220, blank=True)
    roles = models.ManyToManyField(AccessRole, verbose_name='roles que pueden verla', related_name='navigation_items')
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
