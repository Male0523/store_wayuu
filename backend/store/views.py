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

from .models import AccessRole, AuditEvent, Category, Craftswoman, CustomerCartItem, CustomDesign, Customer, Order, OrderItem, Product
from .cart_services import MAX_CART_QUANTITY, merge_legacy_session_cart
from .order_workflow import allowed_order_transitions, can_transition_order, has_custom_design_items
from .rbac import assign_role, has_permission as has_rbac_permission, has_role, record_audit, role_for_user


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


def _assign_access_role(user, role_code):
    """Registra el nivel de acceso en la base de datos al crear una cuenta."""
    return assign_role(user, role_code)


def validate_email_safely(email):
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


def _customer_for(request):
    """Autoriza únicamente una cuenta de cliente y devuelve su perfil."""
    if not has_role(request.user, AccessRole.Code.CUSTOMER):
        raise PermissionDenied('Esta acción solo está disponible para clientes.')
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email or f'{request.user.username}@sin-correo.local',
        },
    )
    return customer


def _require_permission(request, resource, action):
    if not has_rbac_permission(request.user, resource, action):
        record_audit(
            request.user,
            f'denied_{action}',
            resource,
            result=AuditEvent.Result.DENIED,
        )
        raise PermissionDenied('Tu rol no tiene permiso para esta operación.')


def _cart_items(request):
    customer = _customer_for(request)
    merge_legacy_session_cart(request, customer)
    rows = CustomerCartItem.objects.filter(customer=customer).select_related(
        'product__category', 'product__craftswoman', 'product__custom_design',
        'product__custom_design__customer',
    )
    items = []
    total = Decimal('0')
    for row in rows:
        product = row.product
        if product.custom_design_id and product.custom_design.customer_id != customer.id:
            continue
        quantity = row.quantity
        if quantity < 1:
            continue
        subtotal = product.price * quantity
        available = bool(
            product.stock >= quantity
            and (product.active or product.custom_design_id)
            and (not product.custom_design_id or quantity == 1)
        )
        items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal, 'available': available})
        total += subtotal
    return items, total


def _hero_image_from_beta():
    """Recupera la fotografía de portada original incluida en el prototipo."""
    source = Path(settings.BASE_DIR).parent / 'mantas_wayuu_beta_6.0.html'
    if not source.exists():
        return ''
    match = re.search(r'class="hero-art">\s*<img src="(?P<image>data:image/[^\"]+)', source.read_text(encoding='utf-8'))
    return match.group('image') if match else ''


def catalog(request):
    products = Product.objects.filter(
        active=True, custom_design__isnull=True,
        category__active=True, category__is_internal=False,
    ).select_related('category', 'craftswoman')
    role = role_for_user(request.user)
    is_craftswoman = role is not None and role.code == AccessRole.Code.CRAFTSWOMAN
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
        'is_customer': role is not None and role.code == AccessRole.Code.CUSTOMER,
    })


def login_view(request):
    if request.user.is_authenticated:
        role = role_for_user(request.user)
        if role and role.code == AccessRole.Code.CUSTOMER:
            return redirect('store:customer_dashboard')
        if role and role.code == AccessRole.Code.CRAFTSWOMAN:
            return redirect('store:craftswoman_dashboard')
        if role and role.code in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN):
            return redirect('/admin/')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            role = role_for_user(user)
            if role is None:
                messages.error(request, 'Tu cuenta no tiene un rol asignado. Contacta a administración.')
            else:
                login(request, user)
                if role.code in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN):
                    return redirect('/admin/')
                if role.code == AccessRole.Code.CRAFTSWOMAN:
                    return redirect('store:craftswoman_dashboard')
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
@require_POST
def logout_view(request):
    logout(request)
    return redirect('store:catalog')


@login_required
def customer_dashboard(request):
    _require_permission(request, 'orders', 'view')
    _require_permission(request, 'designs', 'view')
    customer = _customer_for(request)
    return render(request, 'store/customer_dashboard_pro.html', {'customer': customer, 'orders': customer.orders.prefetch_related('items__product'), 'designs': customer.custom_designs.all()})


@login_required
def account_settings(request):
    """Perfil de cliente: los datos se actualizan sin salir de su cuenta."""
    _require_permission(request, 'customers', 'change' if request.method == 'POST' else 'view')
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
    if not has_role(request.user, AccessRole.Code.CRAFTSWOMAN):
        raise PermissionDenied('Esta cuenta no tiene rol de tejedora.')
    _require_permission(request, 'orders', 'view')
    try:
        craftswoman = request.user.craftswoman_profile
    except Craftswoman.DoesNotExist:
        messages.error(request, 'Esta cuenta no es de tejedora.')
        return redirect('store:customer_dashboard')
    if not craftswoman.active:
        raise PermissionDenied('La cuenta de tejedora todavía no está activada.')
    available_orders = Order.objects.filter(
        craftswoman__isnull=True, status=Order.Status.PENDING,
    ).select_related('customer')
    orders = craftswoman.orders.select_related('customer').prefetch_related(
        'items__product__custom_design',
    )
    may_change_orders = has_rbac_permission(request.user, 'orders', 'change')
    may_change_designs = has_rbac_permission(request.user, 'designs', 'change')
    for order in orders:
        has_designs = has_custom_design_items(order)
        order.allowed_statuses = (
            allowed_order_transitions(order.status, 'craftswoman')
            if may_change_orders and (may_change_designs or not has_designs)
            else []
        )
        order.allowed_status_options = [
            (value, Order.Status(value).label) for value in order.allowed_statuses
        ]
    may_view_designs = has_rbac_permission(request.user, 'designs', 'view')
    designs = craftswoman.custom_designs.select_related('customer') if may_view_designs else CustomDesign.objects.none()
    for design in designs:
        design.allowed_statuses = (
            allowed_order_transitions(design.status, 'craftswoman')
            if may_change_designs else []
        )
        design.allowed_status_options = [
            (value, Order.Status(value).label) for value in design.allowed_statuses
        ]
    return render(request, 'store/craftswoman_dashboard_pro.html', {
        'craftswoman': craftswoman,
        'orders': orders,
        'designs': designs,
        'available_orders': available_orders,
    })


@login_required
@require_POST
def accept_order(request, order_id):
    if not has_role(request.user, AccessRole.Code.CRAFTSWOMAN):
        raise PermissionDenied('Esta operación solo está disponible para tejedoras.')
    _require_permission(request, 'orders', 'change')
    craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), id=order_id, craftswoman__isnull=True, status=Order.Status.PENDING)
        items = list(order.items.select_related('product__custom_design'))
        if not can_transition_order(order.status, Order.Status.ACCEPTED, 'assignment'):
            return redirect('store:craftswoman_dashboard')
        if any(item.product.custom_design_id for item in items):
            _require_permission(request, 'designs', 'change')
        order.craftswoman = craftswoman
        order.status = Order.Status.ACCEPTED
        order.save(update_fields=['craftswoman', 'status', 'updated_at'])
        for item in items:
            if item.product.custom_design_id:
                design = item.product.custom_design
                design.craftswoman = craftswoman
                design.status = Order.Status.ACCEPTED
                design.save(update_fields=['craftswoman', 'status'])
        record_audit(
            request.user,
            'accept_order',
            'orders',
            affected_user=order.customer.user,
            details={'status': order.status, 'craftswoman_id': craftswoman.id},
            instance=order,
        )
    messages.success(request, f'El pedido #{order.id} fue asignado a tu taller.')
    return redirect('store:craftswoman_dashboard')


@login_required
@require_POST
def update_order_status(request, order_id):
    if not has_role(request.user, AccessRole.Code.CRAFTSWOMAN):
        raise PermissionDenied('Esta operación solo está disponible para tejedoras.')
    _require_permission(request, 'orders', 'change')
    craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update().select_related('customer__user').filter(craftswoman=craftswoman),
            id=order_id,
        )
        if has_custom_design_items(order):
            _require_permission(request, 'designs', 'change')
        next_status = request.POST.get('status')
        if can_transition_order(order.status, next_status, 'craftswoman'):
            previous_status = order.status
            order.status = next_status
            order.save(update_fields=['status', 'updated_at'])
            for item in order.items.select_related('product__custom_design'):
                if item.product.custom_design_id:
                    design = item.product.custom_design
                    if design.craftswoman_id == craftswoman.id:
                        design.status = next_status
                        design.save(update_fields=['status'])
            record_audit(
                request.user,
                'craftswoman_change_order_status',
                'orders',
                affected_user=order.customer.user,
                details={'from': previous_status, 'to': next_status},
                instance=order,
            )
            messages.success(request, f'Pedido #{order.id} actualizado a “{order.get_status_display()}”.')
        else:
            messages.error(request, 'La transición de estado solicitada no está permitida.')
    return redirect('store:craftswoman_dashboard')


@login_required
@require_POST
def update_design_status(request, design_id):
    if not has_role(request.user, AccessRole.Code.CRAFTSWOMAN):
        raise PermissionDenied('Esta operación solo está disponible para tejedoras.')
    _require_permission(request, 'designs', 'change')
    craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
    with transaction.atomic():
        design = get_object_or_404(
            CustomDesign.objects.select_for_update().filter(craftswoman=craftswoman),
            id=design_id,
        )
        next_status = request.POST.get('status')
        if can_transition_order(design.status, next_status, 'craftswoman'):
            previous_status = design.status
            design.status = next_status
            design.save(update_fields=['status'])
            record_audit(
                request.user,
                'craftswoman_change_design_status',
                'designs',
                affected_user=design.customer.user,
                details={'from': previous_status, 'to': next_status},
                instance=design,
            )
            messages.success(request, f'Diseño #{design.id} actualizado a “{design.get_status_display()}”.')
        else:
            messages.error(request, 'La transición de estado solicitada no está permitida.')
    return redirect('store:craftswoman_dashboard')


def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related('category', 'craftswoman'), id=product_id, active=True,
        custom_design__isnull=True, category__active=True, category__is_internal=False,
    )
    role = role_for_user(request.user)
    is_craftswoman = role is not None and role.code == AccessRole.Code.CRAFTSWOMAN
    if is_craftswoman:
        profile = request.user.craftswoman_profile
        if product.craftswoman_id != profile.id and product.region.lower() != profile.region.lower():
            raise PermissionDenied('Las tejedoras solo pueden consultar su catálogo regional.')
    can_shop = role is not None and role.code == AccessRole.Code.CUSTOMER
    return render(request, 'store/product_detail_pro.html', {'product': product, 'can_shop': can_shop})


@login_required
def custom_designer(request):
    _require_permission(request, 'designs', 'add' if request.method == 'POST' else 'view')
    if request.method == 'POST':
        _require_permission(request, 'cart', 'add')
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
                pattern = request.POST.get('pattern', 'rombos')
                colors = [request.POST.get(key, default) for key, default in (
                    ('base_color', '#F5F0EB'),
                    ('accent_color_one', '#C67B5C'),
                    ('accent_color_two', '#45634E'),
                )]
                notes = request.POST.get('notes', '').strip()
                try:
                    quantity = int(request.POST.get('quantity', 1))
                except (TypeError, ValueError):
                    quantity = 0
                valid_patterns = {value for value, _label in patterns}
                if pattern not in valid_patterns or any(not re.fullmatch(r'#[0-9a-fA-F]{6}', color) for color in colors):
                    messages.error(request, 'Revisa el patrón y los colores seleccionados.')
                elif size not in prices or not 1 <= quantity <= 20 or len(notes) > 2000:
                    messages.error(request, 'Revisa la talla, cantidad e indicaciones del diseño.')
                else:
                    if customer.name != name:
                        customer.name = name
                        customer.save(update_fields=['name'])
                    with transaction.atomic():
                        design = CustomDesign.objects.create(customer=customer, pattern=pattern, base_color=colors[0], accent_color_one=colors[1], accent_color_two=colors[2], size=size, quantity=quantity, notes=notes, estimated_price=prices[size] * quantity)
                        category, _ = Category.objects.get_or_create(
                            name='Diseños personalizados',
                            defaults={'description': 'Mantas configuradas por clientes.', 'active': True, 'is_internal': True},
                        )
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
                        record_audit(
                            request.user,
                            'create_custom_design',
                            'designs',
                            affected_user=request.user,
                            instance=design,
                        )
                        CustomerCartItem.objects.update_or_create(
                            customer=customer,
                            product=product,
                            defaults={'quantity': 1},
                        )
                    messages.success(request, 'Tu manta personalizada fue agregada al carrito.')
                    return redirect('store:cart')
    return render(request, 'store/custom_designer_real.html', {'prices': prices, 'patterns': patterns})


@login_required
def cart(request):
    _require_permission(request, 'cart', 'view')
    _customer_for(request)
    items, total = _cart_items(request)
    return render(request, 'store/cart_pro.html', {'items': items, 'total': total})


@require_POST
@login_required
def add_to_cart(request, product_id):
    _require_permission(request, 'cart', 'add')
    customer = _customer_for(request)
    try:
        requested_quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        requested_quantity = 0
    if requested_quantity < 1 or requested_quantity > MAX_CART_QUANTITY:
        messages.error(request, f'La cantidad debe estar entre 1 y {MAX_CART_QUANTITY}.')
        return redirect('store:product_detail', product_id=product_id)
    merge_legacy_session_cart(request, customer)
    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(pk=customer.pk)
        product = get_object_or_404(Product.objects.select_for_update(), id=product_id, active=True, custom_design__isnull=True)
        row, created = CustomerCartItem.objects.select_for_update().get_or_create(
            customer=customer, product=product, defaults={'quantity': requested_quantity},
        )
        next_quantity = row.quantity if created else row.quantity + requested_quantity
        if product.stock < next_quantity:
            if created:
                row.delete()
            messages.error(request, 'No hay suficientes unidades disponibles.')
            return redirect('store:product_detail', product_id=product.id)
        if not created:
            row.quantity = next_quantity
            row.save(update_fields=('quantity', 'updated_at'))
    messages.success(request, f'{product.name} fue agregado al carrito.')
    return redirect('store:cart')


@require_POST
@login_required
def update_cart(request, product_id):
    _require_permission(request, 'cart', 'change')
    customer = _customer_for(request)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 0
    if quantity < 1:
        return remove_from_cart(request, product_id)
    if quantity > MAX_CART_QUANTITY:
        messages.error(request, f'La cantidad no puede superar {MAX_CART_QUANTITY}.')
        return redirect('store:cart')
    merge_legacy_session_cart(request, customer)
    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(pk=customer.pk)
        product = get_object_or_404(
            Product.objects.select_for_update().filter(
                models.Q(active=True, custom_design__isnull=True)
                | models.Q(custom_design__customer=customer),
            ).distinct(),
            id=product_id,
        )
        row = get_object_or_404(CustomerCartItem.objects.select_for_update(), customer=customer, product=product)
        if product.custom_design_id and quantity != 1:
            messages.error(request, 'La cantidad del diseño personalizado ya está incluida en su precio.')
            return redirect('store:cart')
        if quantity > product.stock:
            messages.error(request, 'No hay suficientes unidades disponibles para esa cantidad.')
            return redirect('store:cart')
        row.quantity = quantity
        row.save(update_fields=('quantity', 'updated_at'))
    return redirect('store:cart')


@require_POST
@login_required
def remove_from_cart(request, product_id):
    _require_permission(request, 'cart', 'delete')
    customer = _customer_for(request)
    merge_legacy_session_cart(request, customer)
    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(pk=customer.pk)
        CustomerCartItem.objects.filter(customer=customer, product_id=product_id).delete()
    return redirect('store:cart')


@login_required
def checkout(request):
    if request.method == 'POST':
        _require_permission(request, 'orders', 'add')
        _require_permission(request, 'customers', 'change')
    else:
        _require_permission(request, 'cart', 'view')
    customer_profile = _customer_for(request)
    items = []
    total = Decimal('0')
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
                customer_profile = Customer.objects.select_for_update().get(pk=customer_profile.pk)
                merge_legacy_session_cart(request, customer_profile)
                cart_rows = list(
                    CustomerCartItem.objects.select_for_update()
                    .filter(customer=customer_profile).order_by('product_id')
                )
                if not cart_rows:
                    messages.error(request, 'Tu carrito está vacío.')
                    return redirect('store:cart')
                products = {
                    product.pk: product
                    for product in Product.objects.select_for_update().filter(
                        pk__in=[row.product_id for row in cart_rows],
                    ).select_related('custom_design').order_by('pk')
                }
                for row in cart_rows:
                    product = products.get(row.product_id)
                    if not product or row.quantity < 1 or row.quantity > MAX_CART_QUANTITY:
                        messages.error(request, 'El carrito contiene un producto o una cantidad no válida. Revísalo antes de continuar.')
                        return redirect('store:cart')
                    if product.custom_design_id:
                        if product.custom_design.customer_id != customer_profile.id or row.quantity != 1:
                            messages.error(request, 'El diseño personalizado no pertenece a esta cuenta o su cantidad no es válida.')
                            return redirect('store:cart')
                    elif not product.active:
                        messages.error(request, f'{product.name} ya no está disponible. Retíralo del carrito para continuar.')
                        return redirect('store:cart')
                    if product.stock < row.quantity:
                        messages.error(request, f'No hay suficientes unidades de {product.name}. Ajusta la cantidad antes de confirmar.')
                        return redirect('store:cart')
                customer_profile.name = name
                customer_profile.phone = phone
                customer_profile.address = address
                customer_profile.city = city
                customer_profile.save(update_fields=['name', 'phone', 'address', 'city'])
                order = Order.objects.create(
                    customer=customer_profile,
                    shipping_address=f'{address}, {city}',
                )
                for row in cart_rows:
                    product = products[row.product_id]
                    OrderItem.objects.create(order=order, product=product, quantity=row.quantity, unit_price=product.price)
                    product.stock -= row.quantity
                    product.save(update_fields=['stock', 'updated_at'])
                CustomerCartItem.objects.filter(pk__in=[row.pk for row in cart_rows]).delete()
                record_audit(
                    request.user,
                    'checkout',
                    'orders',
                    affected_user=request.user,
                    details={'item_count': len(cart_rows)},
                    instance=order,
                )
            request.session.pop('cart', None)
            request.session.modified = True
            return redirect('store:order_confirmation', order_id=order.id)
    else:
        items, total = _cart_items(request)
        if not items:
            messages.error(request, 'Tu carrito está vacío.')
            return redirect('store:catalog')
    return render(request, 'store/checkout_pro.html', {'items': items, 'total': total})


@login_required
def order_confirmation(request, order_id):
    role = role_for_user(request.user)
    if role is None:
        raise PermissionDenied('Tu cuenta no tiene un rol de acceso asignado.')
    _require_permission(request, 'orders', 'view')
    if role.code == AccessRole.Code.CRAFTSWOMAN:
        order = get_object_or_404(
            Order.objects.prefetch_related('items__product'),
            id=order_id,
            craftswoman__user=request.user,
            craftswoman__active=True,
        )
    elif role.code == AccessRole.Code.CUSTOMER:
        order = get_object_or_404(
            Order.objects.prefetch_related('items__product'),
            id=order_id,
            customer__user=request.user,
        )
    elif role.code in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN):
        order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    else:
        raise PermissionDenied('Tu rol no tiene acceso a este pedido.')
    return render(request, 'store/order_confirmation_pro.html', {'order': order})
