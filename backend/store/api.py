from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import (
    AccessRole,
    AuditEvent,
    Category,
    Craftswoman,
    CustomDesign,
    Customer,
    Order,
    OrderItem,
    PermissionDelegation,
    Product,
    RolePermission,
    UserPermissionGrant,
    UserRole,
)
from .permissions import AdminOrSuperadmin, CraftswomanOnly, CustomerOnly, HasAssignedRole, OrderAccess, SuperadminOnly
from .rbac import (
    PERMISSION_ACTIONS,
    PERMISSION_RESOURCES,
    assign_role,
    can_manage_permission,
    effective_permission_keys,
    has_permission as has_rbac_permission,
    is_explicitly_denied,
    permission_catalog,
    permission_for,
    permission_key,
    record_audit,
    remove_user_permission,
    revoke_admin_delegations,
    role_for_user,
    set_permission_delegation,
    set_role_permission,
    set_user_permission,
)


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


class SuperadminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_name', 'is_active', 'active', 'location', 'profile', 'date_joined',
        )

    @staticmethod
    def assignment(user):
        try:
            return user.access_profile
        except UserRole.DoesNotExist:
            return None

    def get_full_name(self, user):
        return user.get_full_name() or user.username

    def get_role(self, user):
        assignment = self.assignment(user)
        return assignment.role.code if assignment else 'unassigned'

    def get_role_name(self, user):
        assignment = self.assignment(user)
        return assignment.role.name if assignment else 'Sin rol asignado'

    def get_active(self, user):
        if not user.is_active:
            return False
        assignment = self.assignment(user)
        if assignment and assignment.role.code == AccessRole.Code.CRAFTSWOMAN:
            profile = getattr(user, 'craftswoman_profile', None)
            return bool(profile and profile.active)
        return True

    def get_location(self, user):
        assignment = self.assignment(user)
        if assignment and assignment.role.code == AccessRole.Code.CRAFTSWOMAN:
            profile = getattr(user, 'craftswoman_profile', None)
            return profile.community or profile.region if profile else ''
        if assignment and assignment.role.code == AccessRole.Code.CUSTOMER:
            profile = getattr(user, 'customer_profile', None)
            return profile.city if profile else ''
        return ''

    def get_profile(self, user):
        assignment = self.assignment(user)
        if not assignment:
            return None
        if assignment.role.code == AccessRole.Code.CUSTOMER:
            profile = getattr(user, 'customer_profile', None)
            return ProfileSerializer(profile).data if profile else None
        if assignment.role.code == AccessRole.Code.CRAFTSWOMAN:
            profile = getattr(user, 'craftswoman_profile', None)
            if not profile:
                return None
            return {
                'id': profile.id,
                'name': profile.name,
                'phone': profile.phone,
                'community': profile.community,
                'region': profile.region,
                'active': profile.active,
            }
        return None


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
        assign_role(user, AccessRole.Code.CUSTOMER)
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
        assign_role(user, AccessRole.Code.CRAFTSWOMAN)
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


class PermissionInputSerializer(serializers.Serializer):
    resource = serializers.ChoiceField(choices=tuple((key, key) for key in PERMISSION_RESOURCES))
    action = serializers.ChoiceField(choices=tuple((action, action) for action in PERMISSION_ACTIONS))


class RolePermissionChangeSerializer(serializers.Serializer):
    resource = serializers.ChoiceField(choices=tuple((key, key) for key in PERMISSION_RESOURCES))
    action = serializers.ChoiceField(choices=tuple((action, action) for action in PERMISSION_ACTIONS))
    allowed = serializers.BooleanField()


class UserPermissionChangeSerializer(PermissionInputSerializer):
    effect = serializers.ChoiceField(
        choices=UserPermissionGrant.Effect.choices,
        allow_null=True,
    )


class PermissionDelegationChangeSerializer(PermissionInputSerializer):
    admin_user_id = serializers.IntegerField(min_value=1)
    allowed = serializers.BooleanField()


class RoleAssignmentSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=AccessRole.Code.choices)


class SuperadminUserWriteSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=AccessRole.Code.choices, required=False)
    is_active = serializers.BooleanField(required=False, default=True)
    password = serializers.CharField(write_only=True, required=False, min_length=8, max_length=128)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    community = serializers.CharField(max_length=150, required=False, allow_blank=True)
    region = serializers.CharField(max_length=100, required=False, allow_blank=True)
    craftswoman_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        instance = self.instance
        user_id = instance.pk if instance else None
        username = attrs.get('username', instance.username if instance else '')
        email = attrs.get('email', instance.email if instance else '').strip().lower()
        if not instance and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'La contraseña es obligatoria al crear una cuenta.'})
        if not instance and not attrs.get('role'):
            raise serializers.ValidationError({'role': 'Selecciona uno de los cuatro roles fijos.'})
        if User.objects.filter(username__iexact=username).exclude(pk=user_id).exists():
            raise serializers.ValidationError({'username': 'Ese nombre de usuario ya está registrado.'})
        if User.objects.filter(email__iexact=email).exclude(pk=user_id).exists():
            raise serializers.ValidationError({'email': 'Ese correo ya está asociado a otra cuenta.'})
        customer_profiles = Customer.objects.filter(email__iexact=email)
        if user_id is not None:
            customer_profiles = customer_profiles.exclude(user_id=user_id)
        if customer_profiles.exists():
            raise serializers.ValidationError({'email': 'Ese correo ya está asociado a otro perfil de cliente.'})
        password = attrs.get('password')
        if password:
            try:
                from django.contrib.auth.password_validation import validate_password
                validate_password(password, user=instance)
            except DjangoValidationError as error:
                raise serializers.ValidationError({'password': list(error.messages)}) from error
        return attrs


class RoleStateInputSerializer(serializers.Serializer):
    active = serializers.BooleanField()


def _user_payload(user):
    role = role_for_user(user)
    payload = {
        'id': user.id,
        'username': user.username,
        'name': user.get_full_name() or user.username,
        'email': user.email,
        'role': role.code if role else None,
        'permissions': effective_permission_keys(user),
        'profile': None,
    }
    if role and role.code == AccessRole.Code.CRAFTSWOMAN:
        profile = Craftswoman.objects.filter(user=user).first()
        if not profile:
            return payload
        payload.update(role='craftswoman', profile={
            'id': profile.id,
            'name': profile.name,
            'community': profile.community,
            'region': profile.region,
            'phone': profile.phone,
            'active': profile.active,
        })
    elif role and role.code == AccessRole.Code.CUSTOMER:
        customer = Customer.objects.filter(user=user).first()
        if customer:
            payload['profile'] = ProfileSerializer(customer).data
    return payload


def _sync_managed_user_profile(user, role, values):
    name = ' '.join(part for part in (user.first_name, user.last_name) if part).strip() or user.username
    customer_profile = Customer.objects.filter(user=user).first()
    if role.code == AccessRole.Code.CUSTOMER and not customer_profile:
        customer_profile = Customer.objects.create(
            user=user,
            name=name,
            email=user.email,
            phone=values.get('phone', ''),
            address=values.get('address', ''),
            city=values.get('city', ''),
        )
    if customer_profile:
        profile = customer_profile
        profile.name = name
        profile.email = user.email
        for field in ('phone', 'address', 'city'):
            if field in values:
                setattr(profile, field, values[field])
        profile.save()

    craftswoman_profile = Craftswoman.objects.filter(user=user).first()
    if role.code == AccessRole.Code.CRAFTSWOMAN and not craftswoman_profile:
        craftswoman_profile = Craftswoman.objects.create(
            user=user,
            name=name,
            phone=values.get('phone', ''),
            community=values.get('community', ''),
            region=values.get('region', ''),
            active=values.get('craftswoman_active', False),
        )
    if craftswoman_profile:
        profile = craftswoman_profile
        profile.name = name
        for field in ('phone', 'community', 'region'):
            if field in values:
                setattr(profile, field, values[field])
        if 'craftswoman_active' in values:
            profile.active = values['craftswoman_active']
        profile.save()


def _customer_for(user):
    role = role_for_user(user)
    if not role or role.code != AccessRole.Code.CUSTOMER:
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
    role = role_for_user(user)
    if role is None:
        return Order.objects.none()
    if role.code in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN):
        return Order.objects.all()
    if role.code == AccessRole.Code.CRAFTSWOMAN:
        craftswoman = Craftswoman.objects.filter(user=user).first()
        return craftswoman.orders.all() if craftswoman else Order.objects.none()
    if role.code == AccessRole.Code.CUSTOMER:
        return Order.objects.filter(customer__user=user)
    return Order.objects.none()


@api_view(('GET',))
@permission_classes((AllowAny,))
def api_health(request):
    return Response({'status': 'ok', 'api_version': '1'})


@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({
        'detail': 'Token CSRF disponible para el origen autorizado.',
        'csrfToken': get_token(request),
    })


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
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'products'

    def get(self, request):
        products = Product.objects.select_related('category', 'craftswoman').all()
        return Response(AdminProductSerializer(products, many=True).data)

    def post(self, request):
        serializer = AdminProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        record_audit(request.user, 'create_product', 'products', instance=product)
        return Response(AdminProductSerializer(product).data, status=status.HTTP_201_CREATED)


class SuperadminUserListView(PaginatedAPIView):
    permission_classes = (SuperadminOnly,)
    rbac_resource = 'users'

    def get(self, request):
        role_code = request.query_params.get('role', 'all').strip()
        valid_roles = (*AccessRole.Code.values, 'unassigned', 'all')
        if role_code not in valid_roles:
            raise serializers.ValidationError({'role': 'Filtro de rol desconocido.'})

        users = User.objects.select_related('access_profile__role', 'craftswoman_profile', 'customer_profile')
        if role_code == 'unassigned':
            users = users.filter(access_profile__isnull=True)
        elif role_code != 'all':
            users = users.filter(access_profile__role__code=role_code)

        search = request.query_params.get('search', '').strip()
        if search:
            users = users.filter(
                models.Q(username__icontains=search)
                | models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(craftswoman_profile__community__icontains=search)
                | models.Q(craftswoman_profile__region__icontains=search)
                | models.Q(customer_profile__city__icontains=search)
            ).distinct()
        return Response(SuperadminUserSerializer(users.order_by('id'), many=True).data)

    def post(self, request):
        serializer = SuperadminUserWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        role = get_object_or_404(AccessRole, code=values['role'], active=True)
        with transaction.atomic():
            user = User.objects.create_user(
                username=values['username'],
                email=values['email'].strip().lower(),
                password=values['password'],
                first_name=values.get('first_name', ''),
                last_name=values.get('last_name', ''),
                is_active=values.get('is_active', True),
            )
            assign_role(user, role.code, actor=request.user)
            _sync_managed_user_profile(user, role, values)
            record_audit(
                request.user,
                'create_user',
                'users',
                affected_user=user,
                details={'role': role.code, 'is_active': user.is_active},
                instance=user,
            )
        return Response(SuperadminUserSerializer(user).data, status=status.HTTP_201_CREATED)


class SuperadminUserDetailView(APIView):
    permission_classes = (SuperadminOnly,)
    rbac_resource = 'users'

    def get(self, request, user_id):
        user = get_object_or_404(
            User.objects.select_related('access_profile__role', 'customer_profile', 'craftswoman_profile'),
            pk=user_id,
        )
        return Response(SuperadminUserSerializer(user).data)

    def patch(self, request, user_id):
        user = get_object_or_404(
            User.objects.select_related('access_profile__role', 'customer_profile', 'craftswoman_profile'),
            pk=user_id,
        )
        serializer = SuperadminUserWriteSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        changed_fields = set(values) - {'password', 'phone', 'address', 'city', 'community', 'region', 'craftswoman_active'}
        try:
            with transaction.atomic():
                old_role = role_for_user(user)
                if 'role' in values:
                    assign_role(user, values['role'], actor=request.user)
                new_role = role_for_user(user)
                if (
                    old_role
                    and old_role.code == AccessRole.Code.ADMIN
                    and new_role
                    and new_role.code == AccessRole.Code.ADMIN
                    and values.get('is_active') is False
                    and user.is_active
                ):
                    revoke_admin_delegations(user, request.user)
                update_fields = []
                for field in ('username', 'email', 'first_name', 'last_name', 'is_active'):
                    if field in values:
                        value = values[field]
                        if field == 'email':
                            value = value.strip().lower()
                        setattr(user, field, value)
                        update_fields.append(field)
                if 'password' in values:
                    user.set_password(values['password'])
                    update_fields.append('password')
                if update_fields:
                    user.save(update_fields=tuple(update_fields))
                if new_role:
                    _sync_managed_user_profile(user, new_role, values)
                record_audit(
                    request.user,
                    'update_user',
                    'users',
                    affected_user=user,
                    details={
                        'changed_fields': sorted(changed_fields),
                        'role': new_role.code if new_role else None,
                        'is_active': user.is_active,
                    },
                    instance=user,
                )
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        user.refresh_from_db()
        return Response(SuperadminUserSerializer(user).data)


class RBACCatalogView(APIView):
    permission_classes = (AdminOrSuperadmin,)

    def get(self, request):
        if is_explicitly_denied(request.user, 'permissions', 'view'):
            record_audit(
                request.user,
                'denied_view',
                'permissions',
                result=AuditEvent.Result.DENIED,
            )
            raise PermissionDenied('No tienes permiso para consultar el catálogo RBAC.')
        entries = permission_catalog()
        role = role_for_user(request.user)
        if role.code == AccessRole.Code.ADMIN:
            delegated = set(
                PermissionDelegation.objects.filter(admin=request.user).values_list('permission_id', flat=True)
            )
            entries = [
                item for item in entries
                if permission_for(item['resource'], item['action']).pk in delegated
            ]
        return Response({'permissions': entries})


class SuperadminRolePermissionsView(APIView):
    permission_classes = (SuperadminOnly,)
    rbac_resource = 'roles'

    def get(self, request, role_code):
        role = get_object_or_404(AccessRole, code=role_code)
        grants = set(role.permission_grants.values_list('permission_id', flat=True))
        entries = []
        for item in permission_catalog():
            permission = permission_for(item['resource'], item['action'])
            entries.append({
                **item,
                'allowed': role.code == AccessRole.Code.SUPERADMIN or permission.pk in grants,
            })
        return Response({'role': role.code, 'active': role.active, 'permissions': entries})

    def put(self, request, role_code):
        role = get_object_or_404(AccessRole, code=role_code)
        if role.code == AccessRole.Code.SUPERADMIN:
            raise serializers.ValidationError({'role': 'La matriz del superadmin es global e informativa.'})
        serializer = RolePermissionChangeSerializer(data=request.data.get('permissions'), many=True)
        serializer.is_valid(raise_exception=True)
        permissions = serializer.validated_data
        keys = {(item['resource'], item['action']) for item in permissions}
        if len(keys) != len(permissions):
            raise serializers.ValidationError({'permissions': 'No repitas un permiso en la misma operación.'})
        if not role.active:
            raise serializers.ValidationError({'role': 'No se pueden cambiar permisos de un rol inactivo.'})
        if any(permission_for(item['resource'], item['action']) is None for item in permissions):
            raise serializers.ValidationError({'permissions': 'Uno o más permisos no existen.'})
        with transaction.atomic():
            for item in permissions:
                set_role_permission(
                    request.user,
                    role.code,
                    item['resource'],
                    item['action'],
                    item['allowed'],
                )
        return self.get(request, role_code)

    def patch(self, request, role_code):
        role = get_object_or_404(AccessRole, code=role_code)
        serializer = RoleStateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role.active = serializer.validated_data['active']
        try:
            role.save(update_fields=('active',))
        except DjangoValidationError as error:
            record_audit(
                request.user,
                'deactivate_role',
                'roles',
                result=AuditEvent.Result.DENIED,
                details={'role': role.code},
            )
            raise serializers.ValidationError(error.messages) from error
        record_audit(
            request.user,
            'change_role_state',
            'roles',
            details={'role': role.code, 'active': role.active},
            instance=role,
        )
        return Response({'role': role.code, 'active': role.active})


class PermissionDelegationsView(APIView):
    permission_classes = (SuperadminOnly,)
    rbac_resource = 'delegations'

    def get(self, request):
        delegations = PermissionDelegation.objects.select_related(
            'admin', 'permission__content_type', 'granted_by',
        )
        admin_id = request.query_params.get('admin_user_id')
        if admin_id:
            if not admin_id.isdigit():
                raise serializers.ValidationError({'admin_user_id': 'Debe ser un identificador numérico.'})
            delegations = delegations.filter(admin_id=int(admin_id))
        return Response([{
            'admin_user_id': delegation.admin_id,
            'username': delegation.admin.username,
            'resource': permission_key(delegation.permission)[0] if permission_key(delegation.permission) else '',
            'action': permission_key(delegation.permission)[1] if permission_key(delegation.permission) else '',
            'codename': delegation.permission.codename,
            'granted_by': delegation.granted_by.username,
        } for delegation in delegations])

    def post(self, request):
        serializer = PermissionDelegationChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        admin_user = get_object_or_404(User, pk=values['admin_user_id'])
        set_permission_delegation(
            request.user,
            admin_user,
            values['resource'],
            values['action'],
            values['allowed'],
        )
        return Response({'detail': 'Delegación actualizada.'})


class AdminUserPermissionsView(APIView):
    permission_classes = (AdminOrSuperadmin,)

    def get(self, request, user_id):
        if is_explicitly_denied(request.user, 'permissions', 'view'):
            record_audit(request.user, 'denied_view', 'permissions', result=AuditEvent.Result.DENIED)
            raise PermissionDenied('No tienes permiso para consultar permisos individuales.')
        target = get_object_or_404(User, pk=user_id)
        actor_role = role_for_user(request.user)
        target_role = role_for_user(target)
        if actor_role.code == AccessRole.Code.ADMIN and (
            not target_role or target_role.code not in (AccessRole.Code.CUSTOMER, AccessRole.Code.CRAFTSWOMAN)
        ):
            raise PermissionDenied('Admin solo puede gestionar permisos de clientes y artesanas.')
        grants = {
            grant.permission_id: grant.effect
            for grant in UserPermissionGrant.objects.filter(user=target)
        }
        delegations = set(
            PermissionDelegation.objects.filter(admin=request.user).values_list('permission_id', flat=True)
        ) if actor_role.code == AccessRole.Code.ADMIN else None
        entries = []
        for item in permission_catalog():
            permission = permission_for(item['resource'], item['action'])
            if delegations is not None and permission.pk not in delegations:
                continue
            entries.append({**item, 'effect': grants.get(permission.pk)})
        return Response({'user_id': target.id, 'username': target.username, 'permissions': entries})

    def put(self, request, user_id):
        if is_explicitly_denied(request.user, 'permissions', 'change'):
            record_audit(request.user, 'denied_change', 'permissions', result=AuditEvent.Result.DENIED)
            raise PermissionDenied('No tienes permiso para cambiar grants individuales.')
        target = get_object_or_404(User, pk=user_id)
        serializer = UserPermissionChangeSerializer(data=request.data.get('permissions'), many=True)
        serializer.is_valid(raise_exception=True)
        permissions = serializer.validated_data
        keys = {(item['resource'], item['action']) for item in permissions}
        if len(keys) != len(permissions):
            raise serializers.ValidationError({'permissions': 'No repitas un permiso en la misma operación.'})
        for item in permissions:
            permission = permission_for(item['resource'], item['action'])
            if permission is None:
                raise serializers.ValidationError({'permissions': 'Uno o más permisos no existen.'})
            if not can_manage_permission(request.user, target, permission):
                record_audit(
                    request.user,
                    'set_user_permission',
                    item['resource'],
                    affected_user=target,
                    result=AuditEvent.Result.DENIED,
                    details={'action': item['action'], 'effect': item['effect']},
                )
                raise PermissionDenied('No tienes delegación para modificar todos los permisos solicitados.')
        with transaction.atomic():
            for item in permissions:
                if item['effect'] is None:
                    remove_user_permission(request.user, target, item['resource'], item['action'])
                else:
                    set_user_permission(
                        request.user,
                        target,
                        item['resource'],
                        item['action'],
                        item['effect'],
                    )
        return self.get(request, user_id)


class SuperadminRoleAssignmentView(APIView):
    permission_classes = (SuperadminOnly,)
    rbac_resource = 'role_assignments'

    def patch(self, request, user_id):
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = get_object_or_404(User, pk=user_id)
        try:
            role = assign_role(target, serializer.validated_data['role'], actor=request.user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        return Response({'user_id': target.id, 'role': role.code})


class SuperadminAuditView(APIView):
    permission_classes = (SuperadminOnly,)
    rbac_resource = 'audit'

    def get(self, request):
        events = AuditEvent.objects.select_related('actor', 'affected_user')[:100]
        return Response([{
            'id': event.id,
            'actor': event.actor.username if event.actor else None,
            'action': event.action,
            'resource': event.resource,
            'affected_user': event.affected_user.username if event.affected_user else None,
            'object_type': event.object_type,
            'object_id': event.object_id,
            'result': event.result,
            'details': event.details,
            'created_at': event.created_at,
        } for event in events])


class AdminCategoryListView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'categories'

    def get(self, request):
        return Response(AdminCategorySerializer(Category.objects.all(), many=True).data)

    def post(self, request):
        serializer = AdminCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        record_audit(request.user, 'create_category', 'categories', instance=category)
        return Response(AdminCategorySerializer(category).data, status=status.HTTP_201_CREATED)


class AdminCategoryDetailView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'categories'

    def patch(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        serializer = AdminCategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        record_audit(request.user, 'update_category', 'categories', instance=category)
        return Response(AdminCategorySerializer(category).data)


class AdminProductDetailView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'products'

    def patch(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        serializer = AdminProductSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        record_audit(request.user, 'update_product', 'products', instance=product)
        return Response(AdminProductSerializer(product).data)


class AdminOrderStatusView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'orders'

    def patch(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_status = order.status
        order.status = serializer.validated_data['status']
        order.save(update_fields=('status', 'updated_at'))
        record_audit(
            request.user,
            'change_order_status',
            'orders',
            affected_user=order.customer.user,
            details={'from': previous_status, 'to': order.status},
            instance=order,
        )
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
        identifier = serializer.validated_data['username'].strip()
        user = authenticate(
            request,
            username=identifier,
            password=serializer.validated_data['password'],
        )
        if user is None and '@' in identifier:
            account = User.objects.filter(email__iexact=identifier).only('username').first()
            if account:
                user = authenticate(
                    request,
                    username=account.get_username(),
                    password=serializer.validated_data['password'],
                )
        if user is None:
            return Response({'detail': 'Usuario o contraseña incorrectos.'}, status=status.HTTP_400_BAD_REQUEST)
        if role_for_user(user) is None:
            return Response({'detail': 'Tu cuenta no tiene un rol de acceso asignado. Contacta a administración.'}, status=status.HTTP_403_FORBIDDEN)
        login(request, user)
        return Response({'user': _user_payload(user)})


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated, HasAssignedRole)

    def get(self, request):
        return Response({'user': _user_payload(request.user)})


class CustomerProfileView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'customers'

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
    permission_classes = (CustomerOnly,)
    rbac_resource = 'cart'

    def get(self, request):
        customer = _customer_for(request.user)
        items, total = _cart_items(request, customer)
        return Response({'items': items, 'total': str(total), 'count': sum(item['quantity'] for item in items)})


class CartItemListView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'cart'

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
    permission_classes = (CustomerOnly,)
    rbac_resource = 'cart'

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
    permission_classes = (CustomerOnly,)
    rbac_resource = 'orders'

    def post(self, request):
        if not has_rbac_permission(request.user, 'customers', 'change'):
            raise PermissionDenied('No tienes permiso para modificar los datos del perfil necesarios para finalizar la compra.')
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
            record_audit(
                request.user,
                'checkout',
                'orders',
                affected_user=request.user,
                details={'item_count': len(items)},
                instance=order,
            )
        request.session['cart'] = {}
        request.session.modified = True
        order = Order.objects.prefetch_related('items__product').select_related('craftswoman').get(id=order.id)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(PaginatedAPIView):
    permission_classes = (OrderAccess,)
    rbac_resource = 'orders'

    def get(self, request):
        orders = _customer_orders(request.user).select_related('craftswoman').prefetch_related('items__product')
        return self.get_paginated_response(OrderSerializer(self.paginate_queryset(orders), many=True).data)


class OrderDetailView(APIView):
    permission_classes = (OrderAccess,)
    rbac_resource = 'orders'

    def get(self, request, order_id):
        order = get_object_or_404(
            _customer_orders(request.user).select_related('craftswoman').prefetch_related('items__product'),
            id=order_id,
        )
        return Response(OrderSerializer(order).data)


class CustomDesignListView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'designs'

    def get(self, request):
        customer = _customer_for(request.user)
        designs = customer.custom_designs.select_related('craftswoman')
        return Response(CustomDesignSerializer(designs, many=True).data)

    def post(self, request):
        if not has_rbac_permission(request.user, 'cart', 'add'):
            raise PermissionDenied('No tienes permiso para agregar el diseño al carrito.')
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
            record_audit(
                request.user,
                'create_custom_design',
                'designs',
                affected_user=request.user,
                instance=design,
            )
        cart = _cart_for(request)
        cart[str(product.id)] = 1
        request.session.modified = True
        return Response(
            {**CustomDesignSerializer(design).data, 'product_id': product.id},
            status=status.HTTP_201_CREATED,
        )


class CraftswomanDashboardView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'orders'

    def get(self, request):
        if not has_rbac_permission(request.user, 'designs', 'view'):
            raise PermissionDenied('No tienes permiso para consultar los diseños de tu taller.')
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
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'orders'
    rbac_actions = {'POST': 'change'}

    def post(self, request, order_id):
        if not has_rbac_permission(request.user, 'designs', 'change'):
            raise PermissionDenied('No tienes permiso para actualizar los diseños asociados al pedido.')
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
            record_audit(
                request.user,
                'accept_order',
                'orders',
                affected_user=order.customer.user,
                details={'status': order.status},
                instance=order,
            )
        return Response(OrderSerializer(order).data)


class CraftswomanOrderStatusView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'orders'
    transitions = {
        Order.Status.ACCEPTED: {Order.Status.WEAVING},
        Order.Status.WEAVING: {Order.Status.ACCEPTED, Order.Status.COMPLETED},
    }

    def patch(self, request, order_id):
        if not has_rbac_permission(request.user, 'designs', 'change'):
            raise PermissionDenied('No tienes permiso para actualizar los diseños asociados al pedido.')
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        order = get_object_or_404(Order, id=order_id, craftswoman=craftswoman)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        if new_status not in self.transitions.get(order.status, set()):
            return Response({'detail': 'Transición de estado no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            previous_status = order.status
            order.status = new_status
            order.save(update_fields=('status', 'updated_at'))
            for item in order.items.select_related('product__custom_design'):
                design = getattr(item.product, 'custom_design', None)
                if design and design.craftswoman_id == craftswoman.id:
                    design.status = new_status
                    design.save(update_fields=('status',))
            record_audit(
                request.user,
                'craftswoman_change_order_status',
                'orders',
                affected_user=order.customer.user,
                details={'from': previous_status, 'to': new_status},
                instance=order,
            )
        return Response(OrderSerializer(order).data)


class CraftswomanDesignStatusView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'designs'
    transitions = CraftswomanOrderStatusView.transitions

    def patch(self, request, design_id):
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        design = get_object_or_404(CustomDesign, id=design_id, craftswoman=craftswoman)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        if new_status not in self.transitions.get(design.status, set()):
            return Response({'detail': 'Transición de estado no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
        previous_status = design.status
        with transaction.atomic():
            design.status = new_status
            design.save(update_fields=('status',))
            record_audit(
                request.user,
                'craftswoman_change_design_status',
                'designs',
                affected_user=design.customer.user,
                details={'from': previous_status, 'to': new_status},
                instance=design,
            )
        return Response({'id': design.id, 'status': design.status})