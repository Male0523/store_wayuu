import re
from decimal import Decimal
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import models, transaction
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import AccessRole, Category, Craftswoman, CustomDesign, Customer, Order, OrderItem, Product, UserRole


def permission_denied(request, exception=None):
    """Muestra una salida clara cuando un rol intenta abrir una acción ajena."""
    return render(request, 'store/permission_denied.html', status=403)


def development_version(request):
    """Huella de archivos para recargar automáticamente el navegador local."""
    watched = [settings.BASE_DIR / 'templates', settings.BASE_DIR / 'static', settings.BASE_DIR / 'store']
    latest = 0
    for folder in watched:
        if folder.exists():
            latest = max((item.stat().st_mtime_ns for item in folder.rglob('*') if item.is_file()), default=latest)
    return JsonResponse({'version': latest})


def _cart(request):
    return request.session.setdefault('cart', {})


def _assign_access_role(user, role_code):
    """Registra el nivel de acceso en la base de datos al crear una cuenta."""
    role = AccessRole.objects.get(code=role_code)
    UserRole.objects.update_or_create(user=user, defaults={'role': role})


def validate_email_safely(email):
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


def _customer_for(request):
    """Autoriza únicamente una cuenta de cliente y devuelve su perfil."""
    if request.user.is_staff or hasattr(request.user, 'craftswoman_profile'):
        raise PermissionDenied('Esta acción solo está disponible para clientes.')
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email or f'{request.user.username}@sin-correo.local',
        },
    )
    return customer


def _cart_items(request):
    cart = _cart(request)
    products = Product.objects.filter(id__in=cart).filter(models.Q(active=True) | models.Q(custom_design__isnull=False)).select_related('category', 'craftswoman', 'custom_design')
    product_map = {str(product.id): product for product in products}
    items = []
    total = Decimal('0')
    for product_id, quantity in cart.items():
        product = product_map.get(str(product_id))
        if not product:
            continue
        quantity = min(int(quantity), product.stock)
        if quantity < 1:
            continue
        subtotal = product.price * quantity
        total += subtotal
        items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
    return items, total


def _hero_image_from_beta():
    """Recupera la fotografía de portada original incluida en el prototipo."""
    source = Path(settings.BASE_DIR).parent / 'mantas_wayuu_beta_6.0.html'
    if not source.exists():
        return ''
    match = re.search(r'class="hero-art">\s*<img src="(?P<image>data:image/[^\"]+)', source.read_text(encoding='utf-8'))
    return match.group('image') if match else ''


def catalog(request):
    products = Product.objects.filter(active=True).select_related('category', 'craftswoman')
    is_craftswoman = request.user.is_authenticated and hasattr(request.user, 'craftswoman_profile')
    if is_craftswoman:
        profile = request.user.craftswoman_profile
        products = products.filter(models.Q(craftswoman=profile) | models.Q(region__iexact=profile.region))
    selected_color = request.GET.get('color', '')
    search = request.GET.get('q', '').strip()
    if selected_color in {'blanco', 'negro', 'rojo', 'azul', 'verde', 'multicolor'}:
        products = products.filter(color__icontains=selected_color)
    if search:
        products = products.filter(
            models.Q(name__icontains=search)
            | models.Q(color__icontains=search)
            | models.Q(description__icontains=search)
        )
    return render(request, 'store/catalog_pro.html', {
        'products': products,
        'selected_color': selected_color,
        'search': search,
        'hero_image': _hero_image_from_beta(),
        'color_filters': [
            ('blanco', 'Blanco', '#f7f5ef'),
            ('negro', 'Negro', '#292827'),
            ('rojo', 'Rojo', '#a24c42'),
            ('azul', 'Azul', '#526a82'),
            ('verde', 'Verde', '#657461'),
            ('multicolor', 'Multicolor', 'linear-gradient(135deg,#c49662 0 33%,#9a6252 33% 66%,#5f7166 66%)'),
        ],
        'is_craftswoman': is_craftswoman,
        'is_customer': request.user.is_authenticated and not request.user.is_staff and not is_craftswoman,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:customer_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            login(request, user)
            if user.is_staff:
                return redirect('/admin/')
            return redirect('store:catalog')
    return render(request, 'store/login_pro.html')


def register_customer(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        if not all([name, username, email, password]):
            messages.error(request, 'Completa todos los campos.')
        elif len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        elif User.objects.filter(username=username).exists() or Customer.objects.filter(email=email).exists():
            messages.error(request, 'Ese usuario o correo ya está registrado.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password, first_name=name)
            Customer.objects.create(user=user, name=name, email=email)
            _assign_access_role(user, AccessRole.Code.CUSTOMER)
            login(request, user)
            return redirect('store:catalog')
    return render(request, 'store/register_pro.html', {'role': 'cliente'})


def register_craftswoman(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        if not all([name, username, email, password]):
            messages.error(request, 'Completa todos los campos obligatorios.')
        elif len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya está registrado.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password, first_name=name)
            Craftswoman.objects.create(user=user, name=name, community=request.POST.get('community', '').strip(), region=request.POST.get('region', '').strip(), phone=request.POST.get('phone', '').strip(), active=False)
            _assign_access_role(user, AccessRole.Code.CRAFTSWOMAN)
            login(request, user)
            messages.success(request, 'Tu registro fue recibido. La administradora debe activar tu cuenta antes de asignarte pedidos.')
            return redirect('store:catalog')
    return render(request, 'store/register_pro.html', {'role': 'tejedora'})


@login_required
def logout_view(request):
    logout(request)
    return redirect('store:catalog')


@login_required
def customer_dashboard(request):
    customer = _customer_for(request)
    return render(request, 'store/customer_dashboard_pro.html', {'customer': customer, 'orders': customer.orders.prefetch_related('items__product'), 'designs': customer.custom_designs.all()})


@login_required
def account_settings(request):
    """Perfil de cliente: los datos se actualizan sin salir de su cuenta."""
    customer = _customer_for(request)
    user = request.user
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        city = request.POST.get('city', '').strip()
        address = request.POST.get('address', '').strip()
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not all((name, username, email)):
            messages.error(request, 'Nombre, usuario y correo son obligatorios.')
        elif not validate_email_safely(email):
            messages.error(request, 'Escribe un correo electrónico válido.')
        elif User.objects.exclude(pk=user.pk).filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
        elif Customer.objects.exclude(pk=customer.pk).filter(email=email).exists():
            messages.error(request, 'Ese correo ya está asociado a otra cuenta.')
        elif new_password and (not user.check_password(current_password) or new_password != confirm_password or len(new_password) < 8):
            messages.error(request, 'Para cambiar la contraseña escribe la actual y una nueva de al menos 8 caracteres, confirmada correctamente.')
        elif (current_password or confirm_password) and not new_password:
            messages.error(request, 'Escribe la nueva contraseña para completar el cambio.')
        else:
            with transaction.atomic():
                user.username = username
                user.email = email
                user.first_name = name
                if new_password:
                    user.set_password(new_password)
                user.save()
                customer.name = name
                customer.email = email
                customer.phone = phone
                customer.city = city
                customer.address = address
                customer.save()
            if new_password:
                update_session_auth_hash(request, user)
            messages.success(request, 'Tu perfil fue actualizado correctamente.')
            return redirect('store:account_settings')
    return render(request, 'store/account_settings.html', {'customer': customer})


@login_required
def craftswoman_dashboard(request):
    try:
        craftswoman = request.user.craftswoman_profile
    except Craftswoman.DoesNotExist:
        messages.error(request, 'Esta cuenta no es de tejedora.')
        return redirect('store:customer_dashboard')
    available_orders = Order.objects.filter(craftswoman__isnull=True, status=Order.Status.PENDING).select_related('customer') if craftswoman.active else Order.objects.none()
    return render(request, 'store/craftswoman_dashboard_pro.html', {'craftswoman': craftswoman, 'orders': craftswoman.orders.select_related('customer'), 'designs': craftswoman.custom_designs.select_related('customer'), 'available_orders': available_orders})


@login_required
@require_POST
def accept_order(request, order_id):
    craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), id=order_id, craftswoman__isnull=True, status=Order.Status.PENDING)
        order.craftswoman = craftswoman
        order.status = Order.Status.ACCEPTED
        order.save(update_fields=['craftswoman', 'status', 'updated_at'])
        for item in order.items.select_related('product__custom_design'):
            if item.product.custom_design_id:
                design = item.product.custom_design
                design.craftswoman = craftswoman
                design.status = Order.Status.ACCEPTED
                design.save(update_fields=['craftswoman', 'status'])
    messages.success(request, f'El pedido #{order.id} fue asignado a tu taller.')
    return redirect('store:craftswoman_dashboard')


@login_required
@require_POST
def update_order_status(request, order_id):
    craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
    order = get_object_or_404(Order, id=order_id, craftswoman=craftswoman)
    transitions = {Order.Status.ACCEPTED: {Order.Status.WEAVING}, Order.Status.WEAVING: {Order.Status.ACCEPTED, Order.Status.COMPLETED}}
    status = request.POST.get('status')
    if status in transitions.get(order.status, set()):
        order.status = status
        order.save(update_fields=['status', 'updated_at'])
        for item in order.items.select_related('product__custom_design'):
            if item.product.custom_design_id:
                design = item.product.custom_design
                if design.craftswoman_id == craftswoman.id:
                    design.status = status
                    design.save(update_fields=['status'])
        messages.success(request, f'Pedido #{order.id} actualizado a “{order.get_status_display()}”.')
    return redirect('store:craftswoman_dashboard')


@login_required
@require_POST
def update_design_status(request, design_id):
    craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
    design = get_object_or_404(CustomDesign, id=design_id, craftswoman=craftswoman)
    transitions = {Order.Status.ACCEPTED: {Order.Status.WEAVING}, Order.Status.WEAVING: {Order.Status.ACCEPTED, Order.Status.COMPLETED}}
    status = request.POST.get('status')
    if status in transitions.get(design.status, set()):
        design.status = status
        design.save(update_fields=['status'])
        messages.success(request, f'Diseño #{design.id} actualizado a “{design.get_status_display()}”.')
    return redirect('store:craftswoman_dashboard')


def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.select_related('category', 'craftswoman'), id=product_id, active=True)
    is_craftswoman = request.user.is_authenticated and hasattr(request.user, 'craftswoman_profile')
    if is_craftswoman:
        profile = request.user.craftswoman_profile
        if product.craftswoman_id != profile.id and product.region.lower() != profile.region.lower():
            raise PermissionDenied('Las tejedoras solo pueden consultar su catálogo regional.')
    can_shop = request.user.is_authenticated and not request.user.is_staff and not is_craftswoman
    return render(request, 'store/product_detail_pro.html', {'product': product, 'can_shop': can_shop})


@login_required
def custom_designer(request):
    customer_profile = _customer_for(request)
    prices = {'S': Decimal('100000'), 'M': Decimal('120000'), 'L': Decimal('145000'), 'XL': Decimal('175000')}
    patterns = [('rombos', 'Rombos'), ('olas', 'Olas'), ('estrellas', 'Estrellas'), ('caminos', 'Caminos')]
    if request.method == 'POST':
        name = customer_profile.name or request.user.get_full_name() or request.user.username
        email = customer_profile.email or request.user.email
        size = request.POST.get('size', 'M')
        if not name or not email:
            messages.error(request, 'Escribe tu nombre y correo para enviar la solicitud.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, 'Escribe un correo electrónico válido.')
            else:
                customer = customer_profile
                if customer.name != name:
                    customer.name = name
                    customer.save(update_fields=['name'])
                quantity = max(1, int(request.POST.get('quantity', 1)))
                design = CustomDesign.objects.create(customer=customer, pattern=request.POST.get('pattern', 'rombos'), base_color=request.POST.get('base_color', '#F5F0EB'), accent_color_one=request.POST.get('accent_color_one', '#C67B5C'), accent_color_two=request.POST.get('accent_color_two', '#45634E'), size=size if size in prices else 'M', quantity=quantity, notes=request.POST.get('notes', '').strip(), estimated_price=prices.get(size, prices['M']) * quantity)
                category, _ = Category.objects.get_or_create(name='Diseños personalizados', defaults={'description': 'Mantas configuradas por clientes.', 'active': True})
                product = Product.objects.create(
                    sku=f'DISENO-{design.pk:05d}',
                    name=f'Manta personalizada · {design.pattern.title()}',
                    category=category,
                    custom_design=design,
                    description=f'Diseño personalizado: patrón {design.pattern}, talla {design.size}. {design.notes}',
                    color=f'Base {design.base_color}; acentos {design.accent_color_one} y {design.accent_color_two}',
                    size=design.size,
                    production_time={'S': '12-15 días', 'M': '18-22 días', 'L': '22-28 días', 'XL': '25-30 días'}[design.size],
                    price=design.estimated_price,
                    stock=1,
                    made_to_order=True,
                    active=False,
                )
                cart = _cart(request)
                cart[str(product.id)] = 1
                request.session.modified = True
                messages.success(request, 'Tu manta personalizada fue agregada al carrito.')
                return redirect('store:cart')
    return render(request, 'store/custom_designer_real.html', {'prices': prices, 'patterns': patterns})


@login_required
def cart(request):
    _customer_for(request)
    items, total = _cart_items(request)
    return render(request, 'store/cart_pro.html', {'items': items, 'total': total})


@require_POST
@login_required
def add_to_cart(request, product_id):
    _customer_for(request)
    product = get_object_or_404(Product, id=product_id, active=True)
    requested_quantity = int(request.POST.get('quantity', 1))
    if product.stock < 1:
        messages.error(request, 'Este producto no tiene unidades disponibles.')
        return redirect('store:product_detail', product_id=product.id)
    cart = _cart(request)
    current_quantity = int(cart.get(str(product.id), 0))
    cart[str(product.id)] = min(max(requested_quantity, 1) + current_quantity, product.stock)
    request.session.modified = True
    messages.success(request, f'{product.name} fue agregado al carrito.')
    return redirect('store:cart')


@require_POST
@login_required
def update_cart(request, product_id):
    _customer_for(request)
    cart = _cart(request)
    if str(product_id) not in cart:
        raise Http404
    product = get_object_or_404(Product, id=product_id, active=True)
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = min(quantity, product.stock)
    request.session.modified = True
    return redirect('store:cart')


@require_POST
@login_required
def remove_from_cart(request, product_id):
    _customer_for(request)
    cart = _cart(request)
    cart.pop(str(product_id), None)
    request.session.modified = True
    return redirect('store:cart')


@login_required
def checkout(request):
    customer_profile = _customer_for(request)
    items, total = _cart_items(request)
    if not items:
        messages.error(request, 'Tu carrito está vacío.')
        return redirect('store:catalog')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = customer_profile.email
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        if not all([name, email, address, city]):
            messages.error(request, 'Completa nombre, correo, ciudad y dirección de entrega.')
        else:
            with transaction.atomic():
                customer, _ = Customer.objects.update_or_create(
                    email=email,
                    defaults={'name': name, 'phone': phone, 'address': address, 'city': city},
                )
                order = Order.objects.create(customer=customer, shipping_address=f'{address}, {city}')
                for item in items:
                    product = Product.objects.select_for_update().get(id=item['product'].id)
                    if product.stock < item['quantity']:
                        transaction.set_rollback(True)
                        messages.error(request, f'No hay suficientes unidades de {product.name}.')
                        return redirect('store:cart')
                    OrderItem.objects.create(order=order, product=product, quantity=item['quantity'], unit_price=product.price)
                    product.stock -= item['quantity']
                    product.save(update_fields=['stock', 'updated_at'])
            request.session['cart'] = {}
            request.session.modified = True
            return redirect('store:order_confirmation', order_id=order.id)
    return render(request, 'store/checkout_pro.html', {'items': items, 'total': total})


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    if not request.user.is_staff:
        if hasattr(request.user, 'craftswoman_profile'):
            if order.craftswoman_id != request.user.craftswoman_profile.id:
                raise PermissionDenied('No tienes acceso a este pedido.')
        elif order.customer.user_id != request.user.id:
            raise PermissionDenied('No tienes acceso a este pedido.')
    return render(request, 'store/order_confirmation_pro.html', {'order': order})
