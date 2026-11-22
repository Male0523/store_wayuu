from decimal import Decimal
from html import escape as html_escape
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AccessRole,
    AuditEvent,
    Category,
    Craftswoman,
    CustomDesign,
    Customer,
    CustomerCartItem,
    CustomerFavorite,
    InAppNotification,
    Order,
    OrderItem,
    NavigationItem,
    PermissionDelegation,
    Product,
    RBACAction,
    RBACCapability,
    RBACGrant,
    RBACRecordScopeGrant,
    RBACResource,
    RolePermission,
    UserPermissionGrant,
    UserRole,
)
from .permissions import AdminOrSuperadmin, CraftswomanOnly, CustomerOnly, HasAssignedRole, OrderAccess, RolePermission as RolePermissionAccess, SuperadminOnly, category_visibility_action, order_admin_action, product_publish_action
from .cart_services import (
    MAX_CART_QUANTITY,
    discard_unresolved_legacy_cart_item,
    merge_legacy_session_cart,
    unresolved_legacy_cart_items,
)
from .order_workflow import (
    ADMIN_ACTIVE_ORDER_STATUSES,
    allowed_order_transitions,
    can_transition_order,
    has_custom_design_items,
    recompute_order_tracking_status,
    sync_legacy_order_craftswoman,
)
from .rbac import (
    PERMISSION_ACTIONS,
    PERMISSION_RESOURCES,
    assign_role,
    can_manage_permission,
    capability_for,
    canonical_action,
    effective_permission_keys,
    has_permission as has_rbac_permission,
    is_explicitly_denied,
    permission_catalog,
    permission_for,
    permission_key,
    record_audit,
    record_scope_for,
    role_has_permission,
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
        fields = ('id', 'name', 'description', 'active', 'is_internal')
        read_only_fields = ('id', 'is_internal')


class CraftswomanSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Craftswoman
        fields = ('id', 'name', 'community', 'region', 'biography')


MAX_PRODUCT_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PRODUCT_IMAGE_PIXELS = 25_000_000
PRODUCT_IMAGE_FORMATS = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}


def product_image_url(product, request=None):
    image = getattr(product, 'image', None)
    url = image.url if image and image.name else product.image_url
    if url and request:
        return request.build_absolute_uri(url)
    return url or ''


class ProductImageUploadField(serializers.FileField):
    def to_internal_value(self, data):
        if getattr(data, 'size', 0) > MAX_PRODUCT_IMAGE_BYTES:
            raise serializers.ValidationError('La imagen supera el tamaño máximo de 5 MB.')
        try:
            from PIL import Image, UnidentifiedImageError
        except ImportError as exc:
            if exc.name and exc.name.startswith('PIL'):
                raise serializers.ValidationError('La carga de imágenes no está disponible porque Pillow no está instalado.')
            raise
        try:
            uploaded = super().to_internal_value(data)
        except serializers.ValidationError:
            raise serializers.ValidationError('El archivo no contiene una imagen válida o está dañado.')
        try:
            uploaded.seek(0)
            with Image.open(uploaded) as image:
                image_format = image.format
                width, height = image.size
                if image_format not in PRODUCT_IMAGE_FORMATS:
                    raise serializers.ValidationError('Formato no permitido. Usa JPEG, PNG o WebP.')
                if width < 1 or height < 1 or width * height > MAX_PRODUCT_IMAGE_PIXELS:
                    raise serializers.ValidationError('La imagen tiene dimensiones no permitidas.')
                image.verify()
            uploaded.seek(0)
            uploaded.name = f'{Path(uploaded.name).stem}{PRODUCT_IMAGE_FORMATS[image_format]}'
        except serializers.ValidationError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise serializers.ValidationError('El archivo no contiene una imagen válida o está dañado.')
        return uploaded


class NullableProductCraftswomanField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        if data == '':
            return None
        return super().to_internal_value(data)


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    craftswoman = CraftswomanSummarySerializer(read_only=True)
    is_custom_design = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, product):
        return product_image_url(product, self.context.get('request'))

    @staticmethod
    def get_is_custom_design(product):
        return bool(product.custom_design_id)

    class Meta:
        model = Product
        fields = (
            'id', 'sku', 'name', 'category', 'craftswoman', 'description', 'region',
            'color', 'size', 'production_time', 'price', 'stock', 'image_url',
            'made_to_order', 'active', 'is_custom_design', 'created_at', 'updated_at',
        )


class AdminProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(active=True, is_internal=False))
    craftswoman_name = serializers.CharField(source='craftswoman.name', read_only=True, allow_null=True, default=None)
    active = serializers.BooleanField(required=False, default=True)
    craftswoman = NullableProductCraftswomanField(
        queryset=Craftswoman.objects.all(), required=False, allow_null=True,
    )
    image = ProductImageUploadField(write_only=True, required=False, allow_empty_file=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image_url'] = product_image_url(instance, self.context.get('request'))
        return data

    def validate_active(self, value):
        if value and self.instance and self.instance.custom_design_id:
            raise serializers.ValidationError('Los diseños personalizados son privados y no se pueden publicar en el catálogo.')
        return value

    def validate(self, attrs):
        category = attrs.get('category', self.instance.category if self.instance else None)
        active = attrs.get('active', self.instance.active if self.instance else True)
        category_selection_or_activation = (
            self.instance is None or 'category' in attrs or ('active' in attrs and active)
        )
        if category_selection_or_activation and active and category and (not category.active or category.is_internal):
            raise serializers.ValidationError({'category': 'Los productos públicos requieren una categoría comercial activa.'})
        return attrs

    class Meta:
        model = Product
        fields = (
            'id', 'sku', 'name', 'category', 'craftswoman', 'craftswoman_name', 'description', 'region',
            'color', 'size', 'production_time', 'price', 'stock', 'image_url',
            'image', 'made_to_order', 'active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def update(self, instance, validated_data):
        image = validated_data.pop('image', serializers.empty)
        if image is not serializers.empty:
            instance.image = image
        elif 'image_url' in validated_data and validated_data['image_url'] != instance.image_url:
            # Changing the source URL is an explicit switch away from the stored upload.
            instance.image = None
        return super().update(instance, validated_data)

    def create(self, validated_data):
        image = validated_data.pop('image', serializers.empty)
        product = super().create(validated_data)
        if image is not serializers.empty:
            product.image = image
            product.save(update_fields=('image', 'updated_at'))
        return product


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
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, product):
        return product_image_url(product, self.context.get('request'))

    class Meta:
        model = Product
        fields = ('id', 'name', 'image_url', 'price')


class InventoryProductSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name', read_only=True)
    craftswoman_name = serializers.CharField(source='craftswoman.name', read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = ('id', 'sku', 'name', 'category', 'craftswoman_name', 'stock', 'active')


class InventoryMovementSerializer(serializers.ModelSerializer):
    def to_representation(self, event):
        movement = event.details.get('stock_movement', {})
        return {
            'id': event.id,
            'created_at': event.created_at,
            'product_id': int(event.object_id) if event.object_id.isdecimal() else None,
            'sku': movement.get('sku', ''),
            'product_name': movement.get('product_name', ''),
            'before': movement.get('before'),
            'after': movement.get('after'),
            'delta': movement.get('delta'),
            'reason': movement.get('reason', ''),
            'order_id': movement.get('order_id'),
        }


INVENTORY_EXPORT_HEADERS = ('Referencia', 'Producto', 'Categoría', 'Tejedora', 'Stock', 'Estado', 'Publicado', 'Por encargo')


def _inventory_export_rows(products, threshold):
    rows = []
    for product in products:
        state = 'Agotado' if product.stock == 0 else 'Stock bajo' if product.stock <= threshold else 'Disponible'
        rows.append((
            product.sku, product.name, product.category.name,
            product.craftswoman.name if product.craftswoman else '', product.stock, state,
            'Sí' if product.active else 'No', 'Sí' if product.made_to_order else 'No',
        ))
    return rows


def _xlsx_inventory_export(rows, summary, threshold):
    sheet_rows = [
        ('Reporte de inventario Wayúu Store',),
        (f'Umbral de stock bajo: {threshold}',),
        (f"Productos: {summary['product_count']} · Unidades: {summary['total_units']} · Agotados: {summary['out_of_stock_count']} · Stock bajo: {summary['low_stock_count']}",),
        (), INVENTORY_EXPORT_HEADERS, *rows,
    ]
    sheet_xml_rows = []
    for row_number, row in enumerate(sheet_rows, 1):
        cells = []
        for column_number, value in enumerate(row, 1):
            column = ''
            number = column_number
            while number:
                number, remainder = divmod(number - 1, 26)
                column = chr(65 + remainder) + column
            reference = f'{column}{row_number}'
            if isinstance(value, int):
                cells.append(f'<c r="{reference}" t="n"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{html_escape(str(value), {chr(34): "&quot;"})}</t></is></c>')
        sheet_xml_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    worksheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        + ''.join(sheet_xml_rows) + '</sheetData></worksheet>')
    files = {
        '[Content_Types].xml': ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'),
        '_rels/.rels': ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'),
        'xl/workbook.xml': ('<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            '<sheet name="Inventario" sheetId="1" r:id="rId1"/></sheets></workbook>'),
        'xl/_rels/workbook.xml.rels': ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'),
        'xl/worksheets/sheet1.xml': worksheet,
    }
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode('utf-8'))
    return output.getvalue()


def _pdf_text(value):
    encoded = str(value).encode('cp1252', errors='replace')
    escaped = bytearray()
    for byte in encoded:
        if byte in (40, 41, 92):
            escaped.extend(b'\\' + bytes((byte,)))
        elif byte < 32 or byte > 126:
            escaped.extend(f'\\{byte:03o}'.encode('ascii'))
        else:
            escaped.append(byte)
    return b'(' + bytes(escaped) + b')'


def _pdf_inventory_export(rows, summary, threshold):
    lines = [
        'Reporte de inventario Wayuu Store',
        f"Umbral bajo: {threshold} | Productos: {summary['product_count']} | Unidades: {summary['total_units']} | Agotados: {summary['out_of_stock_count']} | Stock bajo: {summary['low_stock_count']}",
        'Referencia | Producto | Categoria | Tejedora | Stock | Estado | Publicado | Por encargo',
    ]
    lines.extend(' | '.join(str(value) for value in row)[:130] for row in rows)
    pages = [lines[index:index + 54] for index in range(0, len(lines), 54)] or [[]]
    objects = [b''] * (3 + 2 * len(pages))
    objects[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
    objects[2] = b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'
    page_refs = []
    for index, page_lines in enumerate(pages):
        page_id = 4 + index * 2
        content_id = page_id + 1
        page_refs.append(f'{page_id} 0 R')
        commands = [b'BT /F1 8 Tf 40 750 Td 12 TL']
        commands.extend(_pdf_text(line) + b' Tj T*' for line in page_lines)
        commands.append(b'ET')
        stream = b'\n'.join(commands)
        objects[page_id - 1] = f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode('ascii')
        objects[content_id - 1] = f'<< /Length {len(stream)} >>\nstream\n'.encode('ascii') + stream + b'\nendstream'
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(page_refs)}] /Count {len(pages)} >>'.encode('ascii')
    output = BytesIO()
    output.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for object_id, body in enumerate(objects, 1):
        offsets.append(output.tell())
        output.write(f'{object_id} 0 obj\n'.encode('ascii') + body + b'\nendobj\n')
    xref = output.tell()
    output.write(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode('ascii'))
    for offset in offsets[1:]:
        output.write(f'{offset:010d} 00000 n \n'.encode('ascii'))
    output.write(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode('ascii'))
    return output.getvalue()


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSummarySerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    craftswoman_name = serializers.CharField(source='craftswoman.name', read_only=True, allow_null=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    allowed_statuses = serializers.SerializerMethodField()

    def get_allowed_statuses(self, item):
        actor = self.context.get('status_actor')
        return allowed_order_transitions(item.status, actor) if actor == 'craftswoman' else []

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'quantity', 'unit_price', 'subtotal', 'craftswoman', 'craftswoman_name', 'status', 'status_label', 'allowed_statuses')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=0, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    allowed_statuses = serializers.SerializerMethodField()
    craftswoman = CraftswomanSummarySerializer(read_only=True)
    customer_id = serializers.IntegerField(read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'status', 'status_label', 'payment_method', 'shipping_address',
            'notes', 'created_at', 'updated_at', 'items', 'total', 'craftswoman',
            'customer_id', 'customer_name', 'allowed_statuses',
        )

    def get_allowed_statuses(self, order):
        actor = self.context.get('status_actor')
        request = self.context.get('request')
        if (
            actor == 'craftswoman'
            and has_custom_design_items(order)
            and (request is None or not has_rbac_permission(request.user, 'designs', 'change'))
        ):
            return []
        return allowed_order_transitions(order.status, actor) if actor else []


class CustomDesignSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    allowed_statuses = serializers.SerializerMethodField()
    craftswoman_name = serializers.CharField(source='craftswoman.name', read_only=True, allow_null=True, default=None)

    class Meta:
        model = CustomDesign
        fields = (
            'id', 'pattern', 'base_color', 'accent_color_one', 'accent_color_two',
            'size', 'quantity', 'notes', 'estimated_price', 'status', 'status_label',
            'created_at', 'craftswoman_name', 'allowed_statuses',
        )

    def get_allowed_statuses(self, design):
        actor = self.context.get('status_actor')
        request = self.context.get('request')
        if actor == 'craftswoman' and (request is None or not has_rbac_permission(request.user, 'designs', 'change')):
            return []
        return allowed_order_transitions(design.status, actor) if actor else []


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


class CraftswomanProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=150, trim_whitespace=True)
    community = serializers.CharField(max_length=150, required=False, allow_blank=True, trim_whitespace=True)
    region = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, trim_whitespace=True)
    biography = serializers.CharField(max_length=3000, required=False, allow_blank=True, trim_whitespace=True)

    class Meta:
        model = Craftswoman
        fields = ('id', 'name', 'community', 'region', 'phone', 'biography')
        read_only_fields = ('id',)

    def to_internal_value(self, data):
        editable = {'name', 'community', 'region', 'phone', 'biography'}
        protected = set(data.keys()) - editable
        if protected:
            raise serializers.ValidationError({
                field: 'Este campo no se puede modificar desde el perfil propio.'
                for field in sorted(protected)
            })
        return super().to_internal_value(data)

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('El nombre no puede estar vacío.')
        return value.strip()

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Indica al menos un dato del perfil para actualizar.')
        return attrs


class CraftswomanProductWriteSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(active=True, is_internal=False))
    description = serializers.CharField(required=True, allow_blank=False, min_length=10, max_length=2000)
    region = serializers.CharField(required=True, allow_blank=False, max_length=100)
    color = serializers.CharField(required=True, allow_blank=False, max_length=150)
    size = serializers.CharField(required=True, allow_blank=False, max_length=30)
    production_time = serializers.CharField(required=True, allow_blank=False, max_length=100)
    image_url = serializers.URLField(required=True, allow_blank=False)

    class Meta:
        model = Product
        fields = (
            'sku', 'name', 'category', 'description', 'region', 'color', 'size',
            'production_time', 'price', 'stock', 'image_url', 'made_to_order',
        )

    def to_internal_value(self, data):
        # Never silently ignore an attempted ownership or publication change.
        allowed = set(self.fields)
        unexpected = set(data.keys()) - allowed
        if unexpected:
            raise serializers.ValidationError({
                field: 'Este campo no se puede enviar desde el flujo de productos de tejedora.'
                for field in sorted(unexpected)
            })
        return super().to_internal_value(data)


class CartItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class LegacyCartItemRemovalSerializer(serializers.Serializer):
    key = serializers.CharField(allow_blank=True, trim_whitespace=False)


class FavoriteInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)


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
    resource = serializers.SlugField(max_length=80)
    action = serializers.SlugField(max_length=40)


class RolePermissionChangeSerializer(serializers.Serializer):
    resource = serializers.SlugField(max_length=80)
    action = serializers.SlugField(max_length=40)
    allowed = serializers.BooleanField(required=False)
    effect = serializers.ChoiceField(choices=RBACGrant.Effect.choices, required=False, allow_null=True)

    def validate(self, attrs):
        if 'allowed' not in attrs and 'effect' not in attrs:
            raise serializers.ValidationError('Indica allowed o effect para cada capacidad.')
        if not capability_for(attrs['resource'], attrs['action']):
            raise serializers.ValidationError({'resource': 'El recurso/acción no existe o está inactivo.'})
        return attrs


class UserPermissionChangeSerializer(PermissionInputSerializer):
    effect = serializers.ChoiceField(
        choices=UserPermissionGrant.Effect.choices,
        allow_null=True,
    )


class PermissionDelegationChangeSerializer(PermissionInputSerializer):
    admin_user_id = serializers.IntegerField(min_value=1)
    allowed = serializers.BooleanField()


class RoleAssignmentSerializer(serializers.Serializer):
    role = serializers.SlugField(max_length=30)

    def validate_role(self, value):
        if not AccessRole.objects.filter(code=value, active=True).exists():
            raise serializers.ValidationError('Selecciona un rol activo existente.')
        return value


class SuperadminUserWriteSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.SlugField(max_length=30, required=False)
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
            raise serializers.ValidationError({'role': 'Selecciona un rol activo existente.'})
        role_code = attrs.get('role')
        if role_code and not AccessRole.objects.filter(code=role_code, active=True).exists():
            raise serializers.ValidationError({'role': 'Selecciona un rol activo existente.'})
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


NAVIGATION_ROUTE_CATALOG = {
    # Required view capabilities are the minimum data access for each real screen.
    # Action permissions and row scopes are checked separately by each endpoint.
    'store:catalog': {'label': 'Catálogo', 'requires': (('products', 'view'),)},
    'customer.orders': {'label': 'Cliente · Mis pedidos', 'requires': (('orders', 'view'),)},
    'customer.designs': {'label': 'Cliente · Mis diseños', 'requires': (('designs', 'view'),)},
    'customer.profile': {'label': 'Cliente · Mis datos', 'requires': (('customers', 'view'),)},
    'craftswoman.dashboard': {'label': 'Tejedora · Panel principal', 'requires': (('orders', 'view'), ('products', 'view'))},
    'craftswoman.products': {'label': 'Tejedora · Mis tejidos', 'requires': (('products', 'view'),)},
    'craftswoman.inventory': {'label': 'Tejedora · Mi inventario', 'requires': (('products', 'view'),)},
    'craftswoman.orders': {'label': 'Tejedora · Mis pedidos', 'requires': (('orders', 'view'),)},
    'craftswoman.profile': {'label': 'Tejedora · Mi perfil', 'requires': (('craftswomen', 'view'),)},
    'admin.dashboard': {'label': 'Administrador · Panel principal', 'requires': (('products', 'view'), ('orders', 'view')), 'all_scope': ('products', 'orders')},
    'admin.products': {'label': 'Administrador · Productos', 'requires': (('products', 'view'),), 'all_scope': ('products',)},
    'admin.inventory': {'label': 'Administrador · Inventario', 'requires': (('products', 'view'),), 'all_scope': ('products',)},
    'admin.orders': {'label': 'Administrador · Pedidos', 'requires': (('orders', 'view'),), 'all_scope': ('orders',)},
    'admin.categories': {'label': 'Administrador · Categorías', 'requires': (('categories', 'view'),)},
    'admin.access': {'label': 'Roles y permisos', 'requires': (('roles', 'view'),)},
}

def navigation_role_codes(route_name):
    """Return active roles; route-level permission requirements are validated separately."""
    if route_name not in NAVIGATION_ROUTE_CATALOG:
        return []
    return list(AccessRole.objects.filter(active=True).order_by('priority', 'name').values_list('code', flat=True))


def navigation_requirements(route_name):
    return NAVIGATION_ROUTE_CATALOG.get(route_name, {}).get('requires', ())


def missing_role_navigation_requirements(role, route_name):
    return [
        (resource, action)
        for resource, action in navigation_requirements(route_name)
        if not role_has_permission(role, resource, action)
    ]


def role_has_all_scope(role, resource):
    if role is None or not role.active:
        return False
    if role.code == AccessRole.Code.SUPERADMIN:
        return True
    saved_scope = RBACRecordScopeGrant.objects.filter(role=role, resource__code=resource).values_list('scope', flat=True).first()
    if saved_scope:
        return saved_scope == RBACRecordScopeGrant.Scope.ALL
    return role.code == AccessRole.Code.ADMIN


def navigation_requirement_payload(route_name, role=None):
    return [
        {
            'resource': resource,
            'action': action,
            'resource_name': RBACResource.objects.filter(code=resource).values_list('name', flat=True).first() or resource,
            'granted': role_has_permission(role, resource, action) if role else None,
        }
        for resource, action in navigation_requirements(route_name)
    ]


def navigation_route_payload(route_name):
    assignable = navigation_role_codes(route_name)
    return {
        'value': route_name,
        'label': NAVIGATION_ROUTE_CATALOG[route_name]['label'],
        'role_codes': assignable,
        'required_permissions': [
            {key: value for key, value in requirement.items() if key != 'granted'}
            for requirement in navigation_requirement_payload(route_name)
        ],
        'missing_permissions': {
            role.code: [
                requirement for requirement in navigation_requirement_payload(route_name, role)
                if not requirement['granted']
            ]
            for role in AccessRole.objects.filter(active=True).order_by('priority', 'name')
            if role.code in assignable
        },
        'missing_scopes': {
            role.code: [
                resource for resource in NAVIGATION_ROUTE_CATALOG[route_name].get('all_scope', ())
                if not role_has_all_scope(role, resource)
            ]
            for role in AccessRole.objects.filter(active=True).order_by('priority', 'name')
            if role.code in assignable
        },
    }


class NavigationItemWriteSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=80)
    route_name = serializers.ChoiceField(choices=tuple((key, key) for key in NAVIGATION_ROUTE_CATALOG))
    anchor = serializers.CharField(max_length=80, required=False, allow_blank=True)
    description = serializers.CharField(max_length=220, required=False, allow_blank=True)
    role_codes = serializers.ListField(
        child=serializers.SlugField(max_length=30),
        allow_empty=True,
    )
    permission_resource = serializers.ChoiceField(
        choices=tuple((key, key) for key in PERMISSION_RESOURCES),
        required=False,
        allow_null=True,
    )
    permission_action = serializers.ChoiceField(
        choices=tuple((action, action) for action in PERMISSION_ACTIONS),
        required=False,
        allow_null=True,
    )
    order = serializers.IntegerField(min_value=0, max_value=32767, required=False, default=10)
    active = serializers.BooleanField(required=False, default=True)

    def validate_route_name(self, value):
        existing = NavigationItem.objects.filter(route_name=value)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
            if value == self.instance.route_name:
                return value
        if existing.exists():
            raise serializers.ValidationError('Esa ruta ya está configurada; edita la opción existente y agrega los roles allí.')
        return value

    def validate(self, attrs):
        resource = attrs.get('permission_resource')
        action = attrs.get('permission_action')
        if bool(resource) != bool(action):
            raise serializers.ValidationError('Selecciona tanto el recurso como la acción requerida, o deja ambos vacíos.')
        if 'role_codes' in attrs and len(attrs['role_codes']) != len(set(attrs['role_codes'])):
            raise serializers.ValidationError({'role_codes': 'No repitas roles.'})
        role_codes = attrs.get('role_codes')
        if role_codes is not None and set(role_codes) - set(AccessRole.objects.filter(active=True).values_list('code', flat=True)):
            raise serializers.ValidationError({'role_codes': 'Todas las asignaciones deben apuntar a roles activos existentes.'})
        previous_route = getattr(self.instance, 'route_name', None)
        route_name = attrs.get('route_name', previous_route)
        if previous_route == 'admin.access' and route_name != previous_route:
            raise serializers.ValidationError({'route_name': 'La opción Roles y permisos está protegida y no puede cambiar de pantalla.'})
        if getattr(self.instance, 'route_name', None) == 'admin.access' and attrs.get('active') is False:
            raise serializers.ValidationError({'active': 'La pantalla de administración RBAC debe permanecer disponible para el superadministrador.'})
        if route_name and (role_codes is not None or 'route_name' in attrs):
            selected_roles = set(role_codes) if role_codes is not None else set(self.instance.roles.values_list('code', flat=True))
            incompatible = selected_roles - set(navigation_role_codes(route_name))
            if incompatible:
                raise serializers.ValidationError({
                    'role_codes': f'Estos roles no son compatibles con la pantalla seleccionada: {", ".join(sorted(incompatible))}.',
                })
        if route_name and attrs.get('active', getattr(self.instance, 'active', True)):
            selected_roles = set(role_codes) if role_codes is not None else (
                set(self.instance.roles.values_list('code', flat=True)) if self.instance else set()
            )
            for role in AccessRole.objects.filter(code__in=selected_roles, active=True):
                missing = missing_role_navigation_requirements(role, route_name)
                if missing:
                    view_name = NAVIGATION_ROUTE_CATALOG[route_name]['label'].split(' · ', 1)[-1]
                    missing_names = [
                        RBACResource.objects.filter(code=resource).values_list('name', flat=True).first() or resource
                        for resource, _action in missing
                    ]
                    message = f'Para habilitar esta pantalla por favor conceda el permiso de la vista {view_name} de consultar'
                    if len(missing_names) > 1:
                        message += f". Permisos faltantes: {', '.join(missing_names)}"
                    raise serializers.ValidationError({
                        'role_codes': message + '.',
                    })
        return attrs


class RoleStateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.IntegerField(min_value=0, max_value=32767, required=False)
    active = serializers.BooleanField(required=False)


class RoleCreateSerializer(serializers.Serializer):
    code = serializers.SlugField(max_length=30)
    name = serializers.CharField(max_length=80)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.IntegerField(min_value=0, max_value=32767, required=False, default=10)

    def validate_code(self, value):
        if AccessRole.objects.filter(code=value).exists():
            raise serializers.ValidationError('Ya existe un rol con este código.')
        return value


class CatalogEntrySerializer(serializers.Serializer):
    code = serializers.SlugField(max_length=80)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)


class CapabilityInputSerializer(serializers.Serializer):
    resource = serializers.SlugField(max_length=80)
    action = serializers.SlugField(max_length=40)


class RecordScopeChangeSerializer(serializers.Serializer):
    resource = serializers.SlugField(max_length=80)
    scope = serializers.ChoiceField(choices=(('all', 'Todos los registros'), ('none', 'Sin registros')), allow_null=True)

    def validate_resource(self, value):
        if not RBACResource.objects.filter(code=value, active=True).exists():
            raise serializers.ValidationError('Selecciona un recurso activo.')
        return value


def _session_display_name(user, profile_name=None):
    first_name = (user.first_name or '').strip()
    last_name = (user.last_name or '').strip()

    if first_name and last_name:
        return f'{first_name} {last_name}'.strip()

    if profile_name and str(profile_name).strip():
        return str(profile_name).strip()

    combined_name = ' '.join(part for part in (first_name, last_name) if part and str(part).strip()).strip()
    if combined_name:
        return combined_name

    user_name = (user.get_full_name() or '').strip()
    if user_name:
        return user_name
    return user.username or 'Usuario'


def _user_payload(user):
    role = role_for_user(user)
    profile_name = None
    payload = {
        'id': user.id,
        'username': user.username,
        'name': user.get_full_name() or user.username,
        'first_name': (user.first_name or '').strip(),
        'last_name': (user.last_name or '').strip(),
        'email': user.email,
        'role': role.code if role else None,
        'permissions': effective_permission_keys(user),
        'profile': None,
    }
    if role and role.code == AccessRole.Code.CRAFTSWOMAN:
        profile = Craftswoman.objects.filter(user=user).first()
        if not profile:
            payload['name'] = _session_display_name(user)
            return payload
        profile_name = profile.name
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
            profile_name = customer.name
            payload['profile'] = ProfileSerializer(customer).data
    payload['name'] = _session_display_name(user, profile_name)
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
    if not role:
        raise PermissionDenied('Esta acción requiere un rol activo.')
    customer = Customer.objects.filter(user=user).first()
    if customer:
        return customer
    if role.code != AccessRole.Code.CUSTOMER:
        raise PermissionDenied('Esta cuenta no tiene un perfil de cliente vinculado.')
    customer, _ = Customer.objects.get_or_create(
        user=user,
        defaults={
            'name': user.get_full_name() or user.username,
            'email': user.email or f'{user.username}@sin-correo.local',
        },
    )
    return customer


def _sync_legacy_session_cart(request, customer):
    merge_legacy_session_cart(request, customer)


def _cart_items(request, customer):
    _sync_legacy_session_cart(request, customer)
    cart_rows = CustomerCartItem.objects.filter(customer=customer).select_related(
        'product__category', 'product__craftswoman', 'product__custom_design',
        'product__custom_design__customer',
    )
    items = []
    total = Decimal('0')
    for row in cart_rows:
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
        items.append({
            'product': ProductSerializer(product, context={'request': request}).data,
            'quantity': quantity,
            'subtotal': str(subtotal),
            'available': available,
        })
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
    customer = Customer.objects.filter(user=user).first()
    if customer:
        return Order.objects.filter(customer=customer)
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
        categories = Category.objects.filter(active=True, is_internal=False).order_by('name', 'id')
        return Response(CategorySerializer(categories, many=True).data)


class ProductListView(PaginatedAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        products = Product.objects.filter(
            active=True, custom_design__isnull=True, category__active=True, category__is_internal=False,
        ).select_related('category', 'craftswoman')
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
        return self.get_paginated_response(ProductSerializer(page, many=True, context={'request': request}).data)


class ProductDetailView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, product_id):
        product = get_object_or_404(
            Product.objects.select_related('category', 'craftswoman'),
            id=product_id, active=True, custom_design__isnull=True,
            category__active=True, category__is_internal=False,
        )
        return Response(ProductSerializer(product, context={'request': request}).data)


class AdminProductListView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'products'

    def get(self, request):
        products = Product.objects.select_related('category', 'craftswoman').all()
        return Response(AdminProductSerializer(products, many=True, context={'request': request}).data)

    def post(self, request):
        serializer = AdminProductSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        record_audit(request.user, 'create_product', 'products', instance=product)
        return Response(AdminProductSerializer(product, context={'request': request}).data, status=status.HTTP_201_CREATED)


class AdminInventoryReportView(PaginatedAPIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'products'

    def get(self, request):
        threshold_value = request.query_params.get('threshold', '')
        if not threshold_value.isdecimal() or int(threshold_value) < 1:
            raise serializers.ValidationError({'threshold': 'Indica un umbral entero mayor que cero para definir stock bajo.'})
        threshold = int(threshold_value)
        status_filter = request.query_params.get('status', 'all').strip()
        if status_filter not in {'all', 'low', 'out', 'in_stock'}:
            raise serializers.ValidationError({'status': 'Selecciona un filtro de inventario válido.'})

        inventory = Product.objects.select_related('category', 'craftswoman').all()
        summary = inventory.aggregate(
            product_count=Count('id'),
            total_units=Sum('stock'),
            out_of_stock_count=Count('id', filter=Q(stock=0)),
            low_stock_count=Count('id', filter=Q(stock__gt=0, stock__lte=threshold)),
        )
        products = inventory
        search = request.query_params.get('search', '').strip()
        if search:
            products = products.filter(
                Q(name__icontains=search) | Q(sku__icontains=search)
                | Q(category__name__icontains=search)
                | Q(craftswoman__name__icontains=search)
            )
        category_id = request.query_params.get('category', '').strip()
        if category_id:
            if not category_id.isdecimal():
                raise serializers.ValidationError({'category': 'La categoría debe ser un identificador numérico.'})
            products = products.filter(category_id=int(category_id))
        if status_filter == 'low':
            products = products.filter(stock__gt=0, stock__lte=threshold)
        elif status_filter == 'out':
            products = products.filter(stock=0)
        elif status_filter == 'in_stock':
            products = products.filter(stock__gt=0)

        export_format = request.query_params.get('export', '').strip().lower()
        if export_format and export_format not in {'xlsx', 'pdf'}:
            raise serializers.ValidationError({'export': 'Formato de exportación no permitido.'})
        if export_format:
            if not has_rbac_permission(request.user, 'products', 'export'):
                raise PermissionDenied('No tienes permiso para exportar el inventario.')
            export_rows = _inventory_export_rows(products.order_by('name', 'id'), threshold)
            if export_format == 'xlsx':
                response = HttpResponse(
                    _xlsx_inventory_export(export_rows, {
                        'product_count': summary['product_count'],
                        'total_units': summary['total_units'] or 0,
                        'out_of_stock_count': summary['out_of_stock_count'],
                        'low_stock_count': summary['low_stock_count'],
                    }, threshold),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
                response['Content-Disposition'] = 'attachment; filename="reporte-inventario.xlsx"'
                return response
            response = HttpResponse(
                _pdf_inventory_export(export_rows, {
                    'product_count': summary['product_count'],
                    'total_units': summary['total_units'] or 0,
                    'out_of_stock_count': summary['out_of_stock_count'],
                    'low_stock_count': summary['low_stock_count'],
                }, threshold), content_type='application/pdf',
            )
            response['Content-Disposition'] = 'attachment; filename="reporte-inventario.pdf"'
            return response

        page = self.paginate_queryset(products.order_by('name', 'id'))
        product_page = self.get_paginated_response(InventoryProductSerializer(page, many=True).data).data
        movements = AuditEvent.objects.filter(
            resource='products',
            action__in=('stock_adjustment', 'craftswoman_stock_adjustment', 'stock_checkout_decrement'),
        ).order_by('-created_at', '-id')
        movement_count = movements.count()
        return Response({
            'threshold': threshold,
            'summary': {
                'product_count': summary['product_count'],
                'total_units': summary['total_units'] or 0,
                'out_of_stock_count': summary['out_of_stock_count'],
                'low_stock_count': summary['low_stock_count'],
            },
            'products': product_page,
            'movement_count': movement_count,
            'movements': InventoryMovementSerializer(movements[:25], many=True).data,
        })


class AdminProductOptionsView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'products'

    def get(self, request):
        categories = Category.objects.filter(active=True, is_internal=False).order_by('name', 'id')
        craftswomen = Craftswoman.objects.order_by('name', 'id').values(
            'id', 'name', 'community', 'region', 'active',
        )
        return Response({
            'categories': AdminCategorySerializer(categories, many=True).data,
            'craftswomen': list(craftswomen),
        })


class SuperadminUserListView(PaginatedAPIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'users'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [RolePermissionAccess()]
        return [SuperadminOnly()]

    @staticmethod
    def require_global_user_scope(request):
        if record_scope_for(request.user, 'users') != 'all':
            raise PermissionDenied('Tu alcance no permite consultar todas las cuentas.')

    def get(self, request):
        self.require_global_user_scope(request)
        role_code = request.query_params.get('role', 'all').strip()
        valid_roles = (*AccessRole.objects.values_list('code', flat=True), 'unassigned', 'all')
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
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'users'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [RolePermissionAccess()]
        return [SuperadminOnly()]

    def get(self, request, user_id):
        if record_scope_for(request.user, 'users') != 'all':
            raise PermissionDenied('Tu alcance no permite consultar otras cuentas.')
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
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'permissions'

    def get(self, request):
        entries = permission_catalog()
        return Response({
            'permissions': entries,
            'resources': list(RBACResource.objects.values('id', 'code', 'name', 'description', 'active')),
            'actions': list(RBACAction.objects.values('id', 'code', 'name', 'description', 'active')),
        })


RECORD_SCOPE_RESOURCES = ('orders', 'designs', 'products', 'customers', 'users', 'craftswomen')


def _record_scope_rows(principal_field, principal, effective_user=None):
    saved = {
        row.resource.code: row.scope
        for row in RBACRecordScopeGrant.objects.filter(**{principal_field: principal}).select_related('resource')
    }
    rows = []
    for resource in RBACResource.objects.filter(code__in=RECORD_SCOPE_RESOURCES).order_by('name'):
        default_scope = (
            'all' if getattr(principal, 'code', None) in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN)
            else 'own' if getattr(principal, 'code', None) == AccessRole.Code.CUSTOMER
            else 'assigned' if getattr(principal, 'code', None) == AccessRole.Code.CRAFTSWOMAN and resource.code in ('orders', 'designs', 'products')
            else 'none'
        )
        rows.append({
            'resource': resource.code,
            'resource_name': resource.name,
            'scope': saved.get(resource.code),
            'effective_scope': record_scope_for(effective_user, resource.code) if effective_user else (
                saved.get(resource.code) or default_scope
            ),
        })
    return rows


def _save_record_scopes(request, principal_field, principal, scope_rows, resource_name, affected_user=None):
    keys = [item['resource'] for item in scope_rows]
    if len(keys) != len(set(keys)):
        raise serializers.ValidationError({'scopes': 'No repitas recursos en la misma operación.'})
    with transaction.atomic():
        for item in scope_rows:
            lookup = {
                principal_field: principal,
                'resource': RBACResource.objects.get(code=item['resource']),
            }
            if item['scope'] is None:
                RBACRecordScopeGrant.objects.filter(**lookup).delete()
            else:
                RBACRecordScopeGrant.objects.update_or_create(
                    **lookup,
                    defaults={
                        'scope': item['scope'],
                        'granted_by': request.user,
                    },
                )
            record_audit(
                request.user,
                'set_record_scope',
                item['resource'],
                affected_user=affected_user,
                details={'principal': resource_name, 'scope': item['scope']},
            )


class SuperadminRoleScopesView(APIView):
    permission_classes = (SuperadminOnly,)

    def get(self, request, role_code):
        role = get_object_or_404(AccessRole, code=role_code)
        return Response({'role': role.code, 'scopes': _record_scope_rows('role', role)})

    def put(self, request, role_code):
        role = get_object_or_404(AccessRole, code=role_code)
        if role.code == AccessRole.Code.SUPERADMIN:
            raise serializers.ValidationError({'role': 'El superadministrador siempre tiene alcance global.'})
        serializer = RecordScopeChangeSerializer(data=request.data.get('scopes'), many=True)
        serializer.is_valid(raise_exception=True)
        _save_record_scopes(request, 'role', role, serializer.validated_data, role.code)
        return self.get(request, role_code)


class SuperadminUserScopesView(APIView):
    permission_classes = (SuperadminOnly,)

    def get(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        role = role_for_user(target)
        if role and role.code == AccessRole.Code.SUPERADMIN:
            raise PermissionDenied('El superadministrador siempre tiene alcance global.')
        return Response({
            'user_id': target.id,
            'username': target.username,
            'scopes': _record_scope_rows('user', target, effective_user=target),
        })

    def put(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        role = role_for_user(target)
        if role and role.code == AccessRole.Code.SUPERADMIN:
            raise PermissionDenied('No se pueden configurar ámbitos individuales para el superadministrador.')
        serializer = RecordScopeChangeSerializer(data=request.data.get('scopes'), many=True)
        serializer.is_valid(raise_exception=True)
        _save_record_scopes(request, 'user', target, serializer.validated_data, target.username, affected_user=target)
        return self.get(request, user_id)


class SuperadminRolesView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'roles'

    @staticmethod
    def serialize(role):
        return {
            'code': role.code, 'name': role.name, 'description': role.description,
            'priority': role.priority, 'active': role.active,
            'system': role.code in AccessRole.Code.values,
            'assigned_users': role.users.count(),
        }

    def get(self, request):
        return Response([self.serialize(role) for role in AccessRole.objects.all()])

    def post(self, request):
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = AccessRole.objects.create(**serializer.validated_data)
        record_audit(request.user, 'create_role', 'roles', instance=role, details={'role': role.code})
        return Response(self.serialize(role), status=status.HTTP_201_CREATED)


class SuperadminRoleDetailView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'roles'

    def patch(self, request, role_code):
        role = get_object_or_404(AccessRole, code=role_code)
        serializer = RoleStateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        for field in ('name', 'description', 'priority', 'active'):
            if field in changes:
                setattr(role, field, changes[field])
        try:
            role.save(update_fields=tuple(changes.keys()))
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        record_audit(request.user, 'update_role', 'roles', instance=role, details=changes)
        return Response(SuperadminRolesView.serialize(role))


class SuperadminResourceCatalogView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'permissions'

    def get(self, request):
        return Response(list(RBACResource.objects.values('id', 'code', 'name', 'description', 'active')))

    def post(self, request):
        serializer = CatalogEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if RBACResource.objects.filter(code=values['code']).exists():
            raise serializers.ValidationError({'code': 'Ya existe ese recurso.'})
        with transaction.atomic():
            resource = RBACResource.objects.create(**values)
            for action in RBACAction.objects.filter(active=True, code__in=('view', 'create', 'edit', 'delete')):
                RBACCapability.objects.get_or_create(resource=resource, action=action)
        record_audit(request.user, 'create_rbac_resource', 'permissions', instance=resource)
        return Response({'id': resource.id, 'code': resource.code, 'name': resource.name, 'description': resource.description, 'active': resource.active}, status=status.HTTP_201_CREATED)


class SuperadminResourceDetailView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'permissions'

    def patch(self, request, resource_code):
        resource = get_object_or_404(RBACResource, code=resource_code)
        serializer = RoleStateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = {key: value for key, value in serializer.validated_data.items() if key in ('name', 'description', 'active')}
        for key, value in values.items():
            setattr(resource, key, value)
        resource.save(update_fields=tuple(values.keys()))
        record_audit(request.user, 'update_rbac_resource', 'permissions', instance=resource, details=values)
        return Response({'id': resource.id, 'code': resource.code, 'name': resource.name, 'description': resource.description, 'active': resource.active})


class SuperadminActionCatalogView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'permissions'

    def get(self, request):
        return Response(list(RBACAction.objects.values('id', 'code', 'name', 'description', 'active')))

    def post(self, request):
        serializer = CatalogEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if len(values['code']) > 40:
            raise serializers.ValidationError({'code': 'El código de acción admite hasta 40 caracteres.'})
        if len(values['name']) > 80:
            raise serializers.ValidationError({'name': 'El nombre de acción admite hasta 80 caracteres.'})
        if RBACAction.objects.filter(code=values['code']).exists():
            raise serializers.ValidationError({'code': 'Ya existe esa acción.'})
        with transaction.atomic():
            action = RBACAction.objects.create(**values)
        record_audit(request.user, 'create_rbac_action', 'permissions', details={'action': action.code})
        return Response({'id': action.id, 'code': action.code, 'name': action.name, 'description': action.description, 'active': action.active}, status=status.HTTP_201_CREATED)


class SuperadminActionDetailView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'permissions'

    def patch(self, request, action_code):
        action = get_object_or_404(RBACAction, code=action_code)
        serializer = RoleStateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = {key: value for key, value in serializer.validated_data.items() if key in ('name', 'description', 'active')}
        for key, value in values.items():
            setattr(action, key, value)
        action.save(update_fields=tuple(values.keys()))
        record_audit(request.user, 'update_rbac_action', 'permissions', details={'action': action.code, **values})
        return Response({'id': action.id, 'code': action.code, 'name': action.name, 'description': action.description, 'active': action.active})


class SuperadminCapabilitiesView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'permissions'

    def post(self, request):
        serializer = CapabilityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        resource = get_object_or_404(RBACResource, code=values['resource'], active=True)
        action = get_object_or_404(RBACAction, code=values['action'], active=True)
        capability, created = RBACCapability.objects.get_or_create(resource=resource, action=action)
        record_audit(request.user, 'create_rbac_capability', 'permissions', instance=capability)
        return Response({
            'resource': resource.code, 'resource_name': resource.name,
            'action': action.code, 'action_name': action.name,
            'codename': f'{resource.code}_{action.code}',
            'name': f'{action.name} · {resource.name}',
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SuperadminRolePermissionsView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'permissions'
    # Matrix writes return the persisted matrix; require read capability as well
    # to prevent write-only actors from receiving a full permission listing.
    rbac_actions = {'PUT': ('view', 'edit')}

    @staticmethod
    def rbac_resource_for_request(request, view):
        # PATCH updates role metadata/state. Reading or changing the matrix uses
        # permissions.view/edit on GET/PUT respectively.
        if request.method == 'PATCH':
            return 'roles'
        return 'permissions'

    def get(self, request, role_code):
        role = get_object_or_404(AccessRole, code=role_code)
        grants = {grant.capability_id: grant.effect for grant in RBACGrant.objects.filter(role=role)}
        entries = []
        for item in permission_catalog():
            capability = capability_for(item['resource'], item['action'])
            effect = grants.get(capability.id) if capability else None
            if effect is None:
                legacy = permission_for(item['resource'], item['action'])
                if legacy and RolePermission.objects.filter(role=role, permission=legacy).exists():
                    effect = RBACGrant.Effect.ALLOW
            entries.append({
                **item,
                'allowed': role.code == AccessRole.Code.SUPERADMIN or effect == RBACGrant.Effect.ALLOW,
                'effect': RBACGrant.Effect.ALLOW if role.code == AccessRole.Code.SUPERADMIN else effect,
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
        with transaction.atomic():
            for item in permissions:
                set_role_permission(
                    request.user,
                    role.code,
                    item['resource'],
                    item['action'],
                    item.get('allowed'),
                    effect=item.get('effect'),
                )
        return self.get(request, role_code)

    def patch(self, request, role_code):
        role = get_object_or_404(AccessRole, code=role_code)
        serializer = RoleStateInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        if not changes:
            raise serializers.ValidationError('Indica al menos un campo para actualizar.')
        for field, value in changes.items():
            setattr(role, field, value)
        try:
            role.save(update_fields=tuple(changes.keys()))
        except DjangoValidationError as error:
            record_audit(
                request.user,
                'deactivate_role',
                'roles',
                result=AuditEvent.Result.DENIED,
                details={'role': role.code, **changes},
            )
            raise serializers.ValidationError(error.messages) from error
        record_audit(
            request.user,
            'update_role',
            'roles',
            details={'role': role.code, **changes},
            instance=role,
        )
        return Response(SuperadminRolesView.serialize(role))


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
        actor_role = role_for_user(request.user)
        if not actor_role or actor_role.code not in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN):
            raise PermissionDenied('Solo administración puede consultar grants individuales.')
        if is_explicitly_denied(request.user, 'permissions', 'view'):
            record_audit(request.user, 'denied_view', 'permissions', result=AuditEvent.Result.DENIED)
            raise PermissionDenied('No tienes permiso para consultar permisos individuales.')
        target = get_object_or_404(User, pk=user_id)
        actor_role = role_for_user(request.user)
        target_role = role_for_user(target)
        if target_role and target_role.code == AccessRole.Code.SUPERADMIN:
            raise PermissionDenied('La matriz global del superadministrador no admite grants individuales.')
        if actor_role.code == AccessRole.Code.ADMIN and (
            not target_role or target_role.code not in (AccessRole.Code.CUSTOMER, AccessRole.Code.CRAFTSWOMAN)
        ):
            raise PermissionDenied('Admin solo puede gestionar permisos de clientes y artesanas.')
        grants = {grant.capability_id: grant.effect for grant in RBACGrant.objects.filter(user=target)}
        legacy_grants = {grant.permission_id: grant.effect for grant in UserPermissionGrant.objects.filter(user=target)}
        delegations = set(
            PermissionDelegation.objects.filter(admin=request.user).values_list('permission_id', flat=True)
        ) if actor_role.code == AccessRole.Code.ADMIN else None
        entries = []
        for item in permission_catalog():
            permission = permission_for(item['resource'], item['action'])
            capability = capability_for(item['resource'], item['action'])
            if delegations is not None and (not permission or permission.pk not in delegations):
                continue
            effect = grants.get(capability.pk) if capability else None
            if effect is None and permission:
                effect = legacy_grants.get(permission.pk)
            entries.append({**item, 'effect': effect})
        return Response({'user_id': target.id, 'username': target.username, 'permissions': entries})

    def put(self, request, user_id):
        actor_role = role_for_user(request.user)
        if not actor_role or actor_role.code not in (AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN):
            raise PermissionDenied('Solo administración puede modificar grants individuales.')
        if is_explicitly_denied(request.user, 'permissions', 'edit'):
            record_audit(request.user, 'denied_change', 'permissions', result=AuditEvent.Result.DENIED)
            raise PermissionDenied('No tienes permiso para cambiar grants individuales.')
        target = get_object_or_404(User, pk=user_id)
        target_role = role_for_user(target)
        if target_role and target_role.code == AccessRole.Code.SUPERADMIN:
            raise PermissionDenied('La matriz global del superadministrador no admite grants individuales.')
        serializer = UserPermissionChangeSerializer(data=request.data.get('permissions'), many=True)
        serializer.is_valid(raise_exception=True)
        permissions = serializer.validated_data
        keys = {(item['resource'], item['action']) for item in permissions}
        if len(keys) != len(permissions):
            raise serializers.ValidationError({'permissions': 'No repitas un permiso en la misma operación.'})
        for item in permissions:
            if not capability_for(item['resource'], item['action']):
                raise serializers.ValidationError({'permissions': 'Uno o más permisos no existen o están inactivos.'})
            permission = permission_for(item['resource'], item['action'])
            actor_role = role_for_user(request.user)
            can_manage = bool(actor_role and actor_role.code == AccessRole.Code.SUPERADMIN)
            if not can_manage and permission:
                can_manage = can_manage_permission(request.user, target, permission)
            if not can_manage:
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
    permission_classes = (RolePermissionAccess,)
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


class SuperadminNavigationView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'navigation'

    def get(self, request):
        items = NavigationItem.objects.prefetch_related('roles').select_related('permission__content_type').order_by('order', 'label')
        return Response([self.serialize_item(item) for item in items])

    @staticmethod
    def serialize_item(item):
        key = permission_key(item.permission) if item.permission_id else None
        return {
            'id': item.id,
            'label': item.label,
            'route_name': item.route_name,
            'anchor': item.anchor,
            'description': item.description,
            'role_codes': list(item.roles.values_list('code', flat=True)),
            'permission_resource': key[0] if key else None,
            'permission_action': key[1] if key else None,
            'required_permissions': navigation_requirement_payload(item.route_name),
            'order': item.order,
            'active': item.active,
        }

    def post(self, request):
        serializer = NavigationItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        role_codes = values.pop('role_codes')
        resource = values.pop('permission_resource', None)
        action = values.pop('permission_action', None)
        item = NavigationItem.objects.create(
            **values,
            permission=permission_for(resource, action) if resource else None,
        )
        item.roles.set(AccessRole.objects.filter(code__in=role_codes))
        record_audit(request.user, 'create_navigation_item', 'navigation', instance=item)
        return Response(self.serialize_item(item), status=status.HTTP_201_CREATED)


class SuperadminNavigationRouteCatalogView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'navigation'

    def get(self, request):
        return Response([navigation_route_payload(route) for route in NAVIGATION_ROUTE_CATALOG])


class SuperadminNavigationDetailView(APIView):
    permission_classes = (RolePermissionAccess,)
    rbac_resource = 'navigation'

    def patch(self, request, item_id):
        item = get_object_or_404(NavigationItem, pk=item_id)
        serializer = NavigationItemWriteSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        role_codes = values.pop('role_codes', None)
        resource = values.pop('permission_resource', serializers.empty)
        action = values.pop('permission_action', serializers.empty)
        if resource is not serializers.empty or action is not serializers.empty:
            current_resource, current_action = permission_key(item.permission) if item.permission_id else (None, None)
            next_resource = current_resource if resource is serializers.empty else resource
            next_action = current_action if action is serializers.empty else action
            if bool(next_resource) != bool(next_action):
                raise serializers.ValidationError('Selecciona tanto el recurso como la acción requerida, o deja ambos vacíos.')
            item.permission = permission_for(next_resource, next_action) if next_resource else None
        for field, value in values.items():
            setattr(item, field, value)
        item.save()
        if role_codes is not None:
            item.roles.set(AccessRole.objects.filter(code__in=role_codes))
        record_audit(request.user, 'update_navigation_item', 'navigation', instance=item)
        return Response(SuperadminNavigationView.serialize_item(item))

    def delete(self, request, item_id):
        item = get_object_or_404(NavigationItem, pk=item_id)
        if item.route_name == 'admin.access':
            raise serializers.ValidationError('La pantalla de administración RBAC no se puede eliminar.')
        record_audit(request.user, 'delete_navigation_item', 'navigation', instance=item)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleNavigationMenuView(APIView):
    """Devuelve solo opciones permitidas para el rol y los permisos efectivos actuales."""
    permission_classes = (IsAuthenticated, HasAssignedRole)

    def get(self, request):
        role = role_for_user(request.user)
        if role is None:
            return Response([])
        visible = []
        allowed_routes = {
            route_name for route_name in NAVIGATION_ROUTE_CATALOG
            if role.code in navigation_role_codes(route_name)
        }
        items = NavigationItem.objects.filter(active=True, roles=role).select_related('permission__content_type').order_by('order', 'label')
        for item in items:
            if item.route_name not in allowed_routes:
                continue
            if item.route_name.startswith('customer.') and role.code != AccessRole.Code.CUSTOMER and not Customer.objects.filter(user=request.user).exists():
                continue
            if item.route_name.startswith('craftswoman.') and not Craftswoman.objects.filter(user=request.user, active=True).exists():
                continue
            if any(
                not has_rbac_permission(request.user, resource, action)
                for resource, action in navigation_requirements(item.route_name)
            ):
                continue
            if any(
                record_scope_for(request.user, resource) != 'all'
                for resource in NAVIGATION_ROUTE_CATALOG[item.route_name].get('all_scope', ())
            ):
                continue
            if item.permission_id:
                key = permission_key(item.permission)
                if not key or not has_rbac_permission(request.user, *key):
                    continue
            visible.append(SuperadminNavigationView.serialize_item(item))
        return Response(visible)


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
    rbac_actions = {'PATCH': category_visibility_action}

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
    rbac_actions = {'PATCH': product_publish_action}

    def patch(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        previous_stock = product.stock
        serializer = AdminProductSerializer(product, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            product = serializer.save()
            if product.stock != previous_stock:
                record_audit(
                    request.user,
                    'stock_adjustment',
                    'products',
                    details={'stock_movement': {
                        'sku': product.sku,
                        'product_name': product.name,
                        'before': previous_stock,
                        'after': product.stock,
                        'delta': product.stock - previous_stock,
                        'reason': 'admin_adjustment',
                    }},
                    instance=product,
                )
            record_audit(
                request.user,
                'update_product',
                'products',
                instance=product,
            )
        return Response(AdminProductSerializer(product, context={'request': request}).data)


class AdminOrderStatusView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'orders'
    rbac_actions = {'PATCH': order_admin_action}

    def patch(self, request, order_id):
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            order = get_object_or_404(
                Order.objects.select_for_update().select_related('customer__user'),
                id=order_id,
            )
            previous_status = order.status
            next_status = serializer.validated_data['status']
            if not can_transition_order(previous_status, next_status, 'admin'):
                return Response(
                    {'detail': 'Transición de estado no permitida.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            items = list(order.items.select_related('product__custom_design'))
            designs = [item.product.custom_design for item in items if item.product.custom_design_id]
            if designs and not has_rbac_permission(request.user, 'orders', 'manage_design_status'):
                raise PermissionDenied('Este pedido incluye un diseño personalizado y necesitas permiso para cambiar su estado desde el pedido.')
            order.status = next_status
            order.save(update_fields=('status', 'updated_at'))
            for design in designs:
                design.status = next_status
                design.save(update_fields=('status',))
            OrderItem.objects.filter(order=order).update(status=next_status)
            record_audit(
                request.user,
                'change_order_status',
                'orders',
                affected_user=order.customer.user,
                details={'from': previous_status, 'to': order.status},
                instance=order,
            )
        return Response(OrderSerializer(order, context={'request': request, 'status_actor': 'admin'}).data)


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


class CraftswomanProfileView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'craftswomen'
    rbac_actions = {'GET': 'view', 'PATCH': 'edit'}

    def get(self, request):
        profile = get_object_or_404(Craftswoman, user=request.user, active=True)
        return Response(CraftswomanProfileSerializer(profile).data)

    def patch(self, request):
        profile = get_object_or_404(Craftswoman, user=request.user, active=True)
        serializer = CraftswomanProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            profile = serializer.save()
            if 'name' in serializer.validated_data:
                request.user.first_name = profile.name
                request.user.save(update_fields=('first_name',))
            record_audit(
                request.user,
                'update_own_craftswoman_profile',
                'craftswomen',
                affected_user=request.user,
                details={'changed_fields': sorted(serializer.validated_data)},
                instance=profile,
            )
        return Response(CraftswomanProfileSerializer(profile).data)


class CartView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'cart'

    def get(self, request):
        customer = _customer_for(request.user)
        items, total = _cart_items(request, customer)
        return Response({
            'items': items,
            'total': str(total),
            'count': sum(item['quantity'] for item in items),
            'legacy_items': unresolved_legacy_cart_items(request),
        })


class LegacyCartItemRemovalView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'cart'

    def post(self, request):
        customer = _customer_for(request.user)
        serializer = LegacyCartItemRemovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.validated_data['key']
        session_cart = request.session.get('cart')
        was_pending = isinstance(session_cart, dict) and any(
            str(item_key) == key for item_key in session_cart
        )
        # Recheck migration first: if an entry became recoverable, preserve it
        # as a persistent cart row instead of discarding it from the session.
        _sync_legacy_session_cart(request, customer)
        if not discard_unresolved_legacy_cart_item(request, key):
            if was_pending and key not in {item['key'] for item in unresolved_legacy_cart_items(request)}:
                return Response({
                    'detail': 'La pieza anterior se recuperó y quedó guardada en tu carrito.',
                    'recovered': True,
                })
            return Response(
                {'detail': 'Ese elemento ya no está pendiente de recuperación.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'detail': 'Elemento antiguo retirado.', 'recovered': False})


class CartItemListView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'cart'

    def post(self, request):
        customer = _customer_for(request.user)
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data['quantity']
        _sync_legacy_session_cart(request, customer)
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(pk=customer.pk)
            product = get_object_or_404(
                Product.objects.select_for_update().filter(active=True, custom_design__isnull=True),
                id=serializer.validated_data['product_id'],
            )
            row, created = CustomerCartItem.objects.select_for_update().get_or_create(
                customer=customer, product=product, defaults={'quantity': quantity},
            )
            new_quantity = row.quantity if created else row.quantity + quantity
            if product.stock < new_quantity:
                if created:
                    row.delete()
                return Response({'detail': 'No hay suficientes unidades disponibles.'}, status=status.HTTP_400_BAD_REQUEST)
            if not created:
                row.quantity = new_quantity
                row.save(update_fields=('quantity', 'updated_at'))
        return Response({'detail': 'Producto agregado.', 'product_id': product.id, 'quantity': new_quantity}, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'cart'

    def patch(self, request, product_id):
        customer = _customer_for(request.user)
        serializer = CartQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data['quantity']
        _sync_legacy_session_cart(request, customer)
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(pk=customer.pk)
            product = get_object_or_404(
                Product.objects.select_for_update().filter(
                    models.Q(active=True, custom_design__isnull=True)
                    | models.Q(custom_design__customer=customer),
                ).distinct(),
                id=product_id,
            )
            row = get_object_or_404(
                CustomerCartItem.objects.select_for_update(),
                customer=customer, product=product,
            )
            if product.custom_design_id and quantity != 1:
                return Response(
                    {'detail': 'La cantidad del diseño personalizado ya está incluida en su precio. Puedes retirar el diseño del carrito, pero no multiplicarlo.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if quantity > product.stock:
                return Response({'detail': 'No hay suficientes unidades disponibles.'}, status=status.HTTP_400_BAD_REQUEST)
            row.quantity = quantity
            row.save(update_fields=('quantity', 'updated_at'))
        return Response({'detail': 'Carrito actualizado.', 'product_id': product.id, 'quantity': quantity})

    def delete(self, request, product_id):
        customer = _customer_for(request.user)
        _sync_legacy_session_cart(request, customer)
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(pk=customer.pk)
            CustomerCartItem.objects.filter(customer=customer, product_id=product_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoritesView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'favorites'

    def get(self, request):
        customer = _customer_for(request.user)
        product_ids = CustomerFavorite.objects.filter(
            customer=customer,
            product__active=True,
            product__custom_design__isnull=True,
        ).order_by('-created_at', '-id').values_list('product_id', flat=True)
        return Response({'product_ids': list(product_ids)})

    def post(self, request):
        customer = _customer_for(request.user)
        serializer = FavoriteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(
            Product.objects.filter(active=True, custom_design__isnull=True),
            pk=serializer.validated_data['product_id'],
        )
        favorite, created = CustomerFavorite.objects.get_or_create(customer=customer, product=product)
        if created:
            record_audit(
                request.user,
                'add_favorite',
                'favorites',
                affected_user=request.user,
                instance=favorite,
                details={'product_id': product.id},
            )
        return Response({'product_id': product.id, 'saved': True}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class FavoriteDetailView(APIView):
    permission_classes = (CustomerOnly,)
    rbac_resource = 'favorites'

    def delete(self, request, product_id):
        customer = _customer_for(request.user)
        favorite = CustomerFavorite.objects.filter(customer=customer, product_id=product_id).first()
        if favorite:
            record_audit(
                request.user,
                'remove_favorite',
                'favorites',
                affected_user=request.user,
                details={'product_id': product_id},
            )
            favorite.delete()
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
        data = serializer.validated_data
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(pk=customer.pk)
            _sync_legacy_session_cart(request, customer)
            cart_rows = list(
                CustomerCartItem.objects.select_for_update().filter(customer=customer)
                .order_by('product_id')
            )
            if not cart_rows:
                return Response({'detail': 'Tu carrito está vacío.'}, status=status.HTTP_400_BAD_REQUEST)
            products = {
                product.pk: product
                for product in Product.objects.select_for_update().filter(
                    pk__in=[row.product_id for row in cart_rows],
                ).select_related('custom_design', 'craftswoman').order_by('pk')
            }
            for row in cart_rows:
                product = products.get(row.product_id)
                if not product:
                    return Response({'detail': 'Un producto del carrito ya no existe. Actualiza el carrito antes de confirmar.'}, status=status.HTTP_400_BAD_REQUEST)
                if row.quantity < 1 or row.quantity > MAX_CART_QUANTITY:
                    return Response({'detail': f'La cantidad de {product.name} no es válida.'}, status=status.HTTP_400_BAD_REQUEST)
                if product.custom_design_id:
                    if product.custom_design.customer_id != customer.id or row.quantity != 1:
                        return Response({'detail': 'El diseño personalizado no pertenece a esta cuenta o su cantidad no es válida.'}, status=status.HTTP_400_BAD_REQUEST)
                elif not product.active:
                    return Response({'detail': f'{product.name} ya no está disponible. Retíralo del carrito para continuar.'}, status=status.HTTP_400_BAD_REQUEST)
                if product.stock < row.quantity:
                    return Response({'detail': f'No hay suficientes unidades de {product.name}. Ajusta la cantidad antes de confirmar.'}, status=status.HTTP_400_BAD_REQUEST)

            order = Order.objects.create(
                customer=customer,
                payment_method=data['payment_method'],
                shipping_address=f"{data['address'].strip()}, {data['city'].strip()}",
                notes=data.get('notes', '').strip(),
            )
            for row in cart_rows:
                product = products[row.product_id]
                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=row.quantity,
                    unit_price=product.price,
                    craftswoman=product.craftswoman,
                    assigned_at=timezone.now() if product.craftswoman_id else None,
                )
                if product.craftswoman_id and product.craftswoman.user_id:
                    InAppNotification.objects.create(
                        recipient_id=product.craftswoman.user_id,
                        order_item=order_item,
                        title='Nuevo trabajo asignado',
                        message=f'El pedido #{order.id} incluye {product.name}, asignado a tu taller.',
                    )
                previous_stock = product.stock
                product.stock -= row.quantity
                product.save(update_fields=('stock', 'updated_at'))
                record_audit(
                    request.user,
                    'stock_checkout_decrement',
                    'products',
                    affected_user=request.user,
                    details={'stock_movement': {
                        'sku': product.sku,
                        'product_name': product.name,
                        'before': previous_stock,
                        'after': product.stock,
                        'delta': -row.quantity,
                        'reason': 'checkout',
                        'order_id': order.id,
                    }},
                    instance=product,
                )
            customer.address = data['address'].strip()
            customer.city = data['city'].strip()
            customer.save(update_fields=('address', 'city'))
            CustomerCartItem.objects.filter(pk__in=[row.pk for row in cart_rows]).delete()
            record_audit(
                request.user,
                'checkout',
                'orders',
                affected_user=request.user,
                details={'item_count': len(cart_rows)},
                instance=order,
            )
            _sync_order_legacy_assignee(order)
        request.session.pop('cart', None)
        request.session.modified = True
        order = Order.objects.prefetch_related('items__product').select_related('craftswoman').get(id=order.id)
        return Response(OrderSerializer(order, context={'request': request}).data, status=status.HTTP_201_CREATED)


class OrderListView(PaginatedAPIView):
    permission_classes = (OrderAccess,)
    rbac_resource = 'orders'

    def get(self, request):
        orders = _customer_orders(request.user).select_related('craftswoman').prefetch_related('items__product')
        return self.get_paginated_response(OrderSerializer(self.paginate_queryset(orders), many=True, context={'request': request}).data)


class AdminOrderListView(PaginatedAPIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'orders'

    def get(self, request):
        orders = Order.objects.select_related(
            'customer__user', 'craftswoman',
        ).prefetch_related('items__product').order_by('-created_at', '-id')

        selected_status = request.query_params.get('status', '').strip()
        if selected_status:
            valid_statuses = {value for value, _label in Order.Status.choices}
            if selected_status not in valid_statuses:
                raise serializers.ValidationError({'status': 'Selecciona un estado de pedido válido.'})
            orders = orders.filter(status=selected_status)

        assignment = request.query_params.get('assignment', '').strip().lower()
        craftswoman_id = request.query_params.get('craftswoman_id', '').strip()
        # Accept the original Sprint 1 query values during migration to the
        # separate assignment and craftswoman filters.
        if craftswoman_id in {'assigned', 'unassigned'}:
            if assignment and assignment != craftswoman_id:
                raise serializers.ValidationError({'assignment': 'Los filtros de asignación son incompatibles.'})
            assignment = craftswoman_id
            craftswoman_id = ''
        if assignment not in {'', 'all', 'assigned', 'unassigned'}:
            raise serializers.ValidationError({'assignment': 'Selecciona una opción de asignación válida.'})
        if assignment == 'unassigned' and craftswoman_id:
            raise serializers.ValidationError({'craftswoman_id': 'No combines una tejedora con pedidos sin asignar.'})
        if assignment == 'assigned':
            orders = orders.filter(models.Q(craftswoman__isnull=False) | models.Q(items__craftswoman__isnull=False) | models.Q(items__product__craftswoman__isnull=False))
        elif assignment == 'unassigned':
            orders = orders.filter(craftswoman__isnull=True).exclude(items__craftswoman__isnull=False).exclude(items__product__craftswoman__isnull=False)
        if craftswoman_id:
            if not craftswoman_id.isdecimal() or int(craftswoman_id) < 1:
                raise serializers.ValidationError({'craftswoman_id': 'Selecciona una tejedora válida.'})
            orders = orders.filter(models.Q(craftswoman_id=int(craftswoman_id)) | models.Q(items__craftswoman_id=int(craftswoman_id)) | models.Q(items__product__craftswoman_id=int(craftswoman_id)))

        customer_id = request.query_params.get('customer_id', '').strip()
        if customer_id:
            if not customer_id.isdecimal() or int(customer_id) < 1:
                raise serializers.ValidationError({'customer_id': 'Selecciona un cliente válido.'})
            orders = orders.filter(customer_id=int(customer_id))

        search = request.query_params.get('search', '').strip()
        if search:
            search_filter = (
                models.Q(customer__name__icontains=search)
                | models.Q(customer__email__icontains=search)
                | models.Q(customer__user__username__icontains=search)
                | models.Q(customer__user__first_name__icontains=search)
                | models.Q(customer__user__last_name__icontains=search)
                | models.Q(craftswoman__name__icontains=search)
                | models.Q(items__craftswoman__name__icontains=search)
                | models.Q(items__product__craftswoman__name__icontains=search)
                | models.Q(items__product__name__icontains=search)
            )
            if search.isdecimal():
                search_filter |= models.Q(pk=int(search))
            orders = orders.filter(search_filter).distinct()

        return self.get_paginated_response(
            OrderSerializer(
                self.paginate_queryset(orders), many=True,
                context={'request': request, 'status_actor': 'admin'},
            ).data,
        )


class AdminOrderFiltersView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'orders'

    def get(self, request):
        craftswomen = Craftswoman.objects.order_by('name', 'id').values('id', 'name')
        return Response({'craftswomen': list(craftswomen)})


class AdminOrderSummaryView(APIView):
    permission_classes = (AdminOrSuperadmin,)
    rbac_resource = 'orders'

    def get(self, request):
        queryset = Order.objects.all()
        count_by_status = {
            row['status']: row['count']
            for row in queryset.values('status').annotate(count=Count('id'))
        }
        for order_status, _label in Order.Status.choices:
            count_by_status.setdefault(order_status, 0)
        recent = queryset.select_related('customer', 'craftswoman').prefetch_related(
            'items__product',
        ).order_by('-created_at', '-id')[:3]
        return Response({
            'total_count': sum(count_by_status.values()),
            'by_status': count_by_status,
            'pending_count': count_by_status[Order.Status.PENDING],
            # Preserve the dashboard's prior active-status definition. Whether
            # completed and paid should count as active remains a business decision.
            'active_count': sum(count_by_status[value] for value in ADMIN_ACTIVE_ORDER_STATUSES),
            'recent_orders': OrderSerializer(recent, many=True, context={'request': request}).data,
        })


class OrderDetailView(APIView):
    permission_classes = (OrderAccess,)
    rbac_resource = 'orders'

    def get(self, request, order_id):
        order = get_object_or_404(
            _customer_orders(request.user).select_related('craftswoman').prefetch_related('items__product'),
            id=order_id,
        )
        return Response(OrderSerializer(order, context={'request': request}).data)


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
                defaults={'description': 'Mantas configuradas por clientes.', 'active': True, 'is_internal': True},
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
            CustomerCartItem.objects.update_or_create(
                customer=customer,
                product=product,
                defaults={'quantity': 1},
            )
        return Response(
            {**CustomDesignSerializer(design).data, 'product_id': product.id},
            status=status.HTTP_201_CREATED,
        )


class CraftswomanProductsView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'products'

    def get(self, request):
        craftswoman = get_object_or_404(Craftswoman, user=request.user)
        products = Product.objects.filter(craftswoman=craftswoman).select_related('category', 'craftswoman')
        return Response(ProductSerializer(products, many=True, context={'request': request}).data)

    def post(self, request):
        if not has_rbac_permission(request.user, 'products', 'add'):
            raise PermissionDenied('No tienes permiso para registrar productos.')
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        serializer = CraftswomanProductWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save(craftswoman=craftswoman, active=False)
        record_audit(
            request.user,
            'craftswoman_submit_product',
            'products',
            details={'product_name': product.name, 'publication_status': 'pending'},
            instance=product,
        )
        return Response(ProductSerializer(product, context={'request': request}).data, status=status.HTTP_201_CREATED)


class CraftswomanProductDetailView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'products'

    def patch(self, request, product_id):
        if not has_rbac_permission(request.user, 'products', 'change'):
            raise PermissionDenied('No tienes permiso para corregir tus productos.')
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        product = get_object_or_404(Product, id=product_id, craftswoman=craftswoman)
        previous_stock = product.stock
        serializer = CraftswomanProductWriteSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            product = serializer.save(active=False)
            if product.stock != previous_stock:
                record_audit(
                    request.user,
                    'craftswoman_stock_adjustment',
                    'products',
                    details={'stock_movement': {
                        'sku': product.sku,
                        'product_name': product.name,
                        'before': previous_stock,
                        'after': product.stock,
                        'delta': product.stock - previous_stock,
                        'reason': 'craftswoman_adjustment',
                    }},
                    instance=product,
                )
            record_audit(
                request.user,
                'craftswoman_resubmit_product',
                'products',
                details={'product_name': product.name, 'publication_status': 'pending_review'},
                instance=product,
            )
        return Response(ProductSerializer(product).data)


class CraftswomanDashboardView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'orders'

    def get(self, request):
        craftswoman = get_object_or_404(Craftswoman, user=request.user)
        available = OrderItem.objects.filter(
            craftswoman__isnull=True, product__craftswoman__isnull=True, status=Order.Status.PENDING,
            order__status=Order.Status.PENDING,
        ).select_related('order__customer', 'product') if craftswoman.active else OrderItem.objects.none()
        assigned = OrderItem.objects.filter(craftswoman=craftswoman).select_related(
            'order__customer', 'product', 'craftswoman', 'product__custom_design',
        ).order_by('-order__created_at', 'id')
        designs = craftswoman.custom_designs.select_related('customer') if has_rbac_permission(request.user, 'designs', 'view') else CustomDesign.objects.none()
        notifications = InAppNotification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
        legacy_available = Order.objects.annotate(work_item_count=Count('items')).filter(
            work_item_count=1, craftswoman__isnull=True, status=Order.Status.PENDING,
            items__craftswoman__isnull=True, items__product__craftswoman__isnull=True,
        ) if craftswoman.active else Order.objects.none()
        return Response({
            'active': craftswoman.active,
            'available_items': [{**OrderItemSerializer(item, context={'status_actor': 'craftswoman'}).data,
                                 'order_id': item.order_id, 'customer_name': item.order.customer.name,
                                 'order_created_at': item.order.created_at} for item in available],
            'assigned_items': [{**OrderItemSerializer(item, context={'status_actor': 'craftswoman'}).data,
                                'order_id': item.order_id, 'customer_name': item.order.customer.name,
                                'order_created_at': item.order.created_at} for item in assigned],
            # Keep the previous keys for clients deployed during the transition.
            'available_orders': OrderSerializer(legacy_available, many=True, context={'request': request}).data,
            'orders': OrderSerializer(craftswoman.orders.select_related('customer').prefetch_related('items__product'), many=True,
                                      context={'request': request, 'status_actor': 'craftswoman'}).data,
            'designs': CustomDesignSerializer(
                designs, many=True, context={'request': request, 'status_actor': 'craftswoman'},
            ).data,
            'notifications': [{'id': item.id, 'title': item.title, 'message': item.message,
                               'order_id': item.order_item.order_id, 'created_at': item.created_at,
                               'read': item.read_at is not None} for item in notifications],
        })


class AcceptOrderView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'orders'
    rbac_actions = {'POST': 'assign'}

    def post(self, request, order_id):
        if not has_rbac_permission(request.user, 'orders', 'assign'):
            raise PermissionDenied('No tienes permiso para aceptar pedidos.')
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update().select_related('customer__user'), pk=order_id, status=Order.Status.PENDING)
            items = list(order.items.select_related('product__craftswoman', 'product__custom_design', 'craftswoman').order_by('id'))
            if len(items) != 1:
                return Response({'detail': 'Este pedido contiene varios trabajos. Selecciona la partida que deseas aceptar.'}, status=status.HTTP_400_BAD_REQUEST)
            item = items[0]
            response = _accept_order_item(request, craftswoman, item)
            if isinstance(response, Response):
                return response
            _recompute_order_status(order)
            _sync_order_legacy_assignee(order)
            record_audit(request.user, 'accept_order_item', 'orders', affected_user=order.customer.user,
                         details={'status': item.status, 'craftswoman_id': craftswoman.id}, instance=item)
            record_audit(request.user, 'accept_order', 'orders', affected_user=order.customer.user,
                         details={'status': order.status, 'craftswoman_id': craftswoman.id, 'item_id': item.id}, instance=order)
        order.refresh_from_db()
        return Response(OrderSerializer(order, context={'request': request, 'status_actor': 'craftswoman'}).data)


def _accept_order_item(request, craftswoman, item):
    if item.order.status != Order.Status.PENDING or item.status != Order.Status.PENDING:
        return Response({'detail': 'Este trabajo ya no está disponible para aceptación.'}, status=status.HTTP_409_CONFLICT)
    if item.product.craftswoman_id and item.product.craftswoman_id != craftswoman.id:
        raise PermissionDenied('Este producto está asignado a otra tejedora.')
    if item.craftswoman_id and item.craftswoman_id != craftswoman.id:
        raise PermissionDenied('Este trabajo ya está asignado a otra tejedora.')
    if item.product.custom_design_id and not has_rbac_permission(request.user, 'designs', 'change'):
        raise PermissionDenied('No tienes permiso para aceptar trabajos con diseños personalizados.')
    if not can_transition_order(item.status, Order.Status.ACCEPTED, 'assignment'):
        return Response({'detail': 'Transición de asignación no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
    item.craftswoman = craftswoman
    item.assigned_at = timezone.now()
    item.assigned_by = request.user
    item.status = Order.Status.ACCEPTED
    item.save(update_fields=('craftswoman', 'assigned_at', 'assigned_by', 'status'))
    design = getattr(item.product, 'custom_design', None)
    if design:
        design.craftswoman = craftswoman
        design.status = Order.Status.ACCEPTED
        design.save(update_fields=('craftswoman', 'status'))
    return None


class AcceptWorkItemView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'orders'
    rbac_actions = {'POST': 'assign'}

    def post(self, request, item_id):
        if not has_rbac_permission(request.user, 'orders', 'assign'):
            raise PermissionDenied('No tienes permiso para aceptar trabajos.')
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        with transaction.atomic():
            item_ref = get_object_or_404(OrderItem.objects.only('id', 'order_id'), pk=item_id)
            order = get_object_or_404(Order.objects.select_for_update().select_related('customer__user'), pk=item_ref.order_id)
            item = get_object_or_404(OrderItem.objects.select_related(
                'order__customer__user', 'product__craftswoman', 'product__custom_design', 'craftswoman',
            ).select_for_update(), pk=item_id)
            result = _accept_order_item(request, craftswoman, item)
            if result:
                return result
            _recompute_order_status(order)
            _sync_order_legacy_assignee(order)
            record_audit(request.user, 'accept_order_item', 'orders', affected_user=order.customer.user,
                         details={'status': item.status, 'craftswoman_id': craftswoman.id}, instance=item)
        item.refresh_from_db()
        return Response(OrderItemSerializer(item, context={'status_actor': 'craftswoman'}).data)


class CraftswomanOrderStatusView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'orders'

    def patch(self, request, order_id):
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update().filter(craftswoman=craftswoman), id=order_id)
            items = list(order.items.select_related('product__custom_design').filter(craftswoman=craftswoman))
            if not items or order.items.exclude(craftswoman=craftswoman).exists():
                raise PermissionDenied('Este pedido contiene trabajos de otros talleres; actualiza cada partida por separado.')
            new_status = serializer.validated_data['status']
            if any(item.product.custom_design_id for item in items) and not has_rbac_permission(request.user, 'designs', 'change'):
                raise PermissionDenied('Este pedido incluye un diseño personalizado y necesitas permiso para gestionarlo.')
            if not all(can_transition_order(item.status, new_status, 'craftswoman') for item in items):
                return Response({'detail': 'Transición de estado no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
            previous_status = order.status
            for item in items:
                item.status = new_status
                item.save(update_fields=('status',))
                design = getattr(item.product, 'custom_design', None)
                if design:
                    design.status = new_status
                    design.save(update_fields=('status',))
            _recompute_order_status(order)
            record_audit(
                request.user,
                'craftswoman_change_order_status',
                'orders',
                affected_user=order.customer.user,
                details={'from': previous_status, 'to': new_status},
                instance=order,
            )
            for item in items:
                record_audit(request.user, 'craftswoman_change_order_item_status', 'orders',
                             affected_user=order.customer.user,
                             details={'from': previous_status, 'to': new_status, 'order_id': order.id}, instance=item)
            order.refresh_from_db()
        return Response(OrderSerializer(order, context={'request': request, 'status_actor': 'craftswoman'}).data)


class CraftswomanWorkItemStatusView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'orders'

    def patch(self, request, item_id):
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            item_ref = get_object_or_404(OrderItem.objects.only('id', 'order_id'), pk=item_id)
            order = get_object_or_404(Order.objects.select_for_update().select_related('customer__user'), pk=item_ref.order_id)
            item = get_object_or_404(OrderItem.objects.select_related(
                'product__custom_design', 'order__customer__user',
            ).select_for_update().filter(craftswoman=craftswoman), pk=item_id)
            if item.product.custom_design_id and not has_rbac_permission(request.user, 'designs', 'change'):
                raise PermissionDenied('Este trabajo incluye un diseño personalizado y necesita permiso específico.')
            next_status = serializer.validated_data['status']
            if not can_transition_order(item.status, next_status, 'craftswoman'):
                return Response({'detail': 'Transición de estado no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
            previous_status = item.status
            item.status = next_status
            item.save(update_fields=('status',))
            design = getattr(item.product, 'custom_design', None)
            if design:
                design.status = next_status
                design.save(update_fields=('status',))
            _recompute_order_status(order)
            record_audit(request.user, 'craftswoman_change_order_item_status', 'orders',
                         affected_user=order.customer.user,
                         details={'from': previous_status, 'to': next_status, 'order_id': order.id}, instance=item)
        return Response(OrderItemSerializer(item, context={'status_actor': 'craftswoman'}).data)


def _recompute_order_status(order):
    return recompute_order_tracking_status(order)


def _sync_order_legacy_assignee(order):
    return sync_legacy_order_craftswoman(order)


class CraftswomanDesignStatusView(APIView):
    permission_classes = (CraftswomanOnly,)
    rbac_resource = 'designs'

    def patch(self, request, design_id):
        craftswoman = get_object_or_404(Craftswoman, user=request.user, active=True)
        design = get_object_or_404(CustomDesign, id=design_id, craftswoman=craftswoman)
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        if not can_transition_order(design.status, new_status, 'craftswoman'):
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
