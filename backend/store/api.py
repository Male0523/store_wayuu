from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import Category, Craftswoman, CustomDesign, Customer, Order, OrderItem, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'description')


class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'active')
        read_only_fields = ('id',)


class CraftswomanSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Craftswoman
        fields = ('id', 'name', 'community', 'region', 'biography')


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    craftswoman = CraftswomanSummarySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'sku', 'name', 'category', 'craftswoman', 'description', 'region',
            'color', 'size', 'production_time', 'price', 'stock', 'image_url',
            'made_to_order', 'created_at', 'updated_at',
        )


class AdminProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    craftswoman = serializers.PrimaryKeyRelatedField(
        queryset=Craftswoman.objects.all(), required=False, allow_null=True,
    )

    class Meta:
        model = Product
        fields = (
            'id', 'sku', 'name', 'category', 'craftswoman', 'description', 'region',
            'color', 'size', 'production_time', 'price', 'stock', 'image_url',
            'made_to_order', 'active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProductSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'image_url', 'price')


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSummarySerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'quantity', 'unit_price', 'subtotal')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    craftswoman = CraftswomanSummarySerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'status', 'status_label', 'payment_method', 'shipping_address',
            'notes', 'created_at', 'updated_at', 'items', 'total', 'craftswoman',
        )


class CustomDesignSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    craftswoman_name = serializers.CharField(source='craftswoman.name', read_only=True, allow_null=True, default=None)

    class Meta:
        model = CustomDesign
        fields = (
            'id', 'pattern', 'base_color', 'accent_color_one', 'accent_color_two',
            'size', 'quantity', 'notes', 'estimated_price', 'status', 'status_label',
            'created_at', 'craftswoman_name',
        )


class CustomerRegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Ese nombre de usuario ya está registrado.')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if Customer.objects.filter(email__iexact=value).exists() or User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ese correo ya está registrado.')
        return value

    def validate_password(self, value):
        try:
            from django.contrib.auth.password_validation import validate_password
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        phone = validated_data.pop('phone', '')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=password,
            first_name=validated_data['name'],
        )
        Customer.objects.create(user=user, name=validated_data['name'], email=validated_data['email'], phone=phone)
        return user


class CraftswomanRegistrationSerializer(CustomerRegistrationSerializer):
    community = serializers.CharField(max_length=150, required=False, allow_blank=True)
    region = serializers.CharField(max_length=100, required=False, allow_blank=True)

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        community = validated_data.pop('community', '')
        region = validated_data.pop('region', '')
        phone = validated_data.pop('phone', '')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=password,
            first_name=validated_data['name'],
        )
        Craftswoman.objects.create(
            user=user,
            name=validated_data['name'],
            community=community,
            region=region,
            phone=phone,
            active=False,
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ('name', 'email', 'phone', 'address', 'city')
        read_only_fields = ('email',)


class CartItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class CheckoutSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=500)
    city = serializers.CharField(max_length=100)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices, default=Order.PaymentMethod.CONTACT)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class CustomDesignInputSerializer(serializers.Serializer):
    pattern = serializers.ChoiceField(choices=('rombos', 'olas', 'estrellas', 'caminos'))
    base_color = serializers.RegexField(r'^#[0-9a-fA-F]{6}$')
    accent_color_one = serializers.RegexField(r'^#[0-9a-fA-F]{6}$')
    accent_color_two = serializers.RegexField(r'^#[0-9a-fA-F]{6}$')
    size = serializers.ChoiceField(choices=CustomDesign.Size.choices, default=CustomDesign.Size.M)
    quantity = serializers.IntegerField(min_value=1, max_value=20, default=1)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class StatusInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


def _user_payload(user):
    payload = {
        'id': user.id,
        'username': user.username,
        'name': user.get_full_name() or user.username,
        'email': user.email,
        'role': 'admin' if user.is_staff else 'customer',
        'profile': None,
    }
    if hasattr(user, 'craftswoman_profile'):
        profile = user.craftswoman_profile
        payload.update(role='craftswoman', profile={
            'id': profile.id,
            'name': profile.name,
            'community': profile.community,
            'region': profile.region,
            'phone': profile.phone,
            'active': profile.active,
        })
    elif hasattr(user, 'customer_profile'):
        payload['profile'] = ProfileSerializer(user.customer_profile).data
    return payload


def _customer_for(user):
    if user.is_staff or hasattr(user, 'craftswoman_profile'):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied('Esta acción solo está disponible para clientes.')
    customer, _ = Customer.objects.get_or_create(
        user=user,
        defaults={
            'name': user.get_full_name() or user.username,
            'email': user.email or f'{user.username}@sin-correo.local',
        },
    )
    return customer


def _cart_for(request):
    cart = request.session.get('cart')
    if not isinstance(cart, dict):
        cart = {}
        request.session['cart'] = cart
    return cart


def _cart_items(request, customer):
    cart = _cart_for(request)
    product_ids = [int(key) for key in cart if str(key).isdigit()]
    products = Product.objects.filter(id__in=product_ids).select_related('category', 'craftswoman', 'custom_design', 'custom_design__customer')
    items = []
    total = Decimal('0')
    for product in products:
        if not product.active and (not product.custom_design_id or product.custom_design.customer_id != customer.id):
            continue
        quantity = min(max(int(cart.get(str(product.id), 0)), 0), product.stock)
        if not quantity:
            continue
        subtotal = product.price * quantity
        items.append({'product': ProductSerializer(product).data, 'quantity': quantity, 'subtotal': str(subtotal)})
        total += subtotal
    return items, total


def _customer_orders(user):
    if user.is_staff:
        return Order.objects.all()
    if hasattr(user, 'craftswoman_profile'):
        return Order.objects.filter(craftswoman=user.craftswoman_profile)
    return Order.objects.filter(customer__user=user)


@api_view(('GET',))
@permission_classes((AllowAny,))
def api_health(request):
    return Response({'status': 'ok', 'api_version': '1'})


@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({'detail': 'CSRF cookie disponible.'})


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PaginatedAPIView(APIView):
    pagination_class = StandardResultsSetPagination

    def paginate_queryset(self, queryset):
        self.paginator = getattr(self, 'paginator', None) or self.pagination_class()
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)


class CategoryListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        categories = Category.objects.filter(active=True, products__active=True).distinct()
        return Response(CategorySerializer(categories, many=True).data)


class ProductListView(PaginatedAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        products = Product.objects.filter(active=True).select_related('category', 'craftswoman')
        search = request.query_params.get('search', '').strip()
        if search:
            products = products.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
                | models.Q(color__icontains=search)
                | models.Q(region__icontains=search)
            )
        category_id = request.query_params.get('category')
        if category_id:
            if not category_id.isdigit():
                raise serializers.ValidationError({'category': 'Debe ser un identificador numérico.'})
            products = products.filter(category_id=int(category_id))
        color = request.query_params.get('color', '').strip()
        if color:
            products = products.filter(color__icontains=color)
        size = request.query_params.get('size', '').strip()
        if size:
            products = products.filter(size__iexact=size)
        available = request.query_params.get('available')
        if available in ('true', '1'):
            products = products.filter(models.Q(stock__gt=0) | models.Q(made_to_order=True))
        ordering = request.query_params.get('ordering')
        if ordering in ('price', '-price', 'name', '-created_at'):
            products = products.order_by(ordering)
        page = self.paginate_queryset(products)
        return self.get_paginated_response(ProductSerializer(page, many=True).data)


class ProductDetailView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, product_id):
        product = get_object_or_404(
            Product.objects.select_related('category', 'craftswoman'), id=product_id, active=True,
        )
        return Response(ProductSerializer(product).data)


class AdminProductListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        products = Product.objects.select_related('category', 'craftswoman').all()
        return Response(AdminProductSerializer(products, many=True).data)

    def post(self, request):
        serializer = AdminProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(AdminProductSerializer(product).data, status=status.HTTP_201_CREATED)


class AdminCategoryListView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        return Response(AdminCategorySerializer(Category.objects.all(), many=True).data)

    def post(self, request):
        serializer = AdminCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(AdminCategorySerializer(category).data, status=status.HTTP_201_CREATED)


class AdminCategoryDetailView(APIView):
    permission_classes = (IsAdminUser,)

    def patch(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        serializer = AdminCategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(AdminCategorySerializer(serializer.save()).data)


class AdminProductDetailView(APIView):
    permission_classes = (IsAdminUser,)

    def patch(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        serializer = AdminProductSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(AdminProductSerializer(product).data)


class AdminOrderStatusView(APIView):
    permission_classes = (IsAdminUser,)

    def patch(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.status = serializer.validated_data['status']
        order.save(update_fields=('status', 'updated_at'))
        return Response(OrderSerializer(order).data)


class CustomerRegistrationView(APIView):
    permission_classes = (AllowAny,)

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response({'user': _user_payload(user)}, status=status.HTTP_201_CREATED)


class CraftswomanRegistrationView(CustomerRegistrationView):
    def post(self, request):
        serializer = CraftswomanRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response({'user': _user_payload(user)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = (AllowAny,)

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response({'detail': 'Usuario o contraseña incorrectos.'}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response({'user': _user_payload(user)})


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({'user': _user_payload(request.user)})


class CustomerProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        customer = _customer_for(request.user)
        return Response(ProfileSerializer(customer).data)

    def patch(self, request):
        customer = _customer_for(request.user)
        serializer = ProfileSerializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        if 'name' in serializer.validated_data:
            request.user.first_name = customer.name
            request.user.save(update_fields=('first_name',))
        return Response(serializer.data)


class CartView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        customer = _customer_for(request.user)
        items, total = _cart_items(request, customer)
        return Response({'items': items, 'total': str(total), 'count': sum(item['quantity'] for item in items)})


class CartItemListView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        _customer_for(request.user)
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(Product, id=serializer.validated_data['product_id'], active=True)
        quantity = serializer.validated_data['quantity']
        cart = _cart_for(request)
        key = str(product.id)
        new_quantity = int(cart.get(key, 0)) + quantity
        if product.stock < new_quantity:
            return Response({'detail': 'No hay suficientes unidades disponibles.'}, status=status.HTTP_400_BAD_REQUEST)
        cart[key] = new_quantity
        request.session.modified = True
        return Response({'detail': 'Producto agregado.', 'product_id': product.id, 'quantity': new_quantity}, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request, product_id):
        _customer_for(request.user)
        cart = _cart_for(request)
        key = str(product_id)
        if key not in cart:
            return Response({'detail': 'El producto no está en el carrito.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CartQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(Product, id=product_id, active=True)
        quantity = serializer.validated_data['quantity']
        if quantity > product.stock:
            return Response({'detail': 'No hay suficientes unidades disponibles.'}, status=status.HTTP_400_BAD_REQUEST)
        cart[key] = quantity
        request.session.modified = True
        return Response({'detail': 'Carrito actualizado.', 'product_id': product.id, 'quantity': quantity})

    def delete(self, request, product_id):
        _customer_for(request.user)
        cart = _cart_for(request)
        cart.pop(str(product_id), None)
        request.session.modified = True
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        customer = _customer_for(request.user)
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items, _ = _cart_items(request, customer)
        if not items:
            return Response({'detail': 'Tu carrito está vacío.'}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        with transaction.atomic():
            order = Order.objects.create(
                customer=customer,
                payment_method=data['payment_method'],
                shipping_address=f"{data['address'].strip()}, {data['city'].strip()}",
                notes=data.get('notes', '').strip(),
            )
            for item in items:
                product = Product.objects.select_for_update().get(id=item['product']['id'])
                if product.stock < item['quantity']:
                    raise serializers.ValidationError({'detail': f'No hay suficientes unidades de {product.name}.'})
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    unit_price=product.price,
                )
                product.stock -= item['quantity']
                product.save(update_fields=('stock', 'updated_at'))
            customer.address = data['address'].strip()
            customer.city = data['city'].strip()
            customer.save(update_fields=('address', 'city'))
        request.session['cart'] = {}
        request.session.modified = True
        order = Order.objects.prefetch_related('items__product').select_related('craftswoman').get(id=order.id)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(PaginatedAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        orders = _customer_orders(request.user).select_related('craftswoman').prefetch_related('items__product')
        return self.get_paginated_response(OrderSerializer(self.paginate_queryset(orders), many=True).data)


class OrderDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, order_id):
        order = get_object_or_404(
            _customer_orders(request.user).select_related('craftswoman').prefetch_related('items__product'),
            id=order_id,
        )
        return Response(OrderSerializer(order).data)


class CustomDesignListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        customer = _customer_for(request.user)
        designs = customer.custom_designs.select_related('craftswoman')
        return Response(CustomDesignSerializer(designs, many=True).data)

    def post(self, request):
        customer = _customer_for(request.user)
        serializer = CustomDesignInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        prices = {'S': Decimal('100000'), 'M': Decimal('120000'), 'L': Decimal('145000'), 'XL': Decimal('175000')}
        lead_times = {'S': '12-15 días', 'M': '18-22 días', 'L': '22-28 días', 'XL': '25-30 días'}
        with transaction.atomic():
            design = CustomDesign.objects.create(
                customer=customer,
                pattern=data['pattern'],
                base_color=data['base_color'],
                accent_color_one=data['accent_color_one'],
                accent_color_two=data['accent_color_two'],
                size=data['size'],
                quantity=data['quantity'],
                notes=data.get('notes', '').strip(),
                estimated_price=prices[data['size']] * data['quantity'],
            )
            category, _ = Category.objects.get_or_create(
                name='Diseños personalizados',
                defaults={'description': 'Mantas configuradas por clientes.', 'active': True},
            )
            product = Product.objects.create(
                sku=f'DISENO-{design.pk:05d}',
                name=f"Manta personalizada · {design.pattern.title()}",
                category=category,
                custom_design=design,
                description=f"Diseño personalizado: patrón {design.pattern}, talla {design.size}. {design.notes}",
                color=f"Base {design.base_color}; acentos {design.accent_color_one} y {design.accent_color_two}",
                size=design.size,
                production_time=lead_times[design.size],
                price=design.estimated_price,
                stock=1,
                made_to_order=True,
                active=False,
            )
        cart = _cart_for(request)
        cart[str(product.id)] = 1
        request.session.modified = True
        return Response(
            {**CustomDesignSerializer(design).data, 'product_id': product.id},
            status=status.HTTP_201_CREATED,
        )


class CraftswomanDashboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        craftswoman = get_object_or_404(Craftswoman, user=request.user)
        available = Order.objects.filter(
            craftswoman__isnull=True, status=Order.Status.PENDING,
        ).select_related('craftswoman').prefetch_related('items__product') if craftswoman.active else Order.objects.none()
        assigned = craftswoman.orders.select_related('craftswoman').prefetch_related('items__product')
        designs = craftswoman.custom_designs.select_related('customer')
        return Response({
            'active': craftswoman.active,
            'available_orders': OrderSerializer(available, many=True).data,
            'orders': OrderSerializer(assigned, many=True).data,
            'designs': CustomDesignSerializer(designs, many=True).data,
        })


class AcceptOrderView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, order_id):
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        with transaction.atomic():
            order = get_object_or_404(
                Order.objects.select_for_update(),
                id=order_id,
                craftswoman__isnull=True,
                status=Order.Status.PENDING,
            )
            order.craftswoman = craftswoman
            order.status = Order.Status.ACCEPTED
            order.save(update_fields=('craftswoman', 'status', 'updated_at'))
            for item in order.items.select_related('product__custom_design'):
                design = getattr(item.product, 'custom_design', None)
                if design:
                    design.craftswoman = craftswoman
                    design.status = Order.Status.ACCEPTED
                    design.save(update_fields=('craftswoman', 'status'))
        return Response(OrderSerializer(order).data)


class CraftswomanOrderStatusView(APIView):
    permission_classes = (IsAuthenticated,)
    transitions = {
        Order.Status.ACCEPTED: {Order.Status.WEAVING},
        Order.Status.WEAVING: {Order.Status.ACCEPTED, Order.Status.COMPLETED},
    }

    def patch(self, request, order_id):
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        order = get_object_or_404(Order, id=order_id, craftswoman=craftswoman)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        if new_status not in self.transitions.get(order.status, set()):
            return Response({'detail': 'Transición de estado no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            order.status = new_status
            order.save(update_fields=('status', 'updated_at'))
            for item in order.items.select_related('product__custom_design'):
                design = getattr(item.product, 'custom_design', None)
                if design and design.craftswoman_id == craftswoman.id:
                    design.status = new_status
                    design.save(update_fields=('status',))
        return Response(OrderSerializer(order).data)


class CraftswomanDesignStatusView(APIView):
    permission_classes = (IsAuthenticated,)
    transitions = CraftswomanOrderStatusView.transitions

    def patch(self, request, design_id):
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        design = get_object_or_404(CustomDesign, id=design_id, craftswoman=craftswoman)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        if new_status not in self.transitions.get(design.status, set()):
            return Response({'detail': 'Transición de estado no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
        design.status = new_status
        design.save(update_fields=('status',))
        return Response({'id': design.id, 'status': design.status})