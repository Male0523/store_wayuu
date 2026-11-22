import json
import os
import stat
import subprocess
from zipfile import ZipFile
from decimal import Decimal
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib import admin as django_admin
from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.test.client import MULTIPART_CONTENT, encode_multipart
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from .navigation import navigation_menu
from .api import NAVIGATION_ROUTE_CATALOG
from .admin import (
    CategoryAdmin,
    CraftswomanAdmin,
    CustomerAdmin,
    CustomDesignAdmin,
    OrderAdmin,
    OrderItemInline,
    NavigationItemAdminForm,
    PermissionDelegationAdmin,
    ProductAdmin,
    ProtectedUserRoleForm,
    UserRoleAdmin,
    WayuuUserAdmin,
)
from .models import (
    AccessRole,
    AuditEvent,
    Craftswoman,
    CustomDesign,
    Category,
    Customer,
    CustomerCartItem,
    CustomerFavorite,
    InAppNotification,
    NavigationItem,
    Order,
    OrderItem,
    PermissionDelegation,
    Product,
    RolePermission,
    RBACCapability,
    RBACGrant,
    UserPermissionGrant,
    UserRole,
)
from .order_workflow import allowed_order_transitions, can_transition_order
from .rbac import (
    PERMISSION_ACTIONS,
    PERMISSION_RESOURCES,
    assign_role,
    effective_permission_keys,
    has_permission,
    permission_catalog,
    permission_for,
    role_for_user,
    set_permission_delegation,
    set_role_permission,
    set_user_permission,
)


class OrderWorkflowTests(SimpleTestCase):
    def test_shared_transition_matrix_matches_the_documented_actor_rules(self):
        expected = {
            Order.Status.PENDING: {
                'admin': {Order.Status.PREPARING, Order.Status.CANCELLED},
                'craftswoman': set(),
                'assignment': {Order.Status.ACCEPTED},
            },
            Order.Status.ACCEPTED: {
                'admin': {Order.Status.PREPARING, Order.Status.CANCELLED},
                'craftswoman': {Order.Status.WEAVING},
                'assignment': set(),
            },
            Order.Status.WEAVING: {
                'admin': {Order.Status.PREPARING, Order.Status.CANCELLED},
                'craftswoman': {Order.Status.ACCEPTED, Order.Status.COMPLETED},
                'assignment': set(),
            },
            Order.Status.COMPLETED: {
                'admin': {Order.Status.PAID, Order.Status.PREPARING, Order.Status.CANCELLED},
                'craftswoman': set(),
                'assignment': set(),
            },
            Order.Status.PAID: {
                'admin': {Order.Status.PREPARING, Order.Status.CANCELLED},
                'craftswoman': set(),
                'assignment': set(),
            },
            Order.Status.PREPARING: {
                'admin': {Order.Status.SHIPPED, Order.Status.CANCELLED},
                'craftswoman': set(),
                'assignment': set(),
            },
            Order.Status.SHIPPED: {
                'admin': {Order.Status.DELIVERED, Order.Status.CANCELLED},
                'craftswoman': set(),
                'assignment': set(),
            },
            Order.Status.DELIVERED: {'admin': set(), 'craftswoman': set(), 'assignment': set()},
            Order.Status.CANCELLED: {'admin': set(), 'craftswoman': set(), 'assignment': set()},
        }
        for current_status, actor_rules in expected.items():
            for actor, next_statuses in actor_rules.items():
                with self.subTest(status=current_status, actor=actor):
                    self.assertEqual(set(allowed_order_transitions(current_status, actor)), next_statuses)
        self.assertTrue(can_transition_order(Order.Status.PENDING, Order.Status.ACCEPTED, 'assignment'))
        self.assertFalse(can_transition_order(Order.Status.PENDING, Order.Status.ACCEPTED, 'admin'))


class StoreAPITests(TestCase):
    @staticmethod
    def make_test_image(image_format='PNG'):
        from PIL import Image

        stream = BytesIO()
        Image.new('RGB', (3, 2), color='red').save(stream, format=image_format)
        return stream.getvalue()

    def setUp(self):
        self.category = Category.objects.create(name='Mantas', active=True)
        self.product = Product.objects.create(
            sku='API-TEST-001',
            name='Manta de prueba',
            category=self.category,
            description='Producto para pruebas de API.',
            color='Rojo y azul',
            size='M',
            price=Decimal('25000'),
            stock=4,
            active=True,
        )
        self.user = User.objects.create_user(
            username='cliente-api',
            email='cliente-api@example.com',
            password='ClaveSegura2026!',
            first_name='Cliente API',
        )
        self.customer = Customer.objects.create(
            user=self.user,
            name='Cliente API',
            email='cliente-api@example.com',
        )
        self.assign_role(self.user, AccessRole.Code.CUSTOMER)

    def assign_role(self, user, role_code):
        role = AccessRole.objects.get(code=role_code)
        UserRole.objects.create(user=user, role=role)
        return user

    def create_role_user(self, username, role_code):
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='ClaveSegura2026!',
        )
        return self.assign_role(user, role_code)

    def test_health_and_product_catalog(self):
        health = self.client.get('/api/v1/')
        products = self.client.get('/api/v1/products/?search=prueba&category=%s' % self.category.id)

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {'status': 'ok', 'api_version': '1'})
        self.assertEqual(products.status_code, 200)
        self.assertEqual(products.json()['count'], 1)
        self.assertEqual(products.json()['results'][0]['id'], self.product.id)
        self.assertEqual(products.json()['results'][0]['price'], '25000')

    def test_public_catalog_includes_active_empty_commercial_categories_only(self):
        empty = Category.objects.create(name='Mochilas', active=True)
        inactive = Category.objects.create(name='Categoría inactiva', active=False)
        internal = Category.objects.create(name='Diseños personalizados', active=True, is_internal=True)
        Product.objects.create(
            sku='API-CATALOG-INTERNAL', name='Diseño interno', category=internal,
            custom_design=CustomDesign.objects.create(
                customer=self.customer, pattern='rombos', base_color='#111111',
                accent_color_one='#222222', accent_color_two='#333333', size='M',
                estimated_price=Decimal('100000'),
            ),
            price=Decimal('100000'), stock=1, active=True,
        )

        categories = self.client.get('/api/v1/categories/')
        catalog = self.client.get('/api/v1/products/')

        self.assertEqual(categories.status_code, 200)
        self.assertIn(empty.id, [item['id'] for item in categories.json()])
        self.assertNotIn(inactive.id, [item['id'] for item in categories.json()])
        self.assertNotIn(internal.id, [item['id'] for item in categories.json()])
        self.assertEqual(catalog.json()['count'], 1)
        self.assertEqual(catalog.json()['results'][0]['id'], self.product.id)
        self.assertEqual(self.client.get(f'/api/v1/products/{self.product.id}/').status_code, 200)

    def test_public_product_preserves_real_craftswoman_profile_and_image_reference(self):
        craft_user = self.create_role_user('profile-on-public-product', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(
            user=craft_user, name='Tejedora de prueba', community='Comunidad real',
            region='La Guajira', biography='Perfil de prueba', active=True,
        )
        image_data = 'data:image/png;base64,aGVsbG8='
        product = Product.objects.create(
            sku='API-PROFILE-IMAGE', name='Manta con perfil', category=self.category,
            craftswoman=craftswoman, price=Decimal('45000'), stock=2,
            image_url=image_data, active=True,
        )

        listed = self.client.get('/api/v1/products/').json()['results']
        detail = self.client.get(f'/api/v1/products/{product.id}/').json()
        listed_product = next(item for item in listed if item['id'] == product.id)

        for value in (listed_product, detail):
            self.assertEqual(value['image_url'], image_data)
            self.assertEqual(value['craftswoman']['id'], craftswoman.id)
            self.assertEqual(value['craftswoman']['name'], 'Tejedora de prueba')
            self.assertEqual(value['craftswoman']['community'], 'Comunidad real')
            self.assertEqual(value['craftswoman']['region'], 'La Guajira')

    def test_craftswoman_can_read_and_update_only_personal_profile_fields(self):
        craft_user = self.create_role_user('self-profile-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        profile = Craftswoman.objects.create(
            user=craft_user, name='Nombre inicial', community='Comunidad inicial',
            region='Región inicial', phone='3000000000', biography='Biografía inicial', active=True,
        )
        foreign_user = self.create_role_user('other-profile-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        foreign_profile = Craftswoman.objects.create(
            user=foreign_user, name='Otra tejedora', community='Otra comunidad', active=True,
        )
        self.client.force_login(craft_user)

        fetched = self.client.get('/api/v1/craftswoman/profile/')
        updated = self.client.patch('/api/v1/craftswoman/profile/', {
            'name': 'Nombre actualizado', 'community': 'Comunidad Wayúu', 'region': 'La Guajira',
            'phone': '3012345678', 'biography': 'Perfil público actualizado.',
        }, content_type='application/json')

        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()['id'], profile.id)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['name'], 'Nombre actualizado')
        profile.refresh_from_db()
        foreign_profile.refresh_from_db()
        craft_user.refresh_from_db()
        self.assertEqual(profile.phone, '3012345678')
        self.assertEqual(craft_user.first_name, 'Nombre actualizado')
        self.assertEqual(foreign_profile.name, 'Otra tejedora')

    def test_craftswoman_profile_rejects_other_records_and_protected_fields(self):
        craft_user = self.create_role_user('self-profile-protection', AccessRole.Code.CRAFTSWOMAN)
        profile = Craftswoman.objects.create(user=craft_user, name='Perfil protegido', active=True)
        other_user = self.create_role_user('other-profile-protected', AccessRole.Code.CRAFTSWOMAN)
        other_profile = Craftswoman.objects.create(user=other_user, name='Perfil ajeno', active=True)
        self.client.force_login(craft_user)

        response = self.client.patch('/api/v1/craftswoman/profile/', {
            'id': other_profile.id, 'user': other_user.id, 'active': False,
            'name': 'Intento no autorizado', 'role': 'admin', 'email': 'attacker@example.com',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        profile.refresh_from_db()
        other_profile.refresh_from_db()
        self.assertEqual(profile.name, 'Perfil protegido')
        self.assertTrue(profile.active)
        self.assertEqual(other_profile.name, 'Perfil ajeno')

    def test_craftswoman_profile_validates_personal_fields_and_rejects_other_roles(self):
        craft_user = self.create_role_user('self-profile-validation', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(user=craft_user, name='Perfil válido', active=True)
        self.client.force_login(craft_user)
        blank_name = self.client.patch(
            '/api/v1/craftswoman/profile/', {'name': '   '}, content_type='application/json',
        )
        long_phone = self.client.patch(
            '/api/v1/craftswoman/profile/', {'phone': '1' * 31}, content_type='application/json',
        )
        self.assertEqual(blank_name.status_code, 400)
        self.assertEqual(long_phone.status_code, 400)

        self.client.force_login(self.user)
        customer_response = self.client.patch(
            '/api/v1/craftswoman/profile/', {'name': 'No autorizado'}, content_type='application/json',
        )
        self.assertIn(customer_response.status_code, (401, 403))

    def test_admin_product_image_upload_persists_and_appears_in_catalog_and_detail(self):
        admin = self.create_role_user('admin-product-image-upload', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            upload = SimpleUploadedFile('manta.notpng', self.make_test_image(), content_type='image/png')
            response = self.client.post('/api/v1/admin/products/', {
                'sku': 'API-IMAGE-VALID', 'name': 'Manta con imagen', 'category': self.category.id,
                'price': '45000', 'stock': '2', 'image': upload,
            })
            self.assertEqual(response.status_code, 201, response.content)
            product = Product.objects.get(sku='API-IMAGE-VALID')
            self.assertTrue(product.image.name.startswith('products/'))
            self.assertTrue(Path(media_root, product.image.name).is_file())
            self.assertEqual(Path(product.image.name).suffix, '.png')
            expected_url = f'http://testserver/media/{product.image.name}'
            self.assertEqual(response.json()['image_url'], expected_url)
            original_path = Path(media_root, product.image.name)
            replacement = SimpleUploadedFile('replacement.jpeg', self.make_test_image('JPEG'), content_type='image/jpeg')
            updated = self.client.patch(
                f'/api/v1/admin/products/{product.id}/',
                data=encode_multipart('BoUnDaRyStRiNg', {'image': replacement}), content_type=MULTIPART_CONTENT,
            )
            self.assertEqual(updated.status_code, 200, updated.content)
            product.refresh_from_db()
            self.assertEqual(Path(product.image.name).suffix, '.jpg')
            self.assertTrue(original_path.is_file())
            self.assertTrue(product.active)
            self.assertTrue(product.category.active)
            self.assertFalse(product.category.is_internal)
            self.assertIsNone(product.custom_design_id)
            listed = self.client.get('/api/v1/products/').json()['results']
            detail = self.client.get(f'/api/v1/products/{product.id}/').json()
            expected_url = f'http://testserver/media/{product.image.name}'
            self.assertEqual(updated.json()['image_url'], expected_url)
            listed_product = next((item for item in listed if item['id'] == product.id), None)
            self.assertIsNotNone(listed_product, listed)
            self.assertEqual(listed_product['image_url'], expected_url)
            self.assertEqual(detail['image_url'], expected_url)

    def test_admin_product_image_rejects_corrupt_and_unsupported_images(self):
        admin = self.create_role_user('admin-invalid-product-image', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        base = {'sku': 'API-IMAGE-INVALID', 'name': 'Imagen inválida', 'category': self.category.id, 'price': '1', 'stock': '1'}
        corrupt = self.client.post('/api/v1/admin/products/', {
            **base, 'image': SimpleUploadedFile('fake.png', b'not an image', content_type='image/png'),
        })
        self.assertEqual(corrupt.status_code, 400)
        unsupported = self.client.post('/api/v1/admin/products/', {
            **base, 'sku': 'API-IMAGE-GIF',
            'image': SimpleUploadedFile('animated.gif', self.make_test_image('GIF'), content_type='image/gif'),
        })
        self.assertEqual(unsupported.status_code, 400)
        self.assertFalse(Product.objects.filter(sku__in=('API-IMAGE-INVALID', 'API-IMAGE-GIF')).exists())

    def test_admin_product_image_rejects_oversized_file(self):
        admin = self.create_role_user('admin-large-product-image', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        response = self.client.post('/api/v1/admin/products/', {
            'sku': 'API-IMAGE-LARGE', 'name': 'Imagen grande', 'category': self.category.id,
            'price': '1', 'stock': '1',
            'image': SimpleUploadedFile('large.png', b'x' * (5 * 1024 * 1024 + 1), content_type='image/png'),
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Product.objects.filter(sku='API-IMAGE-LARGE').exists())

    def test_existing_and_empty_product_images_remain_compatible(self):
        legacy = 'https://example.test/legacy-manta.jpg'
        self.product.image_url = legacy
        self.product.save(update_fields=('image_url',))
        admin = self.create_role_user('admin-legacy-product-images', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        response = self.client.get('/api/v1/admin/products/')
        by_id = {item['id']: item for item in response.json()}
        self.assertEqual(by_id[self.product.id]['image_url'], legacy)
        self.assertFalse(self.product.image)
        no_image = Product.objects.create(
            sku='API-IMAGE-EMPTY', name='Producto sin imagen', category=self.category,
            price=Decimal('1000'), stock=1,
        )
        refreshed = {item['id']: item for item in self.client.get('/api/v1/admin/products/').json()}
        self.assertEqual(refreshed[no_image.id]['image_url'], '')
        self.assertFalse(no_image.image)

    def test_admin_category_crud_and_rbac_visibility(self):
        admin = self.create_role_user('admin-catalog-categories', AccessRole.Code.ADMIN)
        self.client.force_login(admin)

        created = self.client.post('/api/v1/admin/categories/', {
            'name': 'Accesorios', 'description': 'Categoría comercial', 'active': True, 'is_internal': True,
        }, content_type='application/json')
        category_id = created.json()['id']
        updated = self.client.patch(f'/api/v1/admin/categories/{category_id}/', {
            'name': 'Accesorios Wayúu', 'description': 'Editada',
        }, content_type='application/json')
        deactivated = self.client.patch(f'/api/v1/admin/categories/{category_id}/', {
            'active': False,
        }, content_type='application/json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['name'], 'Accesorios Wayúu')
        self.assertFalse(created.json()['is_internal'])
        self.assertFalse(deactivated.json()['active'])

        internal = Category.objects.create(name='Uso del sistema', active=True, is_internal=True)
        rejected_internal_product = self.client.post('/api/v1/admin/products/', {
            'sku': 'API-ADMIN-INTERNAL-CATEGORY', 'name': 'No comercial', 'category': internal.id,
            'price': '25000', 'stock': 1,
        }, content_type='application/json')
        self.assertEqual(rejected_internal_product.status_code, 400)

        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/v1/admin/categories/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/products/options/').status_code, 403)
        self.assertEqual(self.client.post('/api/v1/admin/categories/', {
            'name': 'No autorizada', 'description': '', 'active': True,
        }, content_type='application/json').status_code, 403)

    def test_public_catalog_search_filters_and_paginates(self):
        Product.objects.create(
            sku='API-PAGE-001', name='Manta Azul de Prueba', category=self.category,
            color='Azul', price=Decimal('30000'), stock=2, active=True,
        )
        Product.objects.create(
            sku='API-PAGE-002', name='Manta Azul de Uribia', category=self.category,
            color='Azul', price=Decimal('35000'), stock=1, active=True,
        )

        response = self.client.get(f'/api/v1/products/?search=Azul&category={self.category.id}&page_size=1')
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['count'], 3)
        self.assertEqual(len(payload['results']), 1)
        self.assertIsNotNone(payload['next'])
        self.assertEqual(payload['results'][0]['category']['id'], self.category.id)

    def test_internal_and_inactive_products_are_not_public_or_detail_accessible(self):
        internal = Category.objects.create(name='Diseños personalizados', active=True, is_internal=True)
        inactive = Category.objects.create(name='Colección archivada', active=False)
        internal_product = Product.objects.create(
            sku='API-PRIVATE-CATEGORY', name='Producto interno', category=internal,
            price=Decimal('20000'), stock=1, active=True,
        )
        inactive_category_product = Product.objects.create(
            sku='API-INACTIVE-CATEGORY', name='Producto de categoría archivada', category=inactive,
            price=Decimal('20000'), stock=1, active=True,
        )

        ids = [item['id'] for item in self.client.get('/api/v1/products/').json()['results']]
        self.assertNotIn(internal_product.id, ids)
        self.assertNotIn(inactive_category_product.id, ids)
        self.assertEqual(self.client.get(f'/api/v1/products/{internal_product.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/products/{inactive_category_product.id}/').status_code, 404)
        html_catalog = self.client.get('/')
        html_ids = [product.id for product in html_catalog.context['products']]
        self.assertIn(self.product.id, html_ids)
        self.assertNotIn(internal_product.id, html_ids)
        self.assertNotIn(inactive_category_product.id, html_ids)
        self.assertEqual(self.client.get(f'/producto/{internal_product.id}/').status_code, 404)

    def test_deactivating_category_hides_products_from_public_queries_but_not_admin(self):
        active_category = Category.objects.create(name='Categoría aún visible', active=True)
        active_product = Product.objects.create(
            sku='CATEGORY-STILL-PUBLIC', name='Manta visible', category=active_category,
            price=Decimal('25000'), stock=2, active=True,
        )
        admin = self.create_role_user('admin-category-deactivation-visibility', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        deactivated = self.client.patch(
            f'/api/v1/admin/categories/{self.category.id}/', {'active': False},
            content_type='application/json',
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.content)

        self.client.logout()
        listing = self.client.get('/api/v1/products/?search=Manta')
        category_listing = self.client.get('/api/v1/categories/')
        hidden = self.client.get(f'/api/v1/products/{self.product.id}/')
        html_listing = self.client.get('/')
        html_detail = self.client.get(f'/producto/{self.product.id}/')
        listed_ids = [product['id'] for product in listing.json()['results']]
        self.assertNotIn(self.product.id, listed_ids)
        self.assertIn(active_product.id, listed_ids)
        self.assertNotIn(self.category.id, [category['id'] for category in category_listing.json()])
        self.assertEqual(hidden.status_code, 404)
        self.assertNotIn(self.product.id, [product.id for product in html_listing.context['products']])
        self.assertIn(active_product.id, [product.id for product in html_listing.context['products']])
        self.assertEqual(html_detail.status_code, 404)

        self.client.force_login(admin)
        admin_products = self.client.get('/api/v1/admin/products/')
        self.assertEqual(admin_products.status_code, 200)
        self.assertIn(self.product.id, [product['id'] for product in admin_products.json()])

    def test_registration_creates_customer_and_starts_session(self):
        client = Client(enforce_csrf_checks=True)
        csrf_response = client.get('/api/v1/csrf/')
        csrf_token = csrf_response.cookies['csrftoken'].value
        response = client.post('/api/v1/auth/register/', {
            'name': 'Nueva Cliente',
            'username': 'nueva-cliente',
            'email': 'nueva@example.com',
            'password': 'OtraClaveSegura2026!',
            'phone': '3001234567',
        }, content_type='application/json', HTTP_X_CSRFTOKEN=csrf_token)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['role'], 'customer')
        self.assertTrue(Customer.objects.filter(email='nueva@example.com').exists())
        self.assertEqual(client.get('/api/v1/auth/me/').status_code, 200)

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:5173'])
    def test_frontend_origin_receives_cors_headers(self):
        response = self.client.options(
            '/api/v1/products/',
            HTTP_ORIGIN='http://localhost:5173',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
        )

        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:5173')

    @override_settings(
        CORS_ALLOWED_ORIGINS=['https://wayuuwaa.vercel.app'],
        CSRF_TRUSTED_ORIGINS=['https://wayuuwaa.vercel.app'],
        CSRF_COOKIE_HTTPONLY=True,
        CSRF_COOKIE_SECURE=True,
        CSRF_COOKIE_SAMESITE='None',
    )
    def test_allowed_frontend_can_obtain_json_csrf_token_and_login_cross_site(self):
        frontend_origin = 'https://wayuuwaa.vercel.app'
        client = Client(enforce_csrf_checks=True)
        csrf_response = client.get('/api/v1/csrf/', HTTP_ORIGIN=frontend_origin)
        csrf_token = csrf_response.json()['csrfToken']

        self.assertEqual(csrf_response['Access-Control-Allow-Origin'], frontend_origin)
        self.assertEqual(csrf_response['Access-Control-Allow-Credentials'], 'true')
        self.assertTrue(csrf_response.cookies['csrftoken']['httponly'])
        self.assertTrue(csrf_response.cookies['csrftoken']['secure'])
        self.assertEqual(csrf_response.cookies['csrftoken']['samesite'], 'None')

        login_response = client.post(
            '/api/v1/auth/login/',
            {'username': self.user.username, 'password': 'ClaveSegura2026!'},
            content_type='application/json',
            HTTP_ORIGIN=frontend_origin,
            HTTP_REFERER=f'{frontend_origin}/',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()['user']['role'], AccessRole.Code.CUSTOMER)

    @override_settings(CORS_ALLOWED_ORIGINS=['https://wayuuwaa.vercel.app'])
    def test_unlisted_vercel_origin_does_not_receive_credentialed_cors_access(self):
        response = self.client.options(
            '/api/v1/auth/me/',
            HTTP_ORIGIN='https://untrusted-project.vercel.app',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
        )

        self.assertNotIn('Access-Control-Allow-Origin', response)
        self.assertNotIn('Access-Control-Allow-Credentials', response)

    def test_cart_checkout_decrements_stock_and_creates_order(self):
        self.client.force_login(self.user)
        added = self.client.post('/api/v1/cart/items/', {
            'product_id': self.product.id,
            'quantity': 2,
        }, content_type='application/json')
        cart = self.client.get('/api/v1/cart/')
        checkout = self.client.post('/api/v1/checkout/', {
            'address': 'Calle 10 # 5-20',
            'city': 'Riohacha',
            'payment_method': 'nequi',
        }, content_type='application/json')

        self.assertEqual(added.status_code, 201)
        self.assertEqual(cart.json()['total'], '50000')
        self.assertEqual(checkout.status_code, 201)
        self.assertEqual(checkout.json()['total'], '50000')
        self.assertEqual(checkout.json()['status'], Order.Status.PENDING)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertEqual(self.client.get('/api/v1/cart/').json()['count'], 0)

    def test_repeated_checkout_does_not_create_duplicate_order_or_reduce_stock_twice(self):
        self.client.force_login(self.user)
        self.client.post('/api/v1/cart/items/', {'product_id': self.product.id, 'quantity': 2}, content_type='application/json')
        payload = {'address': 'Calle 10 # 5-20', 'city': 'Riohacha', 'payment_method': 'contact'}

        first = self.client.post('/api/v1/checkout/', payload, content_type='application/json')
        second = self.client.post('/api/v1/checkout/', payload, content_type='application/json')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)

    def test_checkout_rejects_stock_changed_after_cart_without_consuming_cart(self):
        self.client.force_login(self.user)
        self.client.post('/api/v1/cart/items/', {'product_id': self.product.id, 'quantity': 3}, content_type='application/json')
        Product.objects.filter(pk=self.product.pk).update(stock=2)

        response = self.client.post('/api/v1/checkout/', {
            'address': 'Calle 10 # 5-20', 'city': 'Riohacha', 'payment_method': 'contact',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.filter(customer=self.customer).exists())
        self.assertEqual(CustomerCartItem.objects.get(customer=self.customer, product=self.product).quantity, 3)
        self.assertEqual(Product.objects.get(pk=self.product.pk).stock, 2)

    def test_cart_session_migrates_once_and_merges_with_persistent_quantity(self):
        CustomerCartItem.objects.create(customer=self.customer, product=self.product, quantity=1)
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.product.id): 2}
        session.save()

        first = self.client.get('/api/v1/cart/')
        second = self.client.get('/api/v1/cart/')

        self.assertEqual(first.json()['count'], 3)
        self.assertEqual(second.json()['count'], 3)
        self.assertEqual(CustomerCartItem.objects.get(customer=self.customer, product=self.product).quantity, 3)
        self.assertNotIn('cart', self.client.session)

    def test_unmigratable_legacy_session_items_are_preserved(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {'invalid-id': 'broken', '99999999': 1}
        session.save()

        response = self.client.get('/api/v1/cart/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session['cart'], {'invalid-id': 'broken', '99999999': 1})
        self.assertEqual(response.json()['count'], 0)
        self.assertEqual(
            response.json()['legacy_items'],
            [
                {'key': 'invalid-id', 'label': 'Elemento anterior 1'},
                {'key': '99999999', 'label': 'Producto anterior #99999999'},
            ],
        )

        removed = self.client.post(
            '/api/v1/cart/legacy-items/remove/', {'key': 'invalid-id'},
            content_type='application/json',
        )
        refreshed = self.client.get('/api/v1/cart/')
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(self.client.session['cart'], {'99999999': 1})
        self.assertEqual(refreshed.json()['legacy_items'], [
            {'key': '99999999', 'label': 'Producto anterior #99999999'},
        ])
        self.assertFalse(CustomerCartItem.objects.filter(customer=self.customer).exists())

    def test_discarding_legacy_entry_keeps_valid_persistent_cart_item_unchanged(self):
        CustomerCartItem.objects.create(customer=self.customer, product=self.product, quantity=2)
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {'invalid-id': 'broken'}
        session.save()

        before = self.client.get('/api/v1/cart/')
        removed = self.client.post(
            '/api/v1/cart/legacy-items/remove/', {'key': 'invalid-id'},
            content_type='application/json',
        )
        after = self.client.get('/api/v1/cart/')

        self.assertEqual(before.json()['count'], 2)
        self.assertEqual(len(before.json()['items']), 1)
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(after.json()['count'], 2)
        self.assertEqual(len(after.json()['items']), 1)
        self.assertEqual(after.json()['legacy_items'], [])
        self.assertEqual(
            CustomerCartItem.objects.get(customer=self.customer, product=self.product).quantity,
            2,
        )

    def test_empty_cart_can_clear_last_unrecoverable_legacy_entry(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {'99999999': 1}
        session.save()

        before = self.client.get('/api/v1/cart/')
        removed = self.client.post(
            '/api/v1/cart/legacy-items/remove/', {'key': '99999999'},
            content_type='application/json',
        )
        after = self.client.get('/api/v1/cart/')

        self.assertEqual(before.json()['items'], [])
        self.assertEqual(before.json()['count'], 0)
        self.assertEqual(len(before.json()['legacy_items']), 1)
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(after.json()['items'], [])
        self.assertEqual(after.json()['count'], 0)
        self.assertEqual(after.json()['legacy_items'], [])
        self.assertNotIn('cart', self.client.session)

    def test_removal_rechecks_and_recovers_a_now_valid_legacy_product(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.product.id): 2}
        session.save()

        response = self.client.post(
            '/api/v1/cart/legacy-items/remove/', {'key': str(self.product.id)},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['recovered'])
        self.assertTrue(CustomerCartItem.objects.filter(
            customer=self.customer, product=self.product, quantity=2,
        ).exists())
        self.assertNotIn('cart', self.client.session)

    def test_favorites_reject_inactive_and_missing_products(self):
        self.client.force_login(self.user)
        inactive = Product.objects.create(
            sku='API-FAVORITE-INACTIVE', name='Inactivo', category=self.category,
            price=Decimal('10000'), stock=1, active=False,
        )

        inactive_response = self.client.post('/api/v1/favorites/', {'product_id': inactive.id}, content_type='application/json')
        missing_response = self.client.post('/api/v1/favorites/', {'product_id': 99999999}, content_type='application/json')

        self.assertEqual(inactive_response.status_code, 404)
        self.assertEqual(missing_response.status_code, 404)
        self.assertFalse(CustomerFavorite.objects.filter(customer=self.customer).exists())

    def test_favorites_persist_and_are_isolated_by_customer(self):
        other_user = User.objects.create_user(username='otro-favoritos', password='ClaveSegura2026!')
        other_customer = Customer.objects.create(user=other_user, name='Otro', email='otro-favoritos@example.com')
        self.assign_role(other_user, AccessRole.Code.CUSTOMER)
        self.client.force_login(self.user)

        saved = self.client.post('/api/v1/favorites/', {'product_id': self.product.id}, content_type='application/json')
        duplicate = self.client.post('/api/v1/favorites/', {'product_id': self.product.id}, content_type='application/json')
        self.assertEqual(saved.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(self.client.get('/api/v1/favorites/').json()['product_ids'], [self.product.id])
        self.assertEqual(CustomerFavorite.objects.filter(customer=self.customer).count(), 1)

        self.client.force_login(other_user)
        self.assertEqual(self.client.get('/api/v1/favorites/').json()['product_ids'], [])
        self.client.delete(f'/api/v1/favorites/{self.product.id}/')
        self.assertTrue(CustomerFavorite.objects.filter(customer=self.customer, product=self.product).exists())

    def test_customer_cannot_multiply_own_inactive_custom_design_cart_item_and_can_remove_it(self):
        design = CustomDesign.objects.create(
            customer=self.customer,
            pattern='rombos',
            base_color='#112233',
            accent_color_one='#445566',
            accent_color_two='#778899',
            size='M',
            quantity=2,
            estimated_price=Decimal('240000'),
        )
        custom_product = Product.objects.create(
            sku='CUSTOM-CART-API-001',
            name='Manta personalizada de prueba',
            category=self.category,
            custom_design=design,
            price=Decimal('120000'),
            stock=2,
            active=False,
            made_to_order=True,
        )
        CustomerCartItem.objects.create(customer=self.customer, product=custom_product, quantity=1)
        self.client.force_login(self.user)

        updated = self.client.patch(
            f'/api/v1/cart/items/{custom_product.id}/',
            {'quantity': 2},
            content_type='application/json',
        )
        self.assertEqual(updated.status_code, 400)
        self.assertIn('cantidad del diseño personalizado', updated.json()['detail'])
        self.assertEqual(
            CustomerCartItem.objects.get(customer=self.customer, product=custom_product).quantity,
            1,
        )

        removed = self.client.delete(f'/api/v1/cart/items/{custom_product.id}/')
        self.assertEqual(removed.status_code, 204)
        self.assertFalse(CustomerCartItem.objects.filter(customer=self.customer, product=custom_product).exists())

    def test_custom_design_products_never_appear_in_public_catalog_or_other_customers_cart(self):
        other_user = User.objects.create_user(
            username='cliente-diseno-privado',
            email='cliente-diseno-privado@example.com',
            password='ClaveSegura2026!',
        )
        other_customer = Customer.objects.create(
            user=other_user,
            name='Cliente diseño privado',
            email='cliente-diseno-privado@example.com',
        )
        design = CustomDesign.objects.create(
            customer=other_customer,
            pattern='rombos',
            base_color='#112233',
            accent_color_one='#445566',
            accent_color_two='#778899',
            size='M',
            estimated_price=Decimal('120000'),
        )
        private_product = Product.objects.create(
            sku='CUSTOM-PRIVATE-CATALOG-001',
            name='Diseño que debe ser privado',
            category=self.category,
            custom_design=design,
            price=Decimal('120000'),
            stock=1,
            active=True,
            made_to_order=True,
        )

        self.assertNotIn(
            private_product.id,
            [item['id'] for item in self.client.get('/api/v1/products/').json()['results']],
        )
        self.assertEqual(self.client.get(f'/api/v1/products/{private_product.id}/').status_code, 404)

        self.client.force_login(self.user)
        add_attempt = self.client.post('/api/v1/cart/items/', {
            'product_id': private_product.id,
            'quantity': 1,
        }, content_type='application/json')
        self.assertEqual(add_attempt.status_code, 404)
        self.assertEqual(self.client.get('/api/v1/cart/').json()['count'], 0)

    def test_customer_cannot_update_another_customers_inactive_product(self):
        other_user = User.objects.create_user(
            username='otro-cliente-diseno',
            email='otro-cliente-diseno@example.com',
            password='ClaveSegura2026!',
        )
        other_customer = Customer.objects.create(
            user=other_user,
            name='Otro cliente',
            email='otro-cliente-diseno@example.com',
        )
        design = CustomDesign.objects.create(
            customer=other_customer,
            pattern='rombos',
            base_color='#112233',
            accent_color_one='#445566',
            accent_color_two='#778899',
            size='M',
            estimated_price=Decimal('120000'),
        )
        custom_product = Product.objects.create(
            sku='CUSTOM-CART-API-002',
            name='Diseño privado de otro cliente',
            category=self.category,
            custom_design=design,
            price=Decimal('120000'),
            stock=1,
            active=False,
            made_to_order=True,
        )
        self.client.force_login(self.user)
        response = self.client.patch(
            f'/api/v1/cart/items/{custom_product.id}/',
            {'quantity': 1},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_customer_cart_persists_after_logout_and_new_login(self):
        self.client.force_login(self.user)
        added = self.client.post('/api/v1/cart/items/', {
            'product_id': self.product.id,
            'quantity': 2,
        }, content_type='application/json')
        self.assertEqual(added.status_code, 201)
        self.assertEqual(CustomerCartItem.objects.get(customer=self.customer, product=self.product).quantity, 2)

        self.client.post('/api/v1/auth/logout/')
        self.client.force_login(self.user)
        restored = self.client.get('/api/v1/cart/')

        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()['count'], 2)
        self.assertEqual(restored.json()['items'][0]['product']['id'], self.product.id)

    def test_html_checkout_uses_authenticated_customer_profile(self):
        self.client.force_login(self.user)

        added = self.client.post(
            f'/carrito/agregar/{self.product.id}/',
            {'quantity': 2},
        )
        self.assertEqual(added.status_code, 302)

        checkout = self.client.post('/finalizar-pedido/', {
            'name': 'Cliente API Actualizado',
            'email': 'correo-alternativo@example.com',
            'phone': '3009876543',
            'address': 'Calle 10 # 5-20',
            'city': 'Riohacha',
            'payment_method': 'nequi',
        })

        self.assertEqual(checkout.status_code, 302)
        self.assertTrue(checkout.url.startswith('/pedido-confirmado/'))

        order = Order.objects.get(customer=self.customer)
        self.assertEqual(order.shipping_address, 'Calle 10 # 5-20, Riohacha')

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, 'Cliente API Actualizado')
        self.assertEqual(self.customer.email, 'cliente-api@example.com')
        self.assertEqual(self.customer.phone, '3009876543')
        self.assertEqual(self.customer.city, 'Riohacha')

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)

    def test_customer_cannot_read_another_customers_order(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/orders/999999/')

        self.assertEqual(response.status_code, 404)

    def test_customer_and_craftswoman_cannot_access_other_users_orders_or_designs(self):
        other_customer_user = self.create_role_user('other-customer', AccessRole.Code.CUSTOMER)
        other_customer = Customer.objects.create(
            user=other_customer_user,
            name='Otro cliente',
            email='other-customer@example.com',
        )
        own_order = Order.objects.create(customer=self.customer, shipping_address='Dirección propia')
        foreign_order = Order.objects.create(customer=other_customer, shipping_address='Dirección ajena')
        foreign_design = CustomDesign.objects.create(
            customer=other_customer,
            pattern='olas',
            base_color='#112233',
            accent_color_one='#223344',
            accent_color_two='#334455',
            size='M',
            quantity=1,
            estimated_price=Decimal('120000'),
        )

        self.client.force_login(self.user)
        customer_orders = self.client.get('/api/v1/orders/').json()['results']
        customer_designs = self.client.get('/api/v1/designs/').json()
        self.assertEqual([order['id'] for order in customer_orders], [own_order.id])
        self.assertEqual(customer_orders[0]['customer_id'], self.customer.id)
        self.assertEqual(customer_orders[0]['customer_name'], self.customer.name)
        self.assertEqual(customer_designs, [])
        self.assertEqual(self.client.get(f'/api/v1/orders/{foreign_order.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/pedido-confirmado/{foreign_order.id}/').status_code, 404)

        own_craft_user = self.create_role_user('own-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        own_craft = Craftswoman.objects.create(user=own_craft_user, name='Tejedora propia', active=True)
        foreign_craft_user = self.create_role_user('foreign-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        foreign_craft = Craftswoman.objects.create(user=foreign_craft_user, name='Tejedora ajena', active=True)
        assigned_order = Order.objects.create(
            customer=self.customer,
            craftswoman=own_craft,
            status=Order.Status.ACCEPTED,
            shipping_address='Pedido propio del taller',
        )
        foreign_assigned_order = Order.objects.create(
            customer=self.customer,
            craftswoman=foreign_craft,
            status=Order.Status.ACCEPTED,
            shipping_address='Pedido de otro taller',
        )
        foreign_design.craftswoman = foreign_craft
        foreign_design.status = Order.Status.ACCEPTED
        foreign_design.save(update_fields=('craftswoman', 'status'))

        self.client.force_login(own_craft_user)
        craft_orders = self.client.get('/api/v1/orders/').json()['results']
        self.assertEqual([order['id'] for order in craft_orders], [assigned_order.id])
        self.assertEqual(self.client.get(f'/api/v1/orders/{foreign_assigned_order.id}/').status_code, 404)
        self.assertEqual(
            self.client.patch(
                f'/api/v1/craftswoman/orders/{foreign_assigned_order.id}/status/',
                {'status': Order.Status.WEAVING},
                content_type='application/json',
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(
                f'/api/v1/craftswoman/designs/{foreign_design.id}/status/',
                {'status': Order.Status.WEAVING},
                content_type='application/json',
            ).status_code,
            404,
        )
        # Los querysets limitados al propietario ocultan la existencia de pedidos ajenos con 404.
        self.assertEqual(self.client.get(f'/pedido-confirmado/{foreign_assigned_order.id}/').status_code, 404)
        order_status = self.client.patch(
            f'/api/v1/craftswoman/orders/{foreign_assigned_order.id}/status/',
            {'status': Order.Status.WEAVING},
            content_type='application/json',
        )
        self.assertEqual(order_status.status_code, 404)
        foreign_assigned_order.refresh_from_db()
        self.assertEqual(foreign_assigned_order.status, Order.Status.ACCEPTED)
        self.assertEqual(foreign_assigned_order.craftswoman_id, foreign_craft.id)
        foreign_design.refresh_from_db()
        self.assertEqual(foreign_design.status, Order.Status.ACCEPTED)
        self.assertEqual(foreign_design.craftswoman_id, foreign_craft.id)

    def test_customer_can_read_and_update_profile(self):
        self.client.force_login(self.user)
        updated = self.client.patch('/api/v1/profile/', {
            'name': 'Cliente Actualizado',
            'email': 'otro-cliente@example.com',
            'phone': '3009876543',
            'address': 'Calle 12 # 4-10',
            'city': 'Maicao',
        }, content_type='application/json')

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['name'], 'Cliente Actualizado')
        self.assertEqual(updated.json()['email'], self.customer.email)
        self.assertEqual(updated.json()['city'], 'Maicao')
        self.customer.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.customer.address, 'Calle 12 # 4-10')
        self.assertEqual(self.user.first_name, 'Cliente Actualizado')

    def test_customer_can_create_and_list_custom_designs(self):
        self.client.force_login(self.user)
        created = self.client.post('/api/v1/designs/', {
            'pattern': 'rombos',
            'base_color': '#b77f86',
            'accent_color_one': '#d4b9a2',
            'accent_color_two': '#87978c',
            'size': 'L',
            'quantity': 2,
            'notes': 'Acento en el borde',
        }, content_type='application/json')
        designs = self.client.get('/api/v1/designs/')

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['estimated_price'], '290000')
        self.assertEqual(designs.status_code, 200)
        self.assertEqual(len(designs.json()), 1)
        self.assertEqual(designs.json()[0]['accent_color_two'], '#87978c')
        self.assertEqual(designs.json()[0]['status_label'], 'Pendiente')
        self.assertTrue(Category.objects.get(name='Diseños personalizados').is_internal)
        created_design = CustomDesign.objects.get(customer=self.customer)
        self.assertTrue(CustomerCartItem.objects.filter(
            customer=self.customer,
            product__custom_design=created_design,
            quantity=1,
        ).exists())
        self.assertNotIn(
            'Diseños personalizados',
            [item['name'] for item in self.client.get('/api/v1/categories/').json()],
        )

    def test_html_designer_validates_options_and_persists_design_with_cart_atomically(self):
        self.client.force_login(self.user)
        invalid = self.client.post('/disena-tu-manta/', {
            'pattern': 'inventado', 'base_color': 'rojo', 'accent_color_one': '#112233',
            'accent_color_two': '#223344', 'size': 'M', 'quantity': 1,
        })
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(CustomDesign.objects.count(), 0)

        created = self.client.post('/disena-tu-manta/', {
            'pattern': 'rombos', 'base_color': '#112233', 'accent_color_one': '#223344',
            'accent_color_two': '#334455', 'size': 'L', 'quantity': 2,
            'notes': 'Borde oscuro',
        })
        self.assertEqual(created.status_code, 302)
        design = CustomDesign.objects.get(customer=self.customer)
        self.assertEqual(design.estimated_price, Decimal('290000'))
        self.assertTrue(CustomerCartItem.objects.filter(
            customer=self.customer, product__custom_design=design, quantity=1,
        ).exists())

    def test_custom_design_survives_cart_checkout_assignment_weaving_and_delivery(self):
        self.client.force_login(self.user)
        created = self.client.post('/api/v1/designs/', {
            'pattern': 'caminos', 'base_color': '#112233', 'accent_color_one': '#223344',
            'accent_color_two': '#334455', 'size': 'L', 'quantity': 2,
            'notes': 'Conservar colores del diseño',
        }, content_type='application/json')
        self.assertEqual(created.status_code, 201)
        design_id = created.json()['id']
        product_id = created.json()['product_id']
        cart = self.client.get('/api/v1/cart/')
        self.assertEqual(cart.status_code, 200)
        self.assertEqual(cart.json()['count'], 1)

        checkout = self.client.post('/api/v1/checkout/', {
            'address': 'Calle del tejido 10', 'city': 'Uribia', 'payment_method': 'contact',
        }, content_type='application/json')
        self.assertEqual(checkout.status_code, 201)
        order_id = checkout.json()['id']
        order_item = OrderItem.objects.get(order_id=order_id)
        self.assertEqual(order_item.product_id, product_id)
        self.assertEqual(order_item.product.custom_design_id, design_id)
        design = CustomDesign.objects.get(pk=design_id)
        self.assertEqual(design.customer_id, self.customer.id)
        self.assertEqual(design.quantity, 2)
        self.assertEqual(design.notes, 'Conservar colores del diseño')
        self.assertEqual(Product.objects.get(pk=product_id).stock, 0)

        craft_user = self.create_role_user('full-flow-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora de flujo', active=True)
        self.client.force_login(craft_user)
        accepted = self.client.post(f'/api/v1/craftswoman/orders/{order_id}/accept/')
        self.assertEqual(accepted.status_code, 200)
        design.refresh_from_db()
        self.assertEqual(design.craftswoman_id, craftswoman.id)
        self.assertEqual(design.status, Order.Status.ACCEPTED)

        weaving = self.client.patch(
            f'/api/v1/craftswoman/orders/{order_id}/status/',
            {'status': Order.Status.WEAVING}, content_type='application/json',
        )
        completed = self.client.patch(
            f'/api/v1/craftswoman/orders/{order_id}/status/',
            {'status': Order.Status.COMPLETED}, content_type='application/json',
        )
        self.assertEqual(weaving.status_code, 200)
        self.assertEqual(completed.status_code, 200)
        design.refresh_from_db()
        self.assertEqual(design.status, Order.Status.COMPLETED)

        admin = self.create_role_user('full-flow-admin', AccessRole.Code.ADMIN)
        superadmin = self.create_role_user('full-flow-superadmin', AccessRole.Code.SUPERADMIN)
        set_role_permission(
            superadmin, AccessRole.Code.ADMIN, 'designs', 'change', allowed=True,
        )
        self.client.force_login(admin)
        for next_status in (
            Order.Status.PAID, Order.Status.PREPARING, Order.Status.SHIPPED, Order.Status.DELIVERED,
        ):
            response = self.client.patch(
                f'/api/v1/admin/orders/{order_id}/status/',
                {'status': next_status}, content_type='application/json',
            )
            self.assertEqual(response.status_code, 200, response.content)
        order = Order.objects.get(pk=order_id)
        design.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertEqual(design.status, Order.Status.DELIVERED)
        self.assertEqual(order.items.get().product.custom_design_id, design.id)

    def test_craftswoman_can_accept_order_without_design_change_permission(self):
        craft_user = self.create_role_user(
            'tejedora-order-without-design-change',
            AccessRole.Code.CRAFTSWOMAN,
        )
        craftswoman = Craftswoman.objects.create(
            user=craft_user,
            name='Tejedora Pedido Normal',
            active=True,
        )
        role = AccessRole.objects.get(code=AccessRole.Code.CRAFTSWOMAN)
        orders_permission = permission_for('orders', 'change')
        designs_permission = permission_for('designs', 'change')
        RolePermission.objects.get_or_create(role=role, permission=orders_permission)
        RolePermission.objects.filter(role=role, permission=designs_permission).delete()

        order = Order.objects.create(
            customer=self.customer,
            shipping_address='Maicao, La Guajira',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
        )
        self.client.force_login(craft_user)

        response = self.client.post(f'/api/v1/craftswoman/orders/{order.id}/accept/')

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.craftswoman_id, craftswoman.id)
        self.assertEqual(order.status, Order.Status.ACCEPTED)

        assignment_event = AuditEvent.objects.get(action='accept_order', object_id=str(order.id))
        self.assertEqual(assignment_event.actor, craft_user)
        self.assertEqual(assignment_event.details['craftswoman_id'], craftswoman.id)

        status_response = self.client.patch(
            f'/api/v1/craftswoman/orders/{order.id}/status/',
            {'status': Order.Status.WEAVING},
            content_type='application/json',
        )
        self.assertEqual(status_response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.WEAVING)
        status_event = AuditEvent.objects.get(
            action='craftswoman_change_order_status', object_id=str(order.id),
        )
        self.assertEqual(status_event.actor, craft_user)
        self.assertEqual(status_event.details, {
            'from': Order.Status.ACCEPTED,
            'to': Order.Status.WEAVING,
        })

    def test_craftswoman_order_status_requires_design_permission_only_for_custom_designs(self):
        craft_user = self.create_role_user('normal-and-custom-order-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora Pedidos', active=True)
        role = AccessRole.objects.get(code=AccessRole.Code.CRAFTSWOMAN)
        RolePermission.objects.get_or_create(role=role, permission=permission_for('orders', 'change'))
        RolePermission.objects.filter(role=role, permission=permission_for('designs', 'change')).delete()

        normal_order = Order.objects.create(
            customer=self.customer, craftswoman=craftswoman,
            status=Order.Status.ACCEPTED, shipping_address='Riohacha',
        )
        OrderItem.objects.create(
            order=normal_order, product=self.product, quantity=1, unit_price=self.product.price,
        )
        design = CustomDesign.objects.create(
            customer=self.customer,
            pattern='rombos',
            base_color='#112233',
            accent_color_one='#223344',
            accent_color_two='#334455',
            size='M',
            quantity=1,
            estimated_price=Decimal('120000'),
            status=Order.Status.ACCEPTED,
            craftswoman=craftswoman,
        )
        design_product = Product.objects.create(
            sku='CUSTOM-ORDER-STATUS-001',
            name='Manta personalizada privada',
            category=self.category,
            custom_design=design,
            price=design.estimated_price,
            stock=1,
            made_to_order=True,
            active=False,
        )
        custom_order = Order.objects.create(
            customer=self.customer, craftswoman=craftswoman,
            status=Order.Status.ACCEPTED, shipping_address='Maicao',
        )
        OrderItem.objects.create(
            order=custom_order, product=design_product, quantity=1, unit_price=design_product.price,
        )
        html_normal_order = Order.objects.create(
            customer=self.customer, craftswoman=craftswoman,
            status=Order.Status.ACCEPTED, shipping_address='Fonseca',
        )
        OrderItem.objects.create(
            order=html_normal_order, product=self.product, quantity=1, unit_price=self.product.price,
        )

        self.client.force_login(craft_user)
        craft_dashboard = self.client.get('/api/v1/craftswoman/dashboard/')
        dashboard_orders = {item['id']: item for item in craft_dashboard.json()['orders']}
        dashboard_designs = {item['id']: item for item in craft_dashboard.json()['designs']}
        self.assertEqual(dashboard_orders[normal_order.id]['allowed_statuses'], [Order.Status.WEAVING])
        self.assertEqual(dashboard_orders[custom_order.id]['allowed_statuses'], [])
        self.assertEqual(dashboard_designs[design.id]['allowed_statuses'], [])
        normal_response = self.client.patch(
            f'/api/v1/craftswoman/orders/{normal_order.id}/status/',
            {'status': Order.Status.WEAVING},
            content_type='application/json',
        )
        custom_response = self.client.patch(
            f'/api/v1/craftswoman/orders/{custom_order.id}/status/',
            {'status': Order.Status.WEAVING},
            content_type='application/json',
        )
        custom_html_response = self.client.post(
            f'/panel-tejedora/pedido/{custom_order.id}/estado/',
            {'status': Order.Status.WEAVING},
        )
        normal_html_response = self.client.post(
            f'/panel-tejedora/pedido/{html_normal_order.id}/estado/',
            {'status': Order.Status.WEAVING},
        )

        self.assertEqual(normal_response.status_code, 200)
        self.assertEqual(custom_response.status_code, 403)
        self.assertEqual(custom_html_response.status_code, 403)
        self.assertEqual(normal_html_response.status_code, 302)
        html_normal_order.refresh_from_db()
        self.assertEqual(html_normal_order.status, Order.Status.WEAVING)
        custom_order.refresh_from_db()
        design.refresh_from_db()
        self.assertEqual(custom_order.status, Order.Status.ACCEPTED)
        self.assertEqual(design.status, Order.Status.ACCEPTED)

    def test_craftswoman_can_accept_orders_and_update_design_status(self):
        craft_user = User.objects.create_user(
            username='tejedora-api',
            email='tejedora-api@example.com',
            password='ClaveSegura2026!',
        )
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora API', active=True)
        self.assign_role(craft_user, AccessRole.Code.CRAFTSWOMAN)
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao, La Guajira')
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
        design = CustomDesign.objects.create(
            customer=self.customer,
            pattern='olas',
            base_color='#b77f86',
            accent_color_one='#d4b9a2',
            accent_color_two='#87978c',
            size='M',
            quantity=1,
            estimated_price=Decimal('120000'),
            status=Order.Status.ACCEPTED,
            craftswoman=craftswoman,
        )
        self.client.force_login(craft_user)

        dashboard = self.client.get('/api/v1/craftswoman/dashboard/')
        accepted = self.client.post(f'/api/v1/craftswoman/orders/{order.id}/accept/')
        updated_design = self.client.patch(
            f'/api/v1/craftswoman/designs/{design.id}/status/',
            {'status': Order.Status.WEAVING},
            content_type='application/json',
        )

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()['designs'][0]['craftswoman_name'], 'Tejedora API')
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()['status'], Order.Status.ACCEPTED)
        self.assertEqual(updated_design.status_code, 200)
        self.assertEqual(updated_design.json()['status'], Order.Status.WEAVING)

    def test_craftswoman_can_submit_own_product_for_admin_review(self):
        craft_user = self.create_role_user('tejedora-products-api', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora Productos', active=True)
        self.client.force_login(craft_user)

        created = self.client.post('/api/v1/craftswoman/products/', {
            'sku': 'CRAFT-OWN-001',
            'name': 'Manta de mi taller',
            'category': self.category.id,
            'description': 'Tejido tradicional.',
            'region': 'La Guajira',
            'color': 'Borgoña y crema',
            'size': 'M',
            'production_time': '20 días',
            'image_url': 'https://example.com/manta-wayuu.jpg',
            'price': '280000',
            'stock': 2,
        }, content_type='application/json')

        self.assertEqual(created.status_code, 201)
        self.assertFalse(created.json()['active'])
        product = Product.objects.get(sku='CRAFT-OWN-001')
        self.assertEqual(product.craftswoman_id, craftswoman.id)
        self.assertEqual(
            self.client.get('/api/v1/craftswoman/products/').json()[0]['id'],
            product.id,
        )

    def test_craftswoman_product_api_rejects_manipulated_ownership_on_create_and_edit(self):
        own_user = self.create_role_user('craft-owner-tamper', AccessRole.Code.CRAFTSWOMAN)
        own_profile = Craftswoman.objects.create(user=own_user, name='Tejedora propia', active=True)
        other_user = self.create_role_user('craft-other-tamper', AccessRole.Code.CRAFTSWOMAN)
        other_profile = Craftswoman.objects.create(user=other_user, name='Tejedora ajena', active=True)
        own_product = Product.objects.create(
            sku='CRAFT-OWNERSHIP-TAMPER', name='Pieza propia', category=self.category,
            craftswoman=own_profile, price=Decimal('30000'), stock=2,
        )
        self.client.force_login(own_user)

        created = self.client.post('/api/v1/craftswoman/products/', {
            'sku': 'CRAFT-OWNERSHIP-INJECT', 'name': 'Pieza manipulada', 'category': self.category.id,
            'description': 'Descripción suficiente para validar.', 'region': 'La Guajira',
            'color': 'Rojo', 'size': 'M', 'production_time': '20 días',
            'image_url': 'https://example.test/manta.jpg', 'price': '30000', 'stock': 1,
            'craftswoman': other_profile.id,
        }, content_type='application/json')
        edited = self.client.patch(
            f'/api/v1/craftswoman/products/{own_product.id}/',
            {'craftswoman': other_profile.id}, content_type='application/json',
        )

        self.assertEqual(created.status_code, 400)
        self.assertIn('craftswoman', created.json())
        self.assertEqual(edited.status_code, 400)
        own_product.refresh_from_db()
        self.assertEqual(own_product.craftswoman_id, own_profile.id)
        self.assertFalse(Product.objects.filter(sku='CRAFT-OWNERSHIP-INJECT').exists())

    def test_craftswoman_products_and_edits_are_limited_to_her_real_profile(self):
        own_user = self.create_role_user('craft-inventory-owner', AccessRole.Code.CRAFTSWOMAN)
        own_profile = Craftswoman.objects.create(user=own_user, name='Tejedora propia', active=True)
        foreign_user = self.create_role_user('craft-inventory-foreign', AccessRole.Code.CRAFTSWOMAN)
        foreign_profile = Craftswoman.objects.create(user=foreign_user, name='Tejedora ajena', active=True)
        own_product = Product.objects.create(
            sku='CRAFT-INV-OWN', name='Pieza propia', category=self.category,
            craftswoman=own_profile, price=Decimal('30000'), stock=3,
        )
        foreign_product = Product.objects.create(
            sku='CRAFT-INV-FOREIGN', name='Pieza ajena', category=self.category,
            craftswoman=foreign_profile, price=Decimal('40000'), stock=4,
        )
        self.client.force_login(own_user)

        response = self.client.get('/api/v1/craftswoman/products/')
        foreign_edit = self.client.patch(
            f'/api/v1/craftswoman/products/{foreign_product.id}/',
            {'stock': 0}, content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()], [own_product.id])
        self.assertEqual(foreign_edit.status_code, 404)
        foreign_product.refresh_from_db()
        self.assertEqual(foreign_product.stock, 4)

    def test_administrator_cannot_set_negative_product_stock(self):
        admin = self.create_role_user('admin-negative-inventory', AccessRole.Code.ADMIN)
        self.client.force_login(admin)

        response = self.client.patch(
            f'/api/v1/admin/products/{self.product.id}/',
            {'stock': -1}, content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)

    def test_admin_can_fully_update_product_and_assign_real_craftswoman(self):
        admin = self.create_role_user('admin-full-product-edit', AccessRole.Code.ADMIN)
        craft_user = self.create_role_user('admin-full-product-edit-craft', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Artesana registrada', active=True)
        self.product.image_url = 'https://images.example.test/manta-original.jpg'
        self.product.save(update_fields=('image_url',))
        self.client.force_login(admin)

        updated = self.client.patch(f'/api/v1/admin/products/{self.product.id}/', {
            'name': 'Manta editada', 'description': 'Descripción completa actualizada.',
            'price': '55000', 'category': self.category.id, 'size': 'L', 'color': 'Rojo y crema',
            'region': 'La Guajira', 'production_time': '30 días', 'stock': 6,
            'made_to_order': True, 'craftswoman': craftswoman.id,
        }, content_type='application/json')

        self.assertEqual(updated.status_code, 200, updated.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Manta editada')
        self.assertEqual(self.product.description, 'Descripción completa actualizada.')
        self.assertEqual(self.product.size, 'L')
        self.assertEqual(self.product.color, 'Rojo y crema')
        self.assertEqual(self.product.craftswoman_id, craftswoman.id)
        self.assertTrue(self.product.made_to_order)
        self.assertEqual(self.product.image_url, 'https://images.example.test/manta-original.jpg')

    def test_admin_inventory_report_aggregates_full_stock_and_filters_products(self):
        admin = self.create_role_user('admin-inventory-report', AccessRole.Code.ADMIN)
        low = Product.objects.create(
            sku='REPORT-INVENTORY-LOW', name='Manta stock bajo', category=self.category,
            price=Decimal('10000'), stock=3,
        )
        out = Product.objects.create(
            sku='REPORT-INVENTORY-OUT', name='Manta agotada', category=self.category,
            price=Decimal('10000'), stock=0,
        )
        Product.objects.create(
            sku='REPORT-INVENTORY-HEALTHY', name='Manta disponible', category=self.category,
            price=Decimal('10000'), stock=10,
        )
        self.client.force_login(admin)

        report = self.client.get('/api/v1/admin/inventory/report/?threshold=4')
        low_filter = self.client.get('/api/v1/admin/inventory/report/?threshold=4&status=low&search=LOW')
        out_filter = self.client.get('/api/v1/admin/inventory/report/?threshold=4&status=out')
        missing_threshold = self.client.get('/api/v1/admin/inventory/report/')
        invalid_status = self.client.get('/api/v1/admin/inventory/report/?threshold=4&status=unknown')
        export_without_permission = self.client.get('/api/v1/admin/inventory/report/?threshold=4&export=xlsx')
        self.assertEqual(export_without_permission.status_code, 403)
        root = self.create_role_user('inventory-export-root', AccessRole.Code.SUPERADMIN)
        set_role_permission(root, admin.access_profile.role.code, 'products', 'export', allowed=True)
        xlsx = self.client.get('/api/v1/admin/inventory/report/?threshold=4&status=low&search=LOW&export=xlsx')
        pdf = self.client.get('/api/v1/admin/inventory/report/?threshold=4&status=low&search=LOW&export=pdf')

        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()['summary'], {
            'product_count': 4, 'total_units': 17, 'out_of_stock_count': 1, 'low_stock_count': 2,
        })
        self.assertEqual(report.json()['products']['count'], 4)
        self.assertEqual([item['id'] for item in low_filter.json()['products']['results']], [low.id])
        self.assertEqual([item['id'] for item in out_filter.json()['products']['results']], [out.id])
        self.assertEqual(missing_threshold.status_code, 400)
        self.assertEqual(invalid_status.status_code, 400)
        self.assertEqual(xlsx.status_code, 200)
        self.assertIn('spreadsheetml.sheet', xlsx['Content-Type'])
        with ZipFile(BytesIO(xlsx.content)) as workbook:
            worksheet = workbook.read('xl/worksheets/sheet1.xml')
        self.assertIn(b'REPORT-INVENTORY-LOW', worksheet)
        self.assertNotIn(b'REPORT-INVENTORY-OUT', worksheet)
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.content[:8], b'%PDF-1.4')
        self.assertIn(b'REPORT-INVENTORY-LOW', pdf.content)
        self.assertNotIn(b'REPORT-INVENTORY-OUT', pdf.content)

        customer = self.create_role_user('inventory-report-unauthorized', AccessRole.Code.CUSTOMER)
        self.client.force_login(customer)
        self.assertEqual(self.client.get('/api/v1/admin/inventory/report/?threshold=4&export=xlsx').status_code, 403)

    def test_inventory_report_records_admin_adjustments_and_checkout_movements(self):
        admin = self.create_role_user('admin-inventory-movements', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        adjusted = self.client.patch(
            f'/api/v1/admin/products/{self.product.id}/', {'stock': 2}, content_type='application/json',
        )
        self.assertEqual(adjusted.status_code, 200)

        checkout_product = Product.objects.create(
            sku='REPORT-CHECKOUT-MOVEMENT', name='Pieza comprada', category=self.category,
            price=Decimal('20000'), stock=3, active=True,
        )
        self.client.force_login(self.user)
        added = self.client.post('/api/v1/cart/items/', {
            'product_id': checkout_product.id, 'quantity': 1,
        }, content_type='application/json')
        checkout = self.client.post('/api/v1/checkout/', {
            'address': 'Calle 10 # 5-20', 'city': 'Riohacha', 'payment_method': 'contact',
        }, content_type='application/json')
        self.assertEqual(added.status_code, 201)
        self.assertEqual(checkout.status_code, 201)

        self.client.force_login(admin)
        report = self.client.get('/api/v1/admin/inventory/report/?threshold=2')
        movements = report.json()['movements']
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()['movement_count'], 2)
        self.assertEqual({item['reason'] for item in movements}, {'admin_adjustment', 'checkout'})
        checkout_movement = next(item for item in movements if item['product_id'] == checkout_product.id)
        self.assertEqual((checkout_movement['before'], checkout_movement['after'], checkout_movement['delta']), (3, 2, -1))

    def test_inventory_report_requires_authorized_product_access(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/admin/inventory/report/?threshold=5')
        self.assertIn(response.status_code, (401, 403))

    def test_inventory_report_summary_uses_all_records_across_pages(self):
        admin = self.create_role_user('admin-inventory-report-pagination', AccessRole.Code.ADMIN)
        Product.objects.bulk_create([
            Product(
                sku=f'REPORT-PAGE-{index:02d}', name=f'Producto paginado {index}',
                category=self.category, price=Decimal('1000'), stock=index,
            )
            for index in range(1, 22)
        ])
        self.client.force_login(admin)

        first = self.client.get('/api/v1/admin/inventory/report/?threshold=2&page=1')
        second = self.client.get('/api/v1/admin/inventory/report/?threshold=2&page=2')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()['products']['count'], 22)
        self.assertEqual(len(first.json()['products']['results']), 20)
        self.assertEqual(len(second.json()['products']['results']), 2)
        self.assertEqual(first.json()['summary']['product_count'], 22)
        self.assertEqual(first.json()['summary']['total_units'], 235)


    def test_admin_can_manage_products_and_order_status(self):
        admin = self.create_role_user('admin-api', AccessRole.Code.ADMIN)
        craftswoman = Craftswoman.objects.create(name='Tejedora asignada por administración', region='Alta Guajira', active=True)
        second_category = Category.objects.create(name='Accesorios para prueba', active=True)
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao, La Guajira')
        self.client.force_login(admin)

        options = self.client.get('/api/v1/admin/products/options/').json()
        self.assertIn(craftswoman.name, [item['name'] for item in options['craftswomen']])
        self.assertIn(self.category.id, [item['id'] for item in options['categories']])
        self.assertTrue(all(not item['is_internal'] for item in options['categories']))

        created = self.client.post('/api/v1/admin/products/', {
            'sku': 'API-ADMIN-001',
            'name': 'Manta administrada',
            'category': self.category.id,
            'craftswoman': craftswoman.id,
            'image_url': 'data:image/png;base64,aGVsbG8=',
            'price': '40000',
            'stock': 3,
        }, content_type='application/json')
        updated = self.client.patch(
            f"/api/v1/admin/products/{created.json().get('id', self.product.id)}/",
            {'name': 'Manta administrada editada', 'category': second_category.id, 'price': '41000', 'stock': 8, 'active': False},
            content_type='application/json',
        )
        order_status = self.client.patch(
            f'/api/v1/admin/orders/{order.id}/status/',
            {'status': Order.Status.PREPARING},
            content_type='application/json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['sku'], 'API-ADMIN-001')
        self.assertEqual(created.json()['image_url'], 'data:image/png;base64,aGVsbG8=')
        self.assertEqual(created.json()['craftswoman_name'], craftswoman.name)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['stock'], 8)
        self.assertEqual(updated.json()['name'], 'Manta administrada editada')
        self.assertEqual(updated.json()['category'], second_category.id)
        self.assertFalse(updated.json()['active'])
        self.assertEqual(order_status.status_code, 200)
        self.assertEqual(order_status.json()['status'], Order.Status.PREPARING)

    def test_admin_order_list_searches_filters_and_paginates_authorized_orders(self):
        admin = self.create_role_user('admin-order-list', AccessRole.Code.SUPERADMIN)
        other_user = self.create_role_user('order-list-other-customer', AccessRole.Code.CUSTOMER)
        other_customer = Customer.objects.create(
            user=other_user,
            name='Compradora Wayuu',
            email='compradora@example.com',
        )
        craft_user = self.create_role_user('order-list-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora Asignada', active=True)
        pending_order = Order.objects.create(
            customer=self.customer, status=Order.Status.PENDING, shipping_address='Riohacha',
        )
        assigned_order = Order.objects.create(
            customer=other_customer,
            craftswoman=craftswoman,
            status=Order.Status.PREPARING,
            shipping_address='Maicao',
        )
        for order in (pending_order, assigned_order):
            OrderItem.objects.create(
                order=order, product=self.product, quantity=1, unit_price=self.product.price,
            )

        self.client.force_login(admin)
        all_orders = self.client.get('/api/v1/admin/orders/?page_size=1')
        second_page = self.client.get('/api/v1/admin/orders/?page_size=1&page=2')
        filtered = self.client.get(
            '/api/v1/admin/orders/?status=preparing'
            f'&craftswoman_id={craftswoman.id}&customer_id={other_customer.id}'
            '&search=compradora%40example.com',
        )
        by_order_number = self.client.get(f'/api/v1/admin/orders/?search={assigned_order.id}')
        unassigned = self.client.get('/api/v1/admin/orders/?craftswoman_id=unassigned')
        assigned = self.client.get('/api/v1/admin/orders/?craftswoman_id=assigned')
        invalid_status = self.client.get('/api/v1/admin/orders/?status=unknown')
        invalid_craftswoman = self.client.get('/api/v1/admin/orders/?craftswoman_id=abc')
        invalid_customer = self.client.get('/api/v1/admin/orders/?customer_id=abc')
        assignment_id = self.client.get(
            f'/api/v1/admin/orders/?assignment=assigned&craftswoman_id={craftswoman.id}',
        )
        incompatible_filters = self.client.get(
            f'/api/v1/admin/orders/?assignment=unassigned&craftswoman_id={craftswoman.id}',
        )
        filter_options = self.client.get('/api/v1/admin/orders/filters/')

        self.assertEqual(all_orders.status_code, 200)
        self.assertEqual(all_orders.json()['count'], 2)
        self.assertIsNotNone(all_orders.json()['next'])
        self.assertEqual(len(all_orders.json()['results']), 1)
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(second_page.json()['count'], 2)
        self.assertEqual(len(second_page.json()['results']), 1)
        self.assertNotEqual(all_orders.json()['results'][0]['id'], second_page.json()['results'][0]['id'])
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()['count'], 1)
        result = filtered.json()['results'][0]
        self.assertEqual(result['id'], assigned_order.id)
        self.assertEqual(result['customer_id'], other_customer.id)
        self.assertEqual(result['customer_name'], other_customer.name)
        self.assertEqual(result['craftswoman']['name'], craftswoman.name)
        self.assertEqual([item['id'] for item in by_order_number.json()['results']], [assigned_order.id])
        self.assertEqual([item['id'] for item in unassigned.json()['results']], [pending_order.id])
        self.assertEqual([item['id'] for item in assigned.json()['results']], [assigned_order.id])
        self.assertEqual([item['id'] for item in assignment_id.json()['results']], [assigned_order.id])
        self.assertEqual(assignment_id.json()['results'][0]['allowed_statuses'], [Order.Status.SHIPPED, Order.Status.CANCELLED])
        self.assertEqual(incompatible_filters.status_code, 400)
        self.assertEqual(filter_options.status_code, 200)
        self.assertEqual(filter_options.json()['craftswomen'], [{'id': craftswoman.id, 'name': craftswoman.name}])
        self.assertEqual(invalid_status.status_code, 400)
        self.assertEqual(invalid_craftswoman.status_code, 400)
        self.assertEqual(invalid_customer.status_code, 400)

    def test_admin_order_summary_counts_all_authorized_orders_beyond_a_page(self):
        admin = self.create_role_user('admin-order-summary', AccessRole.Code.ADMIN)
        statuses = [Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.COMPLETED]
        for index in range(105):
            Order.objects.create(
                customer=self.customer,
                status=statuses[index % len(statuses)],
                shipping_address=f'Dirección {index}',
            )

        self.client.force_login(admin)
        page = self.client.get('/api/v1/admin/orders/?page_size=100')
        summary = self.client.get('/api/v1/admin/orders/summary/')

        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.json()['count'], 105)
        self.assertEqual(len(page.json()['results']), 100)
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()['total_count'], 105)
        self.assertEqual(summary.json()['pending_count'], 35)
        self.assertEqual(summary.json()['active_count'], 35)
        self.assertEqual(summary.json()['by_status'][Order.Status.COMPLETED], 35)
        self.assertEqual(len(summary.json()['recent_orders']), 3)

    def test_non_admin_roles_cannot_use_administrative_order_list(self):
        craft_user = self.create_role_user('admin-order-list-craft-denied', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(user=craft_user, name='Tejedora Sin Admin', active=True)

        self.client.force_login(self.user)
        customer_response = self.client.get('/api/v1/admin/orders/')
        self.client.force_login(craft_user)
        craftswoman_response = self.client.get('/api/v1/admin/orders/')

        self.assertEqual(customer_response.status_code, 403)
        self.assertEqual(craftswoman_response.status_code, 403)

    def test_admin_rejects_invalid_order_status_transition(self):
        admin = self.create_role_user('admin-order-invalid-transition', AccessRole.Code.ADMIN)
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao')
        self.client.force_login(admin)

        response = self.client.patch(
            f'/api/v1/admin/orders/{order.id}/status/',
            {'status': Order.Status.DELIVERED},
            content_type='application/json',
        )
        assignment_bypass = self.client.patch(
            f'/api/v1/admin/orders/{order.id}/status/',
            {'status': Order.Status.ACCEPTED},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(assignment_bypass.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(AuditEvent.objects.filter(
            action='change_order_status', object_id=str(order.id),
        ).exists())

    def test_admin_order_status_uses_specific_permission_without_full_design_edit(self):
        admin = self.create_role_user('admin-custom-order-status', AccessRole.Code.ADMIN)
        design = CustomDesign.objects.create(
            customer=self.customer, pattern='rombos', base_color='#111111',
            accent_color_one='#222222', accent_color_two='#333333', size='M',
            estimated_price=Decimal('120000'), status=Order.Status.PENDING,
        )
        product = Product.objects.create(
            sku='ADMIN-CUSTOM-DESIGN-STATUS', name='Diseño ligado', category=self.category,
            custom_design=design, price=design.estimated_price, stock=1, active=False,
        )
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao')
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=product.price)
        role = AccessRole.objects.get(code=AccessRole.Code.ADMIN)
        RolePermission.objects.filter(role=role, permission=permission_for('designs', 'change')).delete()
        capability = RBACCapability.objects.get(
            resource__code='orders', action__code='manage_design_status',
        )
        RBACGrant.objects.filter(role=role, capability=capability).delete()
        self.client.force_login(admin)

        normal_order = Order.objects.create(customer=self.customer, shipping_address='Riohacha')
        OrderItem.objects.create(
            order=normal_order, product=self.product, quantity=1, unit_price=self.product.price,
        )
        normal_updated = self.client.patch(
            f'/api/v1/admin/orders/{normal_order.id}/status/',
            {'status': Order.Status.PREPARING}, content_type='application/json',
        )
        self.assertEqual(normal_updated.status_code, 200)
        normal_order.refresh_from_db()
        self.assertEqual(normal_order.status, Order.Status.PREPARING)

        denied = self.client.patch(
            f'/api/v1/admin/orders/{order.id}/status/',
            {'status': Order.Status.PREPARING}, content_type='application/json',
        )
        order.refresh_from_db()
        design.refresh_from_db()
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(design.status, Order.Status.PENDING)
        self.assertFalse(has_permission(admin, 'designs', 'change'))

        RBACGrant.objects.create(
            role=role, capability=capability, effect=RBACGrant.Effect.ALLOW,
        )
        updated = self.client.patch(
            f'/api/v1/admin/orders/{order.id}/status/',
            {'status': Order.Status.PREPARING}, content_type='application/json',
        )
        order.refresh_from_db()
        design.refresh_from_db()
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(order.status, Order.Status.PREPARING)
        self.assertEqual(design.status, Order.Status.PREPARING)

    def test_django_order_admin_requires_specific_permission_and_syncs_design_status(self):
        admin = self.create_role_user('django-admin-custom-order-status', AccessRole.Code.ADMIN)
        design = CustomDesign.objects.create(
            customer=self.customer, pattern='olas', base_color='#111111',
            accent_color_one='#222222', accent_color_two='#333333', size='M',
            estimated_price=Decimal('120000'), status=Order.Status.PENDING,
        )
        product = Product.objects.create(
            sku='DJANGO-ADMIN-CUSTOM-STATUS', name='Diseño Django', category=self.category,
            custom_design=design, price=design.estimated_price, stock=1, active=False,
        )
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao')
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=product.price)
        model_admin = OrderAdmin(Order, django_admin.site)
        request = RequestFactory().post(f'/admin/store/order/{order.id}/change/')
        request.user = admin
        role = AccessRole.objects.get(code=AccessRole.Code.ADMIN)
        capability = RBACCapability.objects.get(
            resource__code='orders', action__code='manage_design_status',
        )
        RBACGrant.objects.filter(role=role, capability=capability).delete()
        order.status = Order.Status.PREPARING

        with self.assertRaises(DjangoPermissionDenied):
            model_admin.save_model(request, order, form=None, change=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

        RBACGrant.objects.create(
            role=role, capability=capability, effect=RBACGrant.Effect.ALLOW,
        )
        order.status = Order.Status.PREPARING

        model_admin.save_model(request, order, form=None, change=True)
        form = type('SavedOrderForm', (), {
            'instance': order,
            'save_m2m': lambda _self: None,
        })()
        model_admin.save_related(request, form, formsets=[], change=True)

        self.assertFalse(has_permission(admin, 'designs', 'change'))
        order.refresh_from_db()
        design.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PREPARING)
        self.assertEqual(design.status, Order.Status.PREPARING)

    def test_admin_status_endpoint_enforces_each_transition_from_the_shared_matrix(self):
        admin = self.create_role_user('admin-order-transition-matrix', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        for current_status, actor_rules in {
            Order.Status.PENDING: {Order.Status.PREPARING, Order.Status.CANCELLED},
            Order.Status.ACCEPTED: {Order.Status.PREPARING, Order.Status.CANCELLED},
            Order.Status.WEAVING: {Order.Status.PREPARING, Order.Status.CANCELLED},
            Order.Status.COMPLETED: {Order.Status.PAID, Order.Status.PREPARING, Order.Status.CANCELLED},
            Order.Status.PAID: {Order.Status.PREPARING, Order.Status.CANCELLED},
            Order.Status.PREPARING: {Order.Status.SHIPPED, Order.Status.CANCELLED},
            Order.Status.SHIPPED: {Order.Status.DELIVERED, Order.Status.CANCELLED},
            Order.Status.DELIVERED: set(),
            Order.Status.CANCELLED: set(),
        }.items():
            for next_status, _label in Order.Status.choices:
                order = Order.objects.create(
                    customer=self.customer,
                    status=current_status,
                    shipping_address='Maicao',
                )
                response = self.client.patch(
                    f'/api/v1/admin/orders/{order.id}/status/',
                    {'status': next_status},
                    content_type='application/json',
                )
                allowed = next_status in actor_rules
                with self.subTest(current=current_status, next=next_status):
                    self.assertEqual(response.status_code, 200 if allowed else 400)
                    order.refresh_from_db()
                    self.assertEqual(order.status, next_status if allowed else current_status)

    def test_admin_can_review_and_publish_product_submitted_by_craftswoman(self):
        craft_user = self.create_role_user('weaver-review-flow', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(
            user=craft_user, name='Tejedora Flujo', active=True,
        )
        self.client.force_login(craft_user)
        submitted = self.client.post('/api/v1/craftswoman/products/', {
            'sku': 'FLOW-WAY-001',
            'name': 'Manta de prueba de flujo',
            'category': self.category.id,
            'description': 'Manta tejida para comprobar la revisión administrativa.',
            'region': 'La Guajira',
            'color': 'Borgoña y crema',
            'size': 'M',
            'production_time': '15 días',
            'image_url': 'https://example.com/flow-wayuu.jpg',
            'price': '280000',
            'stock': 1,
        }, content_type='application/json')
        self.assertEqual(submitted.status_code, 201)
        self.assertFalse(submitted.json()['active'])

        admin = self.create_role_user('admin-review-flow', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        review_list = self.client.get('/api/v1/admin/products/')
        reviewed_product = next(
            item for item in review_list.json() if item['sku'] == 'FLOW-WAY-001'
        )
        self.assertEqual(reviewed_product['craftswoman'], craftswoman.id)
        self.assertEqual(reviewed_product['craftswoman_name'], 'Tejedora Flujo')
        self.assertFalse(reviewed_product['active'])

        approved = self.client.patch(
            f"/api/v1/admin/products/{submitted.json()['id']}/",
            {'active': True},
            content_type='application/json',
        )
        self.assertEqual(approved.status_code, 200)
        self.assertTrue(approved.json()['active'])
        self.assertEqual(approved.json()['craftswoman'], craftswoman.id)

    def test_admin_product_routes_reject_customers(self):
        self.client.force_login(self.user)

        products = self.client.get('/api/v1/admin/products/')
        categories = self.client.get('/api/v1/admin/categories/')

        self.assertIn(products.status_code, (401, 403))
        self.assertIn(categories.status_code, (401, 403))

    def test_admin_can_create_and_update_categories(self):
        admin = self.create_role_user('admin-category-api', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        created = self.client.post('/api/v1/admin/categories/', {
            'name': 'Tejidos especiales',
            'description': 'Piezas bajo solicitud.',
            'active': True,
        }, content_type='application/json')
        category_id = created.json()['id']
        updated = self.client.patch(
            f'/api/v1/admin/categories/{category_id}/',
            {'active': False},
            content_type='application/json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json()['active'])

    def test_anonymous_user_cannot_access_cart_or_orders(self):
        self.assertEqual(self.client.get('/api/v1/cart/').status_code, 401)
        self.assertEqual(self.client.get('/api/v1/orders/').status_code, 401)
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 401)

    def test_auth_me_distinguishes_admin_and_superadmin_from_role_assignments(self):
        admin = self.create_role_user('role-admin', AccessRole.Code.ADMIN)
        superadmin = self.create_role_user('role-superadmin', AccessRole.Code.SUPERADMIN)
        Craftswoman.objects.create(user=admin, name='Perfil no autoritativo')

        self.client.force_login(admin)
        admin_payload = self.client.get('/api/v1/auth/me/').json()['user']
        self.client.force_login(superadmin)
        superadmin_role = self.client.get('/api/v1/auth/me/').json()['user']['role']
        admin.refresh_from_db()
        superadmin.refresh_from_db()

        self.assertTrue(admin.is_staff)
        self.assertFalse(admin.is_superuser)
        self.assertTrue(superadmin.is_staff)
        self.assertTrue(superadmin.is_superuser)
        self.assertEqual(admin_payload['role'], AccessRole.Code.ADMIN)
        self.assertIsNone(admin_payload['profile'])
        self.assertEqual(superadmin_role, AccessRole.Code.SUPERADMIN)

    def test_all_protected_endpoint_methods_obey_the_role_matrix(self):
        active_craft = self.create_role_user('matrix-craft-active', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(user=active_craft, name='Tejedora activa', active=True)
        inactive_craft = self.create_role_user('matrix-craft-inactive', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(user=inactive_craft, name='Tejedora inactiva', active=False)
        admin = self.create_role_user('matrix-admin', AccessRole.Code.ADMIN)
        superadmin = self.create_role_user('matrix-superadmin', AccessRole.Code.SUPERADMIN)
        unassigned = User.objects.create_user(username='matrix-sin-rol', password='ClaveSegura2026!')

        endpoints = (
            ('get', '/api/v1/auth/me/', {'customer', 'craft-active', 'craft-inactive', 'admin', 'superadmin'}),
            ('get', '/api/v1/profile/', {'customer'}),
            ('patch', '/api/v1/profile/', {'customer'}),
            ('get', '/api/v1/cart/', {'customer'}),
            ('post', '/api/v1/cart/items/', {'customer'}),
            ('post', '/api/v1/cart/legacy-items/remove/', {'customer'}),
            ('patch', '/api/v1/cart/items/999999/', {'customer'}),
            ('delete', '/api/v1/cart/items/999999/', {'customer'}),
            ('post', '/api/v1/checkout/', {'customer'}),
            ('get', '/api/v1/orders/', {'customer', 'craft-active', 'admin', 'superadmin'}),
            ('get', '/api/v1/orders/999999/', {'customer', 'craft-active', 'admin', 'superadmin'}),
            ('get', '/api/v1/designs/', {'customer'}),
            ('post', '/api/v1/designs/', {'customer'}),
            ('get', '/api/v1/craftswoman/dashboard/', {'craft-active'}),
            ('post', '/api/v1/craftswoman/orders/999999/accept/', {'craft-active'}),
            ('patch', '/api/v1/craftswoman/orders/999999/status/', {'craft-active'}),
            ('patch', '/api/v1/craftswoman/designs/999999/status/', {'craft-active'}),
            ('get', '/api/v1/admin/products/', {'admin', 'superadmin'}),
            ('post', '/api/v1/admin/products/', {'admin', 'superadmin'}),
            ('patch', '/api/v1/admin/products/999999/', {'admin', 'superadmin'}),
            ('get', '/api/v1/admin/categories/', {'admin', 'superadmin'}),
            ('post', '/api/v1/admin/categories/', {'admin', 'superadmin'}),
            ('patch', '/api/v1/admin/categories/999999/', {'admin', 'superadmin'}),
            ('get', '/api/v1/admin/orders/', {'admin', 'superadmin'}),
            ('get', '/api/v1/admin/orders/filters/', {'admin', 'superadmin'}),
            ('get', '/api/v1/admin/orders/summary/', {'admin', 'superadmin'}),
            ('patch', '/api/v1/admin/orders/999999/status/', {'admin', 'superadmin'}),
        )
        accounts = {
            'customer': self.user,
            'craft-active': active_craft,
            'craft-inactive': inactive_craft,
            'admin': admin,
            'superadmin': superadmin,
            'unassigned': unassigned,
        }

        for actor, user in accounts.items():
            client = Client()
            client.force_login(user)
            for method, path, permitted_roles in endpoints:
                with self.subTest(actor=actor, method=method, path=path):
                    if actor not in permitted_roles:
                        self.assertEqual(getattr(client, method)(path, data={}, content_type='application/json').status_code, 403)
                        continue
                    response = getattr(client, method)(path, data={}, content_type='application/json')
                    self.assertNotIn(response.status_code, (401, 403))

        anonymous = Client()
        for method, path, _ in endpoints:
            with self.subTest(actor='anonymous', method=method, path=path):
                response = getattr(anonymous, method)(path, data={}, content_type='application/json')
                self.assertEqual(response.status_code, 401)

    def test_registration_assigns_customer_role_and_password_login_creates_session(self):
        client = Client(enforce_csrf_checks=True)
        csrf = client.get('/api/v1/csrf/').cookies['csrftoken'].value
        response = client.post('/api/v1/auth/register/', {
            'name': 'Cliente con rol',
            'username': 'cliente-con-rol',
            'email': 'cliente-con-rol@example.com',
            'password': 'OtraClaveSegura2026!',
        }, content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['role'], AccessRole.Code.CUSTOMER)
        self.assertEqual(client.get('/api/v1/auth/me/').json()['user']['role'], AccessRole.Code.CUSTOMER)
        logout = client.post('/api/v1/auth/logout/', {}, content_type='application/json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(client.get('/api/v1/auth/me/').status_code, 401)

    def test_craftswoman_registration_assigns_role_and_keeps_profile_inactive(self):
        client = Client(enforce_csrf_checks=True)
        csrf = client.get('/api/v1/csrf/').cookies['csrftoken'].value
        response = client.post('/api/v1/auth/register/craftswoman/', {
            'name': 'Tejedora pendiente',
            'username': 'tejedora-pendiente',
            'email': 'tejedora-pendiente@example.com',
            'password': 'OtraClaveSegura2026!',
            'community': 'Comunidad de prueba',
            'region': 'La Guajira',
        }, content_type='application/json', HTTP_X_CSRFTOKEN=csrf)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['role'], AccessRole.Code.CRAFTSWOMAN)
        self.assertFalse(Craftswoman.objects.get(user__username='tejedora-pendiente').active)
        self.assertEqual(client.get('/api/v1/auth/me/').json()['user']['role'], AccessRole.Code.CRAFTSWOMAN)
        self.assertEqual(client.get('/api/v1/craftswoman/dashboard/').status_code, 403)

    def test_html_login_redirects_by_persisted_role(self):
        craft_user = self.create_role_user('html-craft', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(user=craft_user, name='Tejedora HTML', active=True)
        admin = self.create_role_user('html-admin', AccessRole.Code.ADMIN)
        superadmin = self.create_role_user('html-superadmin', AccessRole.Code.SUPERADMIN)
        expected = (
            (self.user, '/'),
            (craft_user, '/panel-tejedora/'),
            (admin, '/admin/'),
            (superadmin, '/admin/'),
        )

        for user, destination in expected:
            client = Client()
            response = client.post('/cuenta/iniciar-sesion/', {
                'username': user.username,
                'password': 'ClaveSegura2026!',
            })
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response['Location'], destination)

    def test_html_login_does_not_authenticate_account_without_role(self):
        unassigned = User.objects.create_user(
            username='html-sin-rol',
            password='ClaveSegura2026!',
        )
        client = Client()
        response = client.post('/cuenta/iniciar-sesion/', {
            'username': unassigned.username,
            'password': 'ClaveSegura2026!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', client.session)

    def test_expired_session_is_rejected_by_auth_me(self):
        self.client.force_login(self.user)
        session = self.client.session
        session.set_expiry(timezone.now() - timedelta(seconds=1))
        session.save()

        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 401)

    def test_login_accepts_email_and_logout_invalidates_session(self):
        response = self.client.post('/api/v1/auth/login/', {
            'username': self.user.email,
            'password': 'ClaveSegura2026!',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['role'], AccessRole.Code.CUSTOMER)
        self.assertIn('sessionid', self.client.cookies)
        self.assertTrue(self.client.cookies['sessionid']['httponly'])
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/auth/logout/').status_code, 204)
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 401)

    def test_html_logout_requires_csrf_protected_post(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        csrf = client.get('/api/v1/csrf/').cookies['csrftoken'].value

        self.assertEqual(client.get('/cuenta/salir/').status_code, 405)
        self.assertEqual(client.get('/api/v1/auth/me/').status_code, 200)
        denied = client.post('/cuenta/salir/')
        self.assertEqual(denied.status_code, 403)
        success = client.post('/cuenta/salir/', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(success.status_code, 302)
        self.assertEqual(client.get('/api/v1/auth/me/').status_code, 401)

    def test_login_rejects_bad_credentials_without_creating_a_session(self):
        response = self.client.post('/api/v1/auth/login/', {
            'username': self.user.username,
            'password': 'incorrecta',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], 'Usuario o contraseña incorrectos.')
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 401)

    def test_api_login_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        csrf = client.get('/api/v1/csrf/').cookies['csrftoken'].value
        data = {'username': self.user.username, 'password': 'ClaveSegura2026!'}

        missing_token = client.post('/api/v1/auth/login/', data, content_type='application/json')
        self.assertEqual(missing_token.status_code, 403)
        valid_token = client.post(
            '/api/v1/auth/login/',
            data,
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(valid_token.status_code, 200)
        self.assertEqual(valid_token.json()['user']['role'], AccessRole.Code.CUSTOMER)

    @override_settings(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='None',
        SESSION_COOKIE_HTTPONLY=True,
        CSRF_COOKIE_SECURE=True,
        CSRF_COOKIE_SAMESITE='None',
    )
    def test_cross_site_session_cookie_security_attributes(self):
        client = Client(enforce_csrf_checks=True)
        csrf = client.get('/api/v1/csrf/').cookies['csrftoken'].value
        response = client.post(
            '/api/v1/auth/login/',
            {'username': self.user.username, 'password': 'ClaveSegura2026!'},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 200)
        session_cookie = response.cookies['sessionid']
        csrf_cookie = response.cookies['csrftoken']
        self.assertTrue(session_cookie['httponly'])
        self.assertTrue(session_cookie['secure'])
        self.assertEqual(session_cookie['samesite'], 'None')
        self.assertTrue(csrf_cookie['secure'])
        self.assertEqual(csrf_cookie['samesite'], 'None')

    def test_staff_flag_without_role_does_not_grant_administration(self):
        unassigned = User.objects.create_user(
            username='staff-sin-rol',
            password='ClaveSegura2026!',
            is_staff=True,
        )
        self.client.force_login(unassigned)

        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/products/').status_code, 403)
        self.assertFalse(UserRole.objects.filter(user=unassigned).exists())
        login_client = Client()
        login_response = login_client.post('/api/v1/auth/login/', {
            'username': unassigned.username,
            'password': 'ClaveSegura2026!',
        }, content_type='application/json')
        self.assertEqual(login_response.status_code, 403)
        self.assertEqual(login_client.get('/api/v1/auth/me/').status_code, 401)

    def test_superuser_flag_without_role_does_not_grant_admin_site(self):
        unassigned = User.objects.create_superuser(
            username='superuser-sin-rol',
            email='superuser-sin-rol@example.com',
            password='ClaveSegura2026!',
        )
        self.client.force_login(unassigned)

        self.assertEqual(self.client.get('/admin/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 403)
        self.assertFalse(UserRole.objects.filter(user=unassigned).exists())

    def test_audit_user_roles_dry_run_and_explicit_confirmation(self):
        candidate = User.objects.create_user(
            username='role-audit-candidate',
            password='ClaveSegura2026!',
        )
        output = StringIO()
        call_command(
            'audit_user_roles',
            '--dry-run',
            '--assign', f'{candidate.id}:customer',
            stdout=output,
        )
        self.assertIn(f'ID={candidate.id}', output.getvalue())
        self.assertFalse(UserRole.objects.filter(user=candidate).exists())

        with self.assertRaises(CommandError):
            call_command('audit_user_roles', '--apply', '--assign', f'{candidate.id}:admin')
        self.assertFalse(UserRole.objects.filter(user=candidate).exists())

        call_command(
            'audit_user_roles',
            '--apply',
            '--assign', f'{candidate.id}:customer',
            '--confirm-user', str(candidate.id),
            stdout=StringIO(),
        )
        self.assertEqual(UserRole.objects.get(user=candidate).role.code, AccessRole.Code.CUSTOMER)

    def test_seed_rbac_users_dry_run_create_profiles_and_remain_idempotent(self):
        usernames = (
            'maleja.superadmin', 'oscar.admin', 'matthew.admin',
            'dayana.craftswoman', 'thania.craftswoman', 'zharik.craftswoman',
            'sarith.craftswoman', 'ana.craftswoman', 'gabriel.customer',
            'sneider.customer', 'carmen.customer', 'cleotilde.customer',
        )
        expected = {
            'maleja.superadmin': ('Maleja', AccessRole.Code.SUPERADMIN),
            'oscar.admin': ('Oscar', AccessRole.Code.ADMIN),
            'matthew.admin': ('Matthew', AccessRole.Code.ADMIN),
            'dayana.craftswoman': ('Dayana', AccessRole.Code.CRAFTSWOMAN),
            'thania.craftswoman': ('Thania', AccessRole.Code.CRAFTSWOMAN),
            'zharik.craftswoman': ('Zharik', AccessRole.Code.CRAFTSWOMAN),
            'sarith.craftswoman': ('Sarith', AccessRole.Code.CRAFTSWOMAN),
            'ana.craftswoman': ('Ana', AccessRole.Code.CRAFTSWOMAN),
            'gabriel.customer': ('Gabriel', AccessRole.Code.CUSTOMER),
            'sneider.customer': ('Sneider', AccessRole.Code.CUSTOMER),
            'carmen.customer': ('Carmen', AccessRole.Code.CUSTOMER),
            'cleotilde.customer': ('Cleotilde', AccessRole.Code.CUSTOMER),
        }
        initial_count = User.objects.count()
        with TemporaryDirectory() as temporary_directory:
            with override_settings(BASE_DIR=Path(temporary_directory)):
                dry_run_output = StringIO()
                call_command('seed_rbac_test_users', stdout=dry_run_output)
                self.assertIn('Dry-run', dry_run_output.getvalue())
                self.assertEqual(User.objects.count(), initial_count)
                self.assertFalse((Path(temporary_directory) / '.local').exists())

                apply_output = StringIO()
                call_command('seed_rbac_test_users', '--apply', stdout=apply_output)
                self.assertEqual(User.objects.count(), initial_count + 12)
                self.assertNotIn('Maleja12345', apply_output.getvalue())

                created_users = User.objects.filter(username__in=usernames).order_by('username')
                self.assertEqual(created_users.count(), 12)
                self.assertEqual(UserRole.objects.filter(user__username__in=usernames).count(), 12)
                for username, (name, role_code) in expected.items():
                    user = User.objects.get(username=username)
                    assignment = UserRole.objects.select_related('role').get(user=user)
                    self.assertEqual(user.first_name, name)
                    self.assertEqual(user.email, f'{username}@store-wayuu-test.example.invalid')
                    self.assertEqual(assignment.role.code, role_code)
                    self.assertTrue(user.check_password(f'{name}12345'))
                    self.assertTrue(user.is_staff, msg=username) if role_code in (
                        AccessRole.Code.ADMIN, AccessRole.Code.SUPERADMIN,
                    ) else self.assertFalse(user.is_staff, msg=username)
                    self.assertEqual(user.is_superuser, role_code == AccessRole.Code.SUPERADMIN)
                    if role_code == AccessRole.Code.CRAFTSWOMAN:
                        self.assertTrue(Craftswoman.objects.get(user=user).active)
                    elif role_code == AccessRole.Code.CUSTOMER:
                        self.assertTrue(Customer.objects.filter(user=user, email=user.email).exists())

                credential_file = Path(temporary_directory) / '.local' / 'rbac-test-users.json'
                if os.name == 'nt':
                    acl_check = subprocess.run(
                        ['icacls.exe', str(credential_file)],
                        capture_output=True,
                        check=False,
                        text=True,
                    )
                    self.assertEqual(acl_check.returncode, 0, msg=acl_check.stderr)
                    acl = acl_check.stdout.casefold()
                    broad_principals = (
                        's-1-1-0', 's-1-5-11', 's-1-5-32-545', 'everyone',
                        'authenticated users', 'builtin\\users', 'todos',
                        'usuarios autenticados',
                    )
                    self.assertFalse(
                        any(principal in acl for principal in broad_principals),
                        msg=f'El archivo de credenciales concede acceso a un grupo amplio: {acl}',
                    )
                else:
                    self.assertEqual(stat.S_IMODE(credential_file.stat().st_mode), 0o600)
                credentials_before = credential_file.read_bytes()
                password_hashes = {user.username: user.password for user in created_users}
                repeat_output = StringIO()
                call_command('seed_rbac_test_users', '--apply', stdout=repeat_output)
                self.assertIn('sin cambios', repeat_output.getvalue().casefold())
                self.assertEqual(credential_file.read_bytes(), credentials_before)
                self.assertEqual(
                    {user.username: user.password for user in User.objects.filter(username__in=usernames)},
                    password_hashes,
                )
                self.assertEqual(User.objects.count(), initial_count + 12)

    def test_seed_rbac_users_conflict_aborts_without_modification(self):
        existing = User.objects.create_user(
            username='maleja.superadmin',
            email='other-account@example.invalid',
            password='ExistingPassword123!',
            first_name='Otra persona',
        )
        original_hash = existing.password
        initial_count = User.objects.count()
        with TemporaryDirectory() as temporary_directory:
            with override_settings(BASE_DIR=Path(temporary_directory)):
                with self.assertRaises(CommandError):
                    call_command('seed_rbac_test_users', '--apply', stdout=StringIO())
                existing.refresh_from_db()
                self.assertEqual(existing.password, original_hash)
                self.assertEqual(User.objects.count(), initial_count)
                self.assertFalse(UserRole.objects.filter(user=existing).exists())
                self.assertFalse((Path(temporary_directory) / '.local').exists())

    def test_admin_cannot_manage_roles_but_superadmin_can(self):
        admin = self.create_role_user('role-admin-no-rbac', AccessRole.Code.ADMIN)
        superadmin = self.create_role_user('role-superadmin-rbac', AccessRole.Code.SUPERADMIN)
        roles_url = '/admin/store/accessrole/'

        self.client.force_login(admin)
        self.assertEqual(self.client.get(roles_url).status_code, 403)
        self.client.force_login(superadmin)
        self.assertEqual(self.client.get(roles_url).status_code, 200)

    def test_commercial_django_admin_requires_effective_role_permission(self):
        admin = self.create_role_user('rbac-modeladmin-admin', AccessRole.Code.ADMIN)
        permission = permission_for('products', 'view')
        self.client.force_login(admin)

        self.assertEqual(self.client.get('/admin/store/product/').status_code, 200)
        RolePermission.objects.filter(
            role=admin.access_profile.role,
            permission__content_type__app_label='store',
            permission__codename__in=(permission.codename, 'change_product'),
        ).delete()
        self.assertEqual(self.client.get('/admin/store/product/').status_code, 403)

    def test_product_list_editable_change_is_persisted_and_audited(self):
        superadmin = self.create_role_user('rbac-list-editable-superadmin', AccessRole.Code.SUPERADMIN)
        self.client.force_login(superadmin)
        response = self.client.get('/admin/store/product/')
        formset = response.context['cl'].formset
        form = formset.forms[0]
        data = {
            f'{formset.prefix}-TOTAL_FORMS': str(formset.total_form_count()),
            f'{formset.prefix}-INITIAL_FORMS': str(formset.initial_form_count()),
            f'{formset.prefix}-MIN_NUM_FORMS': '0',
            f'{formset.prefix}-MAX_NUM_FORMS': '1000',
        }
        for field_name in form.fields:
            if field_name == 'id':
                value = self.product.pk
            elif field_name == 'price':
                value = '56000'
            elif field_name == 'stock':
                value = '7'
            elif field_name == 'active':
                value = 'on'
            else:
                value = form.initial.get(field_name)
            if value is not None:
                data[f'{formset.prefix}-0-{field_name}'] = value
        data['_save'] = 'Guardar'

        update = self.client.post('/admin/store/product/', data)

        self.assertEqual(update.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal('56000'))
        self.assertEqual(self.product.stock, 7)
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='update_products',
            resource='products',
            object_id=str(self.product.id),
        ).exists())

    def test_scoped_modeladmins_save_commercial_models(self):
        actor = self.create_role_user('rbac-modeladmin-save-superadmin', AccessRole.Code.SUPERADMIN)
        request = RequestFactory().post('/admin/')
        request.user = actor
        craftswoman = Craftswoman(name='Artesana de Admin')
        customer = Customer(name='Cliente Admin', email='admin-customer@example.com')
        product = Product(
            sku='ADMIN-SAVE-001',
            name='Manta Admin',
            category=self.category,
            price=Decimal('50000'),
            stock=2,
        )
        order = Order(customer=self.customer, shipping_address='Riohacha')
        design = CustomDesign(
            customer=self.customer,
            pattern='rombos',
            base_color='#112233',
            accent_color_one='#223344',
            accent_color_two='#334455',
            estimated_price=Decimal('120000'),
        )
        cases = (
            (CategoryAdmin, Category, Category(name='Categoría Admin')),
            (CraftswomanAdmin, Craftswoman, craftswoman),
            (CustomerAdmin, Customer, customer),
            (ProductAdmin, Product, product),
            (OrderAdmin, Order, order),
            (CustomDesignAdmin, CustomDesign, design),
        )

        for admin_class, model, instance in cases:
            with self.subTest(admin=admin_class.__name__):
                model_admin = admin_class(model, django_admin.site)
                model_admin.save_model(request, instance, form=None, change=False)
                self.assertIsNotNone(instance.pk)
                model_admin.save_model(request, instance, form=None, change=True)

    def test_individual_user_admin_delete_is_audited(self):
        actor = self.create_role_user('rbac-user-delete-superadmin', AccessRole.Code.SUPERADMIN)
        target = self.create_role_user('rbac-user-delete-target', AccessRole.Code.CUSTOMER)
        request = RequestFactory().post('/admin/auth/user/')
        request.user = actor
        model_admin = WayuuUserAdmin(User, django_admin.site)
        target_id = target.pk
        target_username = target.username

        model_admin.delete_model(request, target)

        self.assertFalse(User.objects.filter(pk=target_id).exists())
        event = AuditEvent.objects.get(
            actor=actor,
            action='delete_user',
            details__username=target_username,
        )
        self.assertIsNone(event.affected_user_id)

    def test_user_admin_deactivation_and_bulk_delete_revoke_admin_scope_with_actor(self):
        superadmin = self.create_role_user('rbac-scope-owner-superadmin', AccessRole.Code.SUPERADMIN)
        admin_user = self.create_role_user('rbac-scope-deactivate-admin', AccessRole.Code.ADMIN)
        set_permission_delegation(superadmin, admin_user, 'products', 'view', True)
        set_user_permission(admin_user, self.user, 'products', 'view', UserPermissionGrant.Effect.ALLOW)
        permission = permission_for('products', 'view')
        request = RequestFactory().post('/admin/auth/user/')
        request.user = superadmin
        user_admin = WayuuUserAdmin(User, django_admin.site)

        admin_user.is_active = False
        user_admin.save_model(request, admin_user, form=None, change=True)

        self.assertFalse(PermissionDelegation.objects.filter(admin=admin_user).exists())
        self.assertFalse(UserPermissionGrant.objects.filter(user=self.user, permission=permission).exists())
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='revoke_user_permission',
            affected_user=self.user,
            details__reason='admin_scope_revoked',
        ).exists())

        admin_user.refresh_from_db()
        admin_user.is_active = True
        admin_user.save(update_fields=('is_active',))
        set_permission_delegation(superadmin, admin_user, 'products', 'view', True)
        set_user_permission(admin_user, self.user, 'products', 'view', UserPermissionGrant.Effect.ALLOW)
        user_admin.delete_queryset(request, User.objects.filter(pk=admin_user.pk))

        self.assertFalse(User.objects.filter(pk=admin_user.pk).exists())
        self.assertFalse(PermissionDelegation.objects.filter(admin=admin_user).exists())
        self.assertFalse(UserPermissionGrant.objects.filter(user=self.user, permission=permission).exists())
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='delete_user',
            details__username=admin_user.username,
        ).exists())

    def test_user_role_admin_demotion_revocation_keeps_superadmin_actor(self):
        superadmin = self.create_role_user('rbac-role-admin-superadmin', AccessRole.Code.SUPERADMIN)
        admin_user = self.create_role_user('rbac-role-demoted-admin', AccessRole.Code.ADMIN)
        set_permission_delegation(superadmin, admin_user, 'products', 'view', True)
        set_user_permission(admin_user, self.user, 'products', 'view', UserPermissionGrant.Effect.ALLOW)
        assignment = admin_user.access_profile
        assignment.role = AccessRole.objects.get(code=AccessRole.Code.CUSTOMER)
        request = RequestFactory().post('/admin/store/userrole/')
        request.user = superadmin
        model_admin = UserRoleAdmin(UserRole, django_admin.site)

        model_admin.save_model(request, assignment, form=None, change=True)

        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='revoke_user_permission',
            affected_user=self.user,
            details__reason='admin_scope_revoked',
        ).exists())

    def test_inactive_users_cannot_login_or_reuse_sessions_in_api_and_admin(self):
        inactive_customer = User.objects.create_user(
            username='inactive-customer-login',
            password='ClaveSegura2026!',
            is_active=False,
        )
        self.assign_role(inactive_customer, AccessRole.Code.CUSTOMER)
        login_client = Client()
        login_response = login_client.post('/api/v1/auth/login/', {
            'username': inactive_customer.username,
            'password': 'ClaveSegura2026!',
        }, content_type='application/json')
        self.assertEqual(login_response.status_code, 400)
        self.assertEqual(login_client.get('/api/v1/auth/me/').status_code, 401)

        customer = self.create_role_user('customer-deactivated-with-session', AccessRole.Code.CUSTOMER)
        customer_client = Client()
        self.assertTrue(customer_client.login(username=customer.username, password='ClaveSegura2026!'))
        self.assertEqual(customer_client.get('/api/v1/auth/me/').status_code, 200)
        customer.is_active = False
        customer.save(update_fields=('is_active',))
        self.assertEqual(customer_client.get('/api/v1/auth/me/').status_code, 401)
        self.assertEqual(customer_client.get('/api/v1/cart/').status_code, 401)

        admin_user = self.create_role_user('admin-deactivated-with-session', AccessRole.Code.ADMIN)
        admin_client = Client()
        self.assertTrue(admin_client.login(username=admin_user.username, password='ClaveSegura2026!'))
        admin_user.is_active = False
        admin_user.save(update_fields=('is_active',))
        self.assertEqual(admin_client.get('/api/v1/admin/products/').status_code, 401)
        self.assertIn(admin_client.get('/admin/').status_code, (302, 401, 403))

    def test_role_with_active_users_cannot_be_deactivated_through_api(self):
        superadmin = self.create_role_user('rbac-role-state-superadmin', AccessRole.Code.SUPERADMIN)
        self.client.force_login(superadmin)
        response = self.client.patch(
            '/api/v1/admin/rbac/roles/customer/permissions/',
            {'active': False},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(AccessRole.objects.get(code=AccessRole.Code.CUSTOMER).active)
        self.assertTrue(UserRole.objects.filter(user=self.user, role__code=AccessRole.Code.CUSTOMER).exists())

    def test_superadmin_user_list_returns_real_fields_filters_and_restricts_access(self):
        admin = self.create_role_user('users-admin', AccessRole.Code.ADMIN)
        craft_active = self.create_role_user('users-craft-active', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(
            user=craft_active,
            name='Tejedora de consulta',
            community='Mayapo',
            region='La Guajira',
            active=True,
        )
        craft_inactive = self.create_role_user('users-craft-inactive', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(user=craft_inactive, name='Tejedora inactiva', active=False)
        superadmin = self.create_role_user('users-superadmin', AccessRole.Code.SUPERADMIN)
        unassigned = User.objects.create_user(username='users-sin-rol', email='unassigned@example.invalid')

        self.client.force_login(superadmin)
        response = self.client.get('/api/v1/admin/users/')
        self.assertEqual(response.status_code, 200)
        rows = {row['username']: row for row in response.json()}
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[self.user.username]['full_name'], 'Cliente API')
        self.assertEqual(rows[self.user.username]['email'], self.user.email)
        self.assertEqual(rows[self.user.username]['role'], AccessRole.Code.CUSTOMER)
        self.assertTrue(rows[self.user.username]['is_active'])
        self.assertEqual(rows[craft_active.username]['role_name'], 'Tejedora')
        self.assertEqual(rows[craft_active.username]['location'], 'Mayapo')
        self.assertTrue(rows[craft_inactive.username]['is_active'])
        self.assertFalse(rows[craft_inactive.username]['active'])
        self.assertEqual(rows[unassigned.username]['role'], 'unassigned')

        self.assertEqual(
            len(self.client.get('/api/v1/admin/users/?role=craftswoman').json()),
            2,
        )
        self.assertEqual(
            len(self.client.get('/api/v1/admin/users/?role=unassigned').json()),
            1,
        )
        self.assertEqual(
            [row['username'] for row in self.client.get('/api/v1/admin/users/?search=Mayapo').json()],
            [craft_active.username],
        )
        self.assertEqual(
            self.client.get('/api/v1/admin/users/?role=unknown').status_code,
            400,
        )

        self.client.force_login(admin)
        self.assertEqual(self.client.get('/api/v1/admin/users/').status_code, 200)
        for non_superadmin in (self.user, craft_active):
            self.client.force_login(non_superadmin)
            self.assertEqual(self.client.get('/api/v1/admin/users/').status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get('/api/v1/admin/users/').status_code, 401)

    def test_superadmin_can_create_users_for_all_roles_with_coherent_profiles(self):
        superadmin = self.create_role_user('managed-users-superadmin', AccessRole.Code.SUPERADMIN)
        self.client.force_login(superadmin)
        users = {}
        for role in AccessRole.Code.values:
            response = self.client.post('/api/v1/admin/users/', {
                'username': f'managed-{role}',
                'email': f'managed-{role}@example.com',
                'first_name': 'Cuenta',
                'last_name': role,
                'role': role,
                'password': 'Managed-Strong-2026!Pass',
                'phone': '3001234567',
                'city': 'Riohacha',
                'community': 'Mayapo',
                'region': 'La Guajira',
            }, content_type='application/json')
            with self.subTest(role=role):
                self.assertEqual(response.status_code, 201, response.content)
                self.assertEqual(response.json()['role'], role)
            users[role] = User.objects.get(username=f'managed-{role}')

        customer = Customer.objects.get(user=users[AccessRole.Code.CUSTOMER])
        craftswoman = Craftswoman.objects.get(user=users[AccessRole.Code.CRAFTSWOMAN])
        self.assertEqual(customer.city, 'Riohacha')
        self.assertEqual(customer.phone, '3001234567')
        self.assertEqual(craftswoman.community, 'Mayapo')
        self.assertEqual(craftswoman.region, 'La Guajira')
        self.assertFalse(craftswoman.active)
        users[AccessRole.Code.ADMIN].refresh_from_db()
        users[AccessRole.Code.SUPERADMIN].refresh_from_db()
        self.assertTrue(users[AccessRole.Code.ADMIN].is_staff)
        self.assertFalse(users[AccessRole.Code.ADMIN].is_superuser)
        self.assertTrue(users[AccessRole.Code.SUPERADMIN].is_superuser)

    def test_superadmin_can_edit_activate_and_switch_user_role_without_losing_profile_history(self):
        superadmin = self.create_role_user('managed-edit-superadmin', AccessRole.Code.SUPERADMIN)
        target = self.create_role_user('managed-edit-customer', AccessRole.Code.CUSTOMER)
        profile = Customer.objects.create(
            user=target,
            name='Cliente gestionado',
            email=target.email,
        )
        Order.objects.create(customer=profile, shipping_address='Historial conservado')
        self.client.force_login(superadmin)

        response = self.client.patch(f'/api/v1/admin/users/{target.id}/', {
            'username': 'managed-edit-renamed',
            'email': 'managed-edit-new@example.com',
            'first_name': 'Nombre editado',
            'last_name': 'Admin',
            'role': AccessRole.Code.CRAFTSWOMAN,
            'is_active': False,
            'phone': '3007654321',
            'community': 'Monguí',
            'region': 'La Guajira',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200, response.content)
        target.refresh_from_db()
        profile.refresh_from_db()
        craftswoman = Craftswoman.objects.get(user=target)
        self.assertEqual(target.username, 'managed-edit-renamed')
        self.assertEqual(target.email, 'managed-edit-new@example.com')
        self.assertEqual(target.access_profile.role.code, AccessRole.Code.CRAFTSWOMAN)
        self.assertFalse(target.is_active)
        self.assertEqual(profile.email, target.email)
        self.assertEqual(profile.name, 'Nombre editado Admin')
        self.assertTrue(Order.objects.filter(customer=profile, shipping_address='Historial conservado').exists())
        self.assertEqual(craftswoman.community, 'Monguí')
        self.assertFalse(craftswoman.active)

        reactivated = self.client.patch(
            f'/api/v1/admin/users/{target.id}/',
            {'is_active': True, 'craftswoman_active': True},
            content_type='application/json',
        )
        self.assertEqual(reactivated.status_code, 200, reactivated.content)
        target.refresh_from_db()
        craftswoman.refresh_from_db()
        self.assertTrue(target.is_active)
        self.assertTrue(craftswoman.active)
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='update_user',
            affected_user=target,
        ).exists())

    def test_user_management_rejects_duplicates_and_non_superadmin_writes(self):
        admin = self.create_role_user('managed-users-limited-admin', AccessRole.Code.ADMIN)
        self.client.force_login(admin)
        denied = self.client.post('/api/v1/admin/users/', {
            'username': 'forbidden-managed-user',
            'email': 'forbidden-managed@example.com',
            'role': AccessRole.Code.SUPERADMIN,
            'password': 'Managed-Strong-2026!Pass',
        }, content_type='application/json')
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(User.objects.filter(username='forbidden-managed-user').exists())

        superadmin = self.create_role_user('managed-users-duplicate-superadmin', AccessRole.Code.SUPERADMIN)
        self.client.force_login(superadmin)
        duplicate = self.client.post('/api/v1/admin/users/', {
            'username': self.user.username,
            'email': 'duplicate-managed@example.com',
            'role': AccessRole.Code.CUSTOMER,
            'password': 'Managed-Strong-2026!Pass',
        }, content_type='application/json')
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(User.objects.filter(username__iexact=self.user.username).count(), 1)

    def test_user_detail_refreshes_role_payload_and_protects_last_superadmin(self):
        superadmin = self.create_role_user('managed-last-superadmin', AccessRole.Code.SUPERADMIN)
        target = self.create_role_user('managed-role-target', AccessRole.Code.CUSTOMER)
        target_session = Client()
        target_session.force_login(target)
        self.assertEqual(target_session.get('/api/v1/auth/me/').json()['user']['role'], AccessRole.Code.CUSTOMER)
        self.client.force_login(superadmin)

        changed = self.client.patch(f'/api/v1/admin/users/{target.id}/', {
            'role': AccessRole.Code.ADMIN,
            'first_name': 'Nuevo nombre',
        }, content_type='application/json')
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertEqual(changed.json()['role'], AccessRole.Code.ADMIN)
        self.assertEqual(changed.json()['full_name'], 'Nuevo nombre')
        detail = self.client.get(f'/api/v1/admin/users/{target.id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['role'], AccessRole.Code.ADMIN)
        refreshed_session_user = target_session.get('/api/v1/auth/me/').json()['user']
        self.assertEqual(refreshed_session_user['role'], AccessRole.Code.ADMIN)
        self.assertIn('orders.change', refreshed_session_user['permissions'])
        self.assertNotIn('cart.add', refreshed_session_user['permissions'])

        protected = self.client.patch(f'/api/v1/admin/users/{superadmin.id}/', {
            'role': AccessRole.Code.ADMIN,
        }, content_type='application/json')
        self.assertEqual(protected.status_code, 400)
        superadmin.refresh_from_db()
        self.assertEqual(superadmin.access_profile.role.code, AccessRole.Code.SUPERADMIN)

    def test_inactive_craftswoman_cannot_use_craftswoman_endpoints(self):
        pending_user = self.create_role_user('role-craft-pending', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(user=pending_user, name='Tejedora pendiente', active=False)
        self.client.force_login(pending_user)

        self.assertEqual(self.client.get('/api/v1/craftswoman/dashboard/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/orders/').status_code, 403)
        self.assertEqual(self.client.get('/panel-tejedora/').status_code, 403)

    def test_cart_rejects_quantity_above_stock(self):
        self.client.force_login(self.user)
        response = self.client.post('/api/v1/cart/items/', {
            'product_id': self.product.id,
            'quantity': 5,
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get('/api/v1/cart/').json()['count'], 0)

    def test_superadmin_has_global_permission_and_role_is_authoritative(self):
        superadmin = self.create_role_user('rbac-global-superadmin', AccessRole.Code.SUPERADMIN)
        superadmin.is_superuser = False
        superadmin.save(update_fields=('is_superuser',))

        self.assertTrue(has_permission(superadmin, 'products', 'delete'))
        self.assertTrue(has_permission(superadmin, 'users', 'view'))

    def test_permission_catalog_and_effective_role_matrices_are_complete(self):
        admin = self.create_role_user('rbac-matrix-admin', AccessRole.Code.ADMIN)
        craftswoman = self.create_role_user('rbac-matrix-craft', AccessRole.Code.CRAFTSWOMAN)
        superadmin = self.create_role_user('rbac-matrix-superadmin', AccessRole.Code.SUPERADMIN)
        catalog = permission_catalog()
        expected_pairs = {(resource, action) for resource in PERMISSION_RESOURCES if resource != 'favorites' for action in ('view', 'create', 'edit', 'delete')}
        expected_pairs.update({('favorites', action) for action in ('view', 'create', 'delete')})
        expected_pairs.update({('orders', action) for action in ('approve', 'assign', 'cancel')})
        expected_pairs.add(('orders', 'manage_design_status'))
        expected_pairs.add(('products', 'export'))
        expected_pairs.update({(resource, action) for resource in ('products', 'categories') for action in ('publish', 'unpublish')})
        expected_pairs.update({('role_assignments', 'assign'), ('roles', 'manage'), ('permissions', 'manage')})
        expected_superadmin = set(expected_pairs)
        expected_superadmin.update({('favorites', 'edit'), ('favorites', 'change')})
        expected_superadmin.update({(resource, 'add') for resource, action in expected_pairs if action == 'create'})
        expected_superadmin.update({(resource, 'change') for resource, action in expected_pairs if action == 'edit'})
        catalog_pairs = {(item['resource'], item['action']) for item in catalog}

        self.assertEqual(catalog_pairs, expected_pairs)

        expected_by_role = {
            AccessRole.Code.SUPERADMIN: expected_superadmin,
            AccessRole.Code.ADMIN: {
                ('roles', 'view'), ('users', 'view'), ('navigation', 'view'), ('permissions', 'view'), ('audit', 'view'),
                ('products', 'view'), ('products', 'create'), ('products', 'add'), ('products', 'edit'), ('products', 'change'), ('products', 'publish'), ('products', 'unpublish'),
                ('categories', 'view'), ('categories', 'create'), ('categories', 'add'), ('categories', 'edit'), ('categories', 'change'), ('categories', 'publish'), ('categories', 'unpublish'),
                ('orders', 'view'), ('orders', 'edit'), ('orders', 'change'), ('orders', 'approve'), ('orders', 'cancel'), ('orders', 'manage_design_status'),
            },
            AccessRole.Code.CUSTOMER: {
                ('customers', 'view'), ('customers', 'edit'), ('customers', 'change'),
                ('orders', 'view'), ('orders', 'create'), ('orders', 'add'),
                ('designs', 'view'), ('designs', 'create'), ('designs', 'add'),
                ('cart', 'view'), ('cart', 'create'), ('cart', 'add'), ('cart', 'edit'), ('cart', 'change'), ('cart', 'delete'),
                ('favorites', 'view'), ('favorites', 'create'), ('favorites', 'add'), ('favorites', 'delete'),
            },
            AccessRole.Code.CRAFTSWOMAN: {
                ('products', 'view'), ('products', 'create'), ('products', 'add'), ('products', 'edit'), ('products', 'change'),
                ('craftswomen', 'view'), ('craftswomen', 'edit'), ('craftswomen', 'change'),
                ('orders', 'view'), ('orders', 'edit'), ('orders', 'change'), ('orders', 'assign'),
                ('designs', 'view'), ('designs', 'edit'), ('designs', 'change'),
            },
        }
        users = {
            AccessRole.Code.SUPERADMIN: superadmin,
            AccessRole.Code.ADMIN: admin,
            AccessRole.Code.CUSTOMER: self.user,
            AccessRole.Code.CRAFTSWOMAN: craftswoman,
        }
        for role_code, user in users.items():
            with self.subTest(role=role_code):
                effective = {
                    tuple(entry.split('.', 1))
                    for entry in effective_permission_keys(user)
                }
                self.assertEqual(effective, expected_by_role[role_code])

    def test_specialized_actions_require_explicit_grants_and_preserve_denies(self):
        admin = self.create_role_user('rbac-explicit-admin', AccessRole.Code.ADMIN)
        craftswoman = self.create_role_user('rbac-explicit-craft', AccessRole.Code.CRAFTSWOMAN)
        superadmin = self.create_role_user('rbac-explicit-root', AccessRole.Code.SUPERADMIN)

        expected = {
            admin: {
                ('products', 'publish'): True,
                ('products', 'unpublish'): True,
                ('categories', 'publish'): True,
                ('categories', 'unpublish'): True,
                ('orders', 'approve'): True,
                ('orders', 'cancel'): True,
                ('orders', 'assign'): False,
            },
            craftswoman: {
                ('orders', 'assign'): True,
                ('orders', 'approve'): False,
                ('orders', 'cancel'): False,
                ('products', 'publish'): False,
                ('products', 'unpublish'): False,
            },
        }
        for user, permissions in expected.items():
            keys = set(effective_permission_keys(user))
            for (resource, action), allowed in permissions.items():
                with self.subTest(role=role_for_user(user).code, resource=resource, action=action):
                    self.assertEqual(has_permission(user, resource, action), allowed)
                    self.assertEqual(f'{resource}.{action}' in keys, allowed)

        custom = AccessRole.objects.create(code='legacy_editor', name='Editor heredado')
        target = self.create_role_user('rbac-explicit-custom', custom.code)
        RolePermission.objects.get_or_create(
            role=custom,
            permission=permission_for('orders', 'edit'),
        )
        self.assertTrue(has_permission(target, 'orders', 'edit'))
        for action in ('approve', 'assign', 'cancel'):
            self.assertFalse(has_permission(target, 'orders', action))
            self.assertNotIn(f'orders.{action}', effective_permission_keys(target))

        set_role_permission(superadmin, custom.code, 'orders', 'assign', allowed=True)
        self.assertTrue(has_permission(target, 'orders', 'assign'))
        self.assertIn('orders.assign', effective_permission_keys(target))
        set_user_permission(superadmin, target, 'orders', 'assign', UserPermissionGrant.Effect.DENY)
        self.assertFalse(has_permission(target, 'orders', 'assign'))
        self.assertNotIn('orders.assign', effective_permission_keys(target))

        # Individual and Django edit grants never imply specialized actions.
        UserPermissionGrant.objects.create(
            user=self.user,
            permission=permission_for('products', 'edit'),
            effect=UserPermissionGrant.Effect.ALLOW,
        )
        self.user.user_permissions.add(permission_for('categories', 'edit'))
        for resource, action in (
            ('products', 'publish'), ('products', 'unpublish'),
            ('categories', 'publish'), ('categories', 'unpublish'),
        ):
            self.assertFalse(has_permission(self.user, resource, action))
            self.assertNotIn(f'{resource}.{action}', effective_permission_keys(self.user))

    def test_approved_specialized_actions_protect_sensitive_api_operations(self):
        admin = self.create_role_user('rbac-sensitive-actions-admin', AccessRole.Code.ADMIN)
        inactive_product = Product.objects.create(
            sku='RBAC-SENSITIVE-PUBLISH', name='Producto para publicación',
            category=self.category, price=Decimal('30000'), stock=1, active=False,
        )
        pending_order = Order.objects.create(customer=self.customer, shipping_address='Maicao')
        assignment_order = Order.objects.create(customer=self.customer, shipping_address='Riohacha')
        OrderItem.objects.create(order=assignment_order, product=self.product, quantity=1, unit_price=self.product.price)
        completed_order = Order.objects.create(
            customer=self.customer, shipping_address='Uribia', status=Order.Status.COMPLETED,
        )
        self.client.force_login(admin)

        published_product = self.client.patch(
            f'/api/v1/admin/products/{inactive_product.id}/', {'active': True},
            content_type='application/json',
        )
        unpublished_product = self.client.patch(
            f'/api/v1/admin/products/{inactive_product.id}/', {'active': False},
            content_type='application/json',
        )
        unpublished_category = self.client.patch(
            f'/api/v1/admin/categories/{self.category.id}/', {'active': False},
            content_type='application/json',
        )
        published_category = self.client.patch(
            f'/api/v1/admin/categories/{self.category.id}/', {'active': True},
            content_type='application/json',
        )
        approved_order = self.client.patch(
            f'/api/v1/admin/orders/{completed_order.id}/status/', {'status': Order.Status.PAID},
            content_type='application/json',
        )
        cancelled_order = self.client.patch(
            f'/api/v1/admin/orders/{pending_order.id}/status/', {'status': Order.Status.CANCELLED},
            content_type='application/json',
        )
        self.assertEqual(
            [published_product.status_code, unpublished_product.status_code,
             unpublished_category.status_code, published_category.status_code,
             approved_order.status_code, cancelled_order.status_code],
            [200, 200, 200, 200, 200, 200],
        )

        craft_user = self.create_role_user('rbac-sensitive-actions-craft', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora de asignación', active=True)
        self.client.force_login(admin)
        admin_assignment = self.client.post(f'/api/v1/craftswoman/orders/{assignment_order.id}/accept/')
        self.assertEqual(admin_assignment.status_code, 403)
        self.assertFalse(has_permission(admin, 'orders', 'assign'))

        self.client.force_login(craft_user)
        accepted_order = self.client.post(f'/api/v1/craftswoman/orders/{assignment_order.id}/accept/')
        self.assertEqual(accepted_order.status_code, 200, accepted_order.content)
        assignment_order.refresh_from_db()
        self.assertEqual(assignment_order.craftswoman_id, craftswoman.id)

    def test_role_matrix_loads_and_saves_for_all_editable_roles(self):
        superadmin = self.create_role_user('rbac-matrix-api-superadmin', AccessRole.Code.SUPERADMIN)
        admin = self.create_role_user('rbac-matrix-api-admin', AccessRole.Code.ADMIN)
        craftswoman = self.create_role_user('rbac-matrix-api-craft', AccessRole.Code.CRAFTSWOMAN)
        self.client.force_login(superadmin)
        users_by_role = {
            AccessRole.Code.ADMIN: admin,
            AccessRole.Code.CUSTOMER: self.user,
            AccessRole.Code.CRAFTSWOMAN: craftswoman,
        }

        for role_code in (AccessRole.Code.ADMIN, AccessRole.Code.CUSTOMER, AccessRole.Code.CRAFTSWOMAN):
            with self.subTest(role=role_code):
                url = f'/api/v1/admin/rbac/roles/{role_code}/permissions/'
                loaded = self.client.get(url)
                self.assertEqual(loaded.status_code, 200)
                self.assertEqual(
                    {(item['resource'], item['action']) for item in loaded.json()['permissions']},
                    {(item['resource'], item['action']) for item in permission_catalog()},
                )
                saved = self.client.put(url, {
                    'permissions': [{'resource': 'products', 'action': 'delete', 'allowed': True}],
                }, content_type='application/json')
                self.assertEqual(saved.status_code, 200)
                self.assertTrue(has_permission(users_by_role[role_code], 'products', 'delete'))

        superadmin_matrix = self.client.get('/api/v1/admin/rbac/roles/superadmin/permissions/')
        self.assertEqual(superadmin_matrix.status_code, 200)
        self.assertTrue(all(item['allowed'] for item in superadmin_matrix.json()['permissions']))
        rejected = self.client.put('/api/v1/admin/rbac/roles/superadmin/permissions/', {
            'permissions': [{'resource': 'products', 'action': 'delete', 'allowed': False}],
        }, content_type='application/json')
        self.assertEqual(rejected.status_code, 400)

    def test_superadmin_root_is_not_limited_by_individual_denies(self):
        superadmin = self.create_role_user('rbac-denied-superadmin', AccessRole.Code.SUPERADMIN)
        with self.assertRaises(DjangoPermissionDenied):
            set_user_permission(superadmin, superadmin, 'users', 'view', UserPermissionGrant.Effect.DENY)
        with self.assertRaises(DjangoPermissionDenied):
            set_user_permission(superadmin, superadmin, 'roles', 'view', UserPermissionGrant.Effect.DENY)
        self.client.force_login(superadmin)

        users_response = self.client.get('/api/v1/admin/users/')
        roles_response = self.client.get('/api/v1/admin/rbac/roles/admin/permissions/')
        django_admin_response = self.client.get('/admin/store/accessrole/')

        self.assertEqual(users_response.status_code, 200)
        self.assertEqual(roles_response.status_code, 200)
        self.assertEqual(django_admin_response.status_code, 200)

    def test_denied_permission_management_blocks_catalog_and_grant_api(self):
        superadmin = self.create_role_user('rbac-denied-permissions-superadmin', AccessRole.Code.SUPERADMIN)
        with self.assertRaises(DjangoPermissionDenied):
            set_user_permission(superadmin, superadmin, 'permissions', 'view', UserPermissionGrant.Effect.DENY)
        self.client.force_login(superadmin)
        catalog = self.client.get('/api/v1/admin/rbac/catalog/')
        self.assertEqual(catalog.status_code, 200)

        delegated_admin = self.create_role_user('rbac-permissions-denied-admin', AccessRole.Code.ADMIN)
        set_permission_delegation(superadmin, delegated_admin, 'products', 'view', True)
        set_user_permission(
            superadmin,
            delegated_admin,
            'permissions',
            'change',
            UserPermissionGrant.Effect.DENY,
        )
        self.client.force_login(delegated_admin)
        target_url = f'/api/v1/admin/rbac/users/{self.user.id}/permissions/'
        response = self.client.put(target_url, {
            'permissions': [{'resource': 'products', 'action': 'view', 'effect': 'deny'}],
        }, content_type='application/json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserPermissionGrant.objects.filter(
            user=self.user,
            permission=permission_for('products', 'view'),
        ).exists())

    def test_explicit_denies_are_enforced_by_rbac_mutation_services(self):
        superadmin = self.create_role_user('rbac-deny-services-superadmin', AccessRole.Code.SUPERADMIN)
        target = self.create_role_user('rbac-deny-services-target', AccessRole.Code.CUSTOMER)
        delegated_admin = self.create_role_user('rbac-deny-services-admin', AccessRole.Code.ADMIN)
        with self.assertRaises(DjangoPermissionDenied):
            set_user_permission(superadmin, superadmin, 'roles', 'change', UserPermissionGrant.Effect.DENY)
        set_role_permission(superadmin, AccessRole.Code.ADMIN, 'products', 'delete', True)
        self.assertTrue(RolePermission.objects.filter(
            role__code=AccessRole.Code.ADMIN,
            permission=permission_for('products', 'delete'),
        ).exists())

        with self.assertRaises(DjangoPermissionDenied):
            set_user_permission(superadmin, superadmin, 'role_assignments', 'change', UserPermissionGrant.Effect.DENY)
        self.assertTrue(has_permission(superadmin, 'role_assignments', 'change'))
        with self.assertRaises(DjangoPermissionDenied):
            assign_role(target, AccessRole.Code.SUPERADMIN, actor=target)
        self.assertEqual(target.access_profile.role.code, AccessRole.Code.CUSTOMER)

        with self.assertRaises(DjangoPermissionDenied):
            set_user_permission(superadmin, superadmin, 'delegations', 'add', UserPermissionGrant.Effect.DENY)
        set_permission_delegation(superadmin, delegated_admin, 'products', 'view', True)
        self.assertTrue(PermissionDelegation.objects.filter(permission=permission_for('products', 'view')).exists())

    def test_admin_role_demotion_revokes_delegations_and_individual_grants(self):
        superadmin = self.create_role_user('rbac-demotion-superadmin', AccessRole.Code.SUPERADMIN)
        admin = self.create_role_user('rbac-demotion-admin', AccessRole.Code.ADMIN)
        set_permission_delegation(superadmin, admin, 'products', 'view', True)
        set_user_permission(admin, self.user, 'products', 'view', UserPermissionGrant.Effect.ALLOW)
        permission = permission_for('products', 'view')
        self.assertTrue(has_permission(self.user, 'products', 'view'))
        self.client.force_login(superadmin)

        response = self.client.patch(
            f'/api/v1/admin/users/{admin.id}/role/',
            {'role': AccessRole.Code.CUSTOMER},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(has_permission(self.user, 'products', 'view'))
        self.assertFalse(UserPermissionGrant.objects.filter(user=self.user, permission=permission).exists())
        self.assertFalse(PermissionDelegation.objects.filter(admin=admin).exists())
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='revoke_user_permission',
            affected_user=self.user,
            details__reason='admin_scope_revoked',
        ).exists())

    def test_django_admin_delegation_delete_cascades_and_audits_user_grants(self):
        superadmin = self.create_role_user('rbac-deletion-superadmin', AccessRole.Code.SUPERADMIN)
        admin = self.create_role_user('rbac-deletion-admin', AccessRole.Code.ADMIN)
        set_permission_delegation(superadmin, admin, 'products', 'view', True)
        set_user_permission(admin, self.user, 'products', 'view', UserPermissionGrant.Effect.ALLOW)
        delegation = PermissionDelegation.objects.get(admin=admin, permission=permission_for('products', 'view'))
        request = RequestFactory().post('/admin/store/permissiondelegation/')
        request.user = superadmin
        model_admin = PermissionDelegationAdmin(PermissionDelegation, django_admin.site)

        model_admin.delete_model(request, delegation)

        self.assertFalse(PermissionDelegation.objects.filter(pk=delegation.pk).exists())
        self.assertFalse(UserPermissionGrant.objects.filter(user=self.user, granted_by=admin).exists())
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='revoke_user_permission',
            affected_user=self.user,
            details__reason='delegation_revoked',
        ).exists())

    def test_individual_deny_overrides_role_allow_and_blocks_admin_endpoint(self):
        admin = self.create_role_user('rbac-deny-admin', AccessRole.Code.ADMIN)
        permission = permission_for('products', 'view')
        self.assertTrue(RolePermission.objects.filter(role=admin.access_profile.role, permission=permission).exists())
        UserPermissionGrant.objects.create(
            user=admin,
            permission=permission,
            effect=UserPermissionGrant.Effect.DENY,
        )
        self.client.force_login(admin)

        self.assertFalse(has_permission(admin, 'products', 'view'))
        self.assertEqual(self.client.get('/api/v1/admin/products/').status_code, 403)

    def test_individual_allow_grants_catalogued_permission(self):
        superadmin = self.create_role_user('rbac-allow-superadmin', AccessRole.Code.SUPERADMIN)
        set_user_permission(superadmin, self.user, 'products', 'view', UserPermissionGrant.Effect.ALLOW)

        self.assertTrue(has_permission(self.user, 'products', 'view'))
        grant = UserPermissionGrant.objects.get(user=self.user, permission=permission_for('products', 'view'))
        self.assertEqual(grant.granted_by, superadmin)

    def test_admin_cannot_self_elevate_or_grant_without_delegation(self):
        admin = self.create_role_user('rbac-limited-admin', AccessRole.Code.ADMIN)

        with self.assertRaises(DjangoPermissionDenied):
            set_user_permission(admin, admin, 'users', 'add', UserPermissionGrant.Effect.ALLOW)
        with self.assertRaises(DjangoPermissionDenied):
            set_user_permission(admin, self.user, 'products', 'delete', UserPermissionGrant.Effect.ALLOW)

        self.assertFalse(UserPermissionGrant.objects.filter(user=admin).exists())
        self.assertTrue(AuditEvent.objects.filter(
            actor=admin,
            result=AuditEvent.Result.DENIED,
            action='set_user_permission',
        ).exists())

    def test_admin_can_manage_only_delegated_permission_for_customer(self):
        admin = self.create_role_user('rbac-delegated-admin', AccessRole.Code.ADMIN)
        superadmin = self.create_role_user('rbac-delegating-superadmin', AccessRole.Code.SUPERADMIN)
        set_permission_delegation(superadmin, admin, 'products', 'view', True)
        set_user_permission(admin, self.user, 'products', 'view', UserPermissionGrant.Effect.DENY)

        self.assertFalse(has_permission(self.user, 'products', 'view'))
        self.assertEqual(
            UserPermissionGrant.objects.get(user=self.user, permission=permission_for('products', 'view')).effect,
            UserPermissionGrant.Effect.DENY,
        )
        self.assertTrue(AuditEvent.objects.filter(
            actor=admin,
            affected_user=self.user,
            action='set_user_permission',
            result=AuditEvent.Result.SUCCESS,
        ).exists())

    def test_admin_cannot_create_or_assign_superadmin(self):
        admin = self.create_role_user('rbac-no-elevated-role-admin', AccessRole.Code.ADMIN)
        target = self.create_role_user('rbac-role-target', AccessRole.Code.CUSTOMER)

        with self.assertRaises(DjangoPermissionDenied):
            assign_role(target, AccessRole.Code.SUPERADMIN, actor=admin)

        self.client.force_login(admin)
        response = self.client.patch(
            f'/api/v1/admin/users/{target.id}/role/',
            {'role': AccessRole.Code.SUPERADMIN},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(target.access_profile.role.code, AccessRole.Code.CUSTOMER)
        self.assertTrue(AuditEvent.objects.filter(
            actor=admin,
            action='denied_patch',
            resource='role_assignments',
            result=AuditEvent.Result.DENIED,
        ).exists())

    def test_fixed_roles_cannot_be_deleted_or_renamed(self):
        role = AccessRole.objects.get(code=AccessRole.Code.CUSTOMER)

        with self.assertRaises(ValidationError):
            role.delete()
        role.code = 'new_customer'
        with self.assertRaises(ValidationError):
            role.save(update_fields=('code',))

    def test_sensitive_operations_write_immutable_audit_records(self):
        admin = self.create_role_user('rbac-audit-admin', AccessRole.Code.ADMIN)
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao, La Guajira')
        self.client.force_login(admin)
        response = self.client.patch(
            f'/api/v1/admin/orders/{order.id}/status/',
            {'status': Order.Status.PREPARING},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        event = AuditEvent.objects.get(action='change_order_status', object_id=str(order.id))
        self.assertEqual(event.actor, admin)
        self.assertEqual(event.affected_user, self.user)
        self.assertEqual(event.details, {'from': Order.Status.PENDING, 'to': Order.Status.PREPARING})
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()

    def test_superadmin_can_configure_role_permissions_and_admin_cannot(self):
        superadmin = self.create_role_user('rbac-role-api-superadmin', AccessRole.Code.SUPERADMIN)
        admin = self.create_role_user('rbac-role-api-admin', AccessRole.Code.ADMIN)
        url = '/api/v1/admin/rbac/roles/admin/permissions/'

        self.client.force_login(superadmin)
        global_access = self.client.get('/api/v1/admin/rbac/roles/superadmin/permissions/')
        self.assertEqual(global_access.status_code, 200)
        self.assertTrue(all(item['allowed'] for item in global_access.json()['permissions']))
        response = self.client.put(url, {
            'permissions': [{'resource': 'products', 'action': 'delete', 'allowed': True}],
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(has_permission(admin, 'products', 'delete'))

        self.client.force_login(admin)
        denied = self.client.put(url, {
            'permissions': [{'resource': 'products', 'action': 'delete', 'allowed': False}],
        }, content_type='application/json')
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(RolePermission.objects.filter(
            role=admin.access_profile.role,
            permission=permission_for('products', 'delete'),
        ).exists())
        self.assertTrue(AuditEvent.objects.filter(
            actor=admin,
            action='denied_put',
            result=AuditEvent.Result.DENIED,
        ).exists())

    def test_delegation_api_scopes_admin_user_permission_management(self):
        superadmin = self.create_role_user('rbac-delegation-api-superadmin', AccessRole.Code.SUPERADMIN)
        admin = self.create_role_user('rbac-delegation-api-admin', AccessRole.Code.ADMIN)
        delegation_url = '/api/v1/admin/rbac/delegations/'
        user_permissions_url = f'/api/v1/admin/rbac/users/{self.user.id}/permissions/'

        self.client.force_login(superadmin)
        delegated = self.client.post(delegation_url, {
            'admin_user_id': admin.id,
            'resource': 'products',
            'action': 'view',
            'allowed': True,
        }, content_type='application/json')
        self.assertEqual(delegated.status_code, 200)
        order_delegation = self.client.post(delegation_url, {
            'admin_user_id': admin.id,
            'resource': 'orders',
            'action': 'view',
            'allowed': True,
        }, content_type='application/json')
        self.assertEqual(order_delegation.status_code, 200)
        self.assertEqual(
            {(row['resource'], row['action']) for row in self.client.get(delegation_url).json()},
            {('products', 'view'), ('orders', 'view')},
        )

        self.client.force_login(admin)
        listed = self.client.get(user_permissions_url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            {(item['resource'], item['action']) for item in listed.json()['permissions']},
            {('orders', 'view'), ('products', 'view')},
        )
        updated = self.client.put(user_permissions_url, {
            'permissions': [{'resource': 'products', 'action': 'view', 'effect': 'deny'}],
        }, content_type='application/json')
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(has_permission(self.user, 'products', 'view'))

        out_of_scope = self.client.put(user_permissions_url, {
            'permissions': [{'resource': 'products', 'action': 'delete', 'effect': 'allow'}],
        }, content_type='application/json')
        self.assertEqual(out_of_scope.status_code, 403)
        self.assertTrue(AuditEvent.objects.filter(
            actor=admin,
            affected_user=self.user,
            action='set_user_permission',
            result=AuditEvent.Result.DENIED,
        ).exists())

    def test_navigation_and_session_permissions_follow_individual_deny(self):
        superadmin = self.create_role_user('rbac-navigation-superadmin', AccessRole.Code.SUPERADMIN)
        permission = permission_for('products', 'view')
        item = NavigationItem.objects.create(
            label='Gestión de productos',
            route_name='store:catalog',
            permission=permission,
        )
        item.roles.add(superadmin.access_profile.role)
        request = RequestFactory().get('/')
        request.user = superadmin

        visible = navigation_menu(request)['navigation_items']
        self.assertIn('Gestión de productos', [entry['label'] for entry in visible])
        self.assertIn('products.view', effective_permission_keys(superadmin))

        UserPermissionGrant.objects.create(
            user=superadmin,
            permission=permission,
            effect=UserPermissionGrant.Effect.DENY,
        )
        self.assertIn('products.view', effective_permission_keys(superadmin))
        visible_after_deny = navigation_menu(request)['navigation_items']
        self.assertIn('Gestión de productos', [entry['label'] for entry in visible_after_deny])

    def test_denied_individual_permissions_block_direct_html_requests(self):
        UserPermissionGrant.objects.create(
            user=self.user,
            permission=permission_for('cart', 'add'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        UserPermissionGrant.objects.create(
            user=self.user,
            permission=permission_for('designs', 'add'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        UserPermissionGrant.objects.create(
            user=self.user,
            permission=permission_for('orders', 'view'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        self.client.force_login(self.user)

        add_to_cart = self.client.post(f'/carrito/agregar/{self.product.id}/', {'quantity': 1})
        create_design = self.client.post('/disena-tu-manta/', {'size': 'M', 'quantity': 1})
        dashboard = self.client.get('/mi-cuenta/')

        self.assertEqual(add_to_cart.status_code, 403)
        self.assertEqual(create_design.status_code, 403)
        self.assertEqual(dashboard.status_code, 403)
        self.assertEqual(CustomDesign.objects.count(), 0)
        self.assertEqual(self.client.session.get('cart', {}), {})

    def test_craftswoman_deny_blocks_direct_html_order_acceptance(self):
        craft_user = self.create_role_user('rbac-html-craft-deny', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora con denegación')
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao, La Guajira')
        superadmin = self.create_role_user('rbac-html-craft-deny-root', AccessRole.Code.SUPERADMIN)
        set_user_permission(superadmin, craft_user, 'orders', 'assign', UserPermissionGrant.Effect.DENY)
        self.client.force_login(craft_user)

        response = self.client.post(f'/panel-tejedora/pedido/{order.id}/aceptar/')

        self.assertEqual(response.status_code, 403)
        order.refresh_from_db()
        self.assertIsNone(order.craftswoman_id)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertNotEqual(craftswoman.id, order.craftswoman_id)

    def test_html_order_assignment_status_audit_and_ownership_match_the_api(self):
        craft_user = self.create_role_user('html-order-workflow', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora HTML', active=True)
        other_craft_user = self.create_role_user('html-order-foreign-workflow', AccessRole.Code.CRAFTSWOMAN)
        other_craftswoman = Craftswoman.objects.create(
            user=other_craft_user, name='Tejedora HTML ajena', active=True,
        )
        available = Order.objects.create(customer=self.customer, shipping_address='Maicao')
        OrderItem.objects.create(
            order=available, product=self.product, quantity=1, unit_price=self.product.price,
        )
        foreign = Order.objects.create(
            customer=self.customer, craftswoman=other_craftswoman,
            status=Order.Status.ACCEPTED, shipping_address='Uribia',
        )
        self.client.force_login(craft_user)

        accepted = self.client.post(f'/panel-tejedora/pedido/{available.id}/aceptar/')
        invalid_html = self.client.post(
            f'/panel-tejedora/pedido/{available.id}/estado/',
            {'status': Order.Status.COMPLETED},
        )
        foreign_html = self.client.post(
            f'/panel-tejedora/pedido/{foreign.id}/estado/',
            {'status': Order.Status.WEAVING},
        )
        foreign_api = self.client.patch(
            f'/api/v1/craftswoman/orders/{foreign.id}/status/',
            {'status': Order.Status.WEAVING},
            content_type='application/json',
        )

        self.assertEqual(accepted.status_code, 302)
        available.refresh_from_db()
        self.assertEqual((available.craftswoman_id, available.status), (craftswoman.id, Order.Status.ACCEPTED))
        self.assertTrue(AuditEvent.objects.filter(
            action='accept_order', actor=craft_user, object_id=str(available.id),
            details__craftswoman_id=craftswoman.id,
        ).exists())
        self.assertEqual(invalid_html.status_code, 302)
        self.assertEqual(foreign_html.status_code, 404)
        self.assertEqual(foreign_api.status_code, 404)
        available.refresh_from_db()
        foreign.refresh_from_db()
        self.assertEqual(available.status, Order.Status.ACCEPTED)
        self.assertEqual(foreign.status, Order.Status.ACCEPTED)
        self.assertFalse(AuditEvent.objects.filter(
            action='craftswoman_change_order_status', object_id=str(available.id),
        ).exists())

        valid_html = self.client.post(
            f'/panel-tejedora/pedido/{available.id}/estado/',
            {'status': Order.Status.WEAVING},
        )
        self.assertEqual(valid_html.status_code, 302)
        available.refresh_from_db()
        self.assertEqual(available.status, Order.Status.WEAVING)
        self.assertTrue(AuditEvent.objects.filter(
            action='craftswoman_change_order_status', actor=craft_user,
            object_id=str(available.id), details__from=Order.Status.ACCEPTED,
            details__to=Order.Status.WEAVING,
        ).exists())

    def test_craftswoman_design_denies_protect_dashboard_and_order_acceptance(self):
        craft_user = self.create_role_user('rbac-craft-design-deny', AccessRole.Code.CRAFTSWOMAN)
        craftswoman = Craftswoman.objects.create(user=craft_user, name='Tejedora diseño deny')
        design = CustomDesign.objects.create(
            customer=self.customer,
            pattern='rombos',
            base_color='#112233',
            accent_color_one='#445566',
            accent_color_two='#778899',
            size='M',
            quantity=1,
            estimated_price=Decimal('120000'),
        )
        product = Product.objects.create(
            sku='RBAC-DESIGN-DENY',
            name='Diseño con permiso denegado',
            category=self.category,
            custom_design=design,
            price=Decimal('120000'),
            stock=1,
            active=False,
        )
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao, La Guajira')
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=product.price)
        UserPermissionGrant.objects.create(
            user=craft_user,
            permission=permission_for('designs', 'view'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        self.client.force_login(craft_user)

        dashboard = self.client.get('/api/v1/craftswoman/dashboard/')
        html_dashboard = self.client.get('/panel-tejedora/')
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()['designs'], [])
        self.assertEqual(html_dashboard.status_code, 200)

        UserPermissionGrant.objects.filter(user=craft_user).delete()
        UserPermissionGrant.objects.create(
            user=craft_user,
            permission=permission_for('designs', 'change'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        accepted = self.client.post(f'/api/v1/craftswoman/orders/{order.id}/accept/')
        self.assertEqual(accepted.status_code, 403)
        order.refresh_from_db()
        design.refresh_from_db()
        self.assertIsNone(order.craftswoman_id)
        self.assertIsNone(design.craftswoman_id)

    def test_cross_resource_denies_block_checkout_and_design_api(self):
        UserPermissionGrant.objects.create(
            user=self.user,
            permission=permission_for('customers', 'change'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.product.id): 1}
        session.save()
        order_count = Order.objects.count()
        checkout = self.client.post('/api/v1/checkout/', {
            'address': 'Calle 10 # 5-20',
            'city': 'Riohacha',
            'payment_method': 'contact',
        }, content_type='application/json')
        self.assertEqual(checkout.status_code, 403)
        self.assertEqual(Order.objects.count(), order_count)

        UserPermissionGrant.objects.create(
            user=self.user,
            permission=permission_for('cart', 'add'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        design = self.client.post('/api/v1/designs/', {
            'pattern': 'rombos',
            'base_color': '#112233',
            'accent_color_one': '#445566',
            'accent_color_two': '#778899',
            'size': 'M',
            'quantity': 1,
        }, content_type='application/json')
        self.assertEqual(design.status_code, 403)
        self.assertEqual(CustomDesign.objects.count(), 0)

    def test_permission_batch_with_out_of_scope_entry_has_no_partial_effect(self):
        superadmin = self.create_role_user('rbac-batch-superadmin', AccessRole.Code.SUPERADMIN)
        admin = self.create_role_user('rbac-batch-admin', AccessRole.Code.ADMIN)
        set_permission_delegation(superadmin, admin, 'products', 'view', True)
        permission = permission_for('products', 'view')
        self.client.force_login(admin)

        response = self.client.put(
            f'/api/v1/admin/rbac/users/{self.user.id}/permissions/',
            {'permissions': [
                {'resource': 'products', 'action': 'view', 'effect': 'deny'},
                {'resource': 'products', 'action': 'delete', 'effect': 'allow'},
            ]},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserPermissionGrant.objects.filter(user=self.user, permission=permission).exists())

    def test_superadmin_can_change_self_role_when_another_superadmin_remains(self):
        superadmin = self.create_role_user('rbac-self-change-superadmin', AccessRole.Code.SUPERADMIN)
        self.create_role_user('rbac-second-superadmin', AccessRole.Code.SUPERADMIN)
        self.client.force_login(superadmin)

        response = self.client.patch(
            f'/api/v1/admin/users/{superadmin.id}/role/',
            {'role': AccessRole.Code.ADMIN},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        superadmin.access_profile.refresh_from_db()
        self.assertEqual(superadmin.access_profile.role.code, AccessRole.Code.ADMIN)

    def test_last_superadmin_self_demotion_is_http_400_and_audited(self):
        superadmin = self.create_role_user('rbac-last-self-demotion', AccessRole.Code.SUPERADMIN)
        self.client.force_login(superadmin)

        response = self.client.patch(
            f'/api/v1/admin/users/{superadmin.id}/role/',
            {'role': AccessRole.Code.ADMIN},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        superadmin.access_profile.refresh_from_db()
        self.assertEqual(superadmin.access_profile.role.code, AccessRole.Code.SUPERADMIN)
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='assign_role',
            result=AuditEvent.Result.DENIED,
        ).exists())

    def test_user_role_admin_form_rejects_last_superadmin_demotion(self):
        superadmin = self.create_role_user('rbac-admin-form-superadmin', AccessRole.Code.SUPERADMIN)
        admin_role = AccessRole.objects.get(code=AccessRole.Code.ADMIN)
        form = ProtectedUserRoleForm(
            data={'user': superadmin.pk, 'role': admin_role.pk},
            instance=superadmin.access_profile,
        )

        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_order_item_inline_requires_order_rbac_not_native_item_permission(self):
        admin_user = self.create_role_user('rbac-order-inline-admin', AccessRole.Code.ADMIN)
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao, La Guajira')
        RolePermission.objects.filter(
            role=admin_user.access_profile.role,
            permission=permission_for('orders', 'change'),
        ).delete()
        order_item_permission = Permission.objects.get(
            content_type__app_label='store',
            codename='add_orderitem',
        )
        admin_user.user_permissions.add(order_item_permission)
        request = RequestFactory().get('/admin/store/order/')
        request.user = admin_user
        inline = OrderItemInline(Order, django_admin.site)

        self.assertFalse(inline.has_add_permission(request, order))


    def test_superadmin_can_create_update_and_delete_navigation_items(self):
        superadmin = self.create_role_user('rbac-navigation-superadmin', AccessRole.Code.SUPERADMIN)
        dynamic_role = AccessRole.objects.create(code='navigation_roundtrip', name='Rol dinámico de navegación')
        NavigationItem.objects.filter(route_name='customer.orders').delete()
        self.client.force_login(superadmin)
        create = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Mis pedidos',
            'route_name': 'customer.orders',
            'description': 'Consulta tus pedidos.',
            'role_codes': ['customer'],
            'permission_resource': 'orders',
            'permission_action': 'view',
            'order': 4,
            'active': True,
        }, content_type='application/json')
        self.assertEqual(create.status_code, 201)
        item_id = create.json()['id']
        self.assertEqual(create.json()['role_codes'], ['customer'])
        self.assertEqual(create.json()['permission_resource'], 'orders')
        created_again = next(item for item in self.client.get('/api/v1/admin/rbac/navigation/').json() if item['id'] == item_id)
        self.assertEqual(created_again['role_codes'], ['customer'])
        duplicate = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Pedidos duplicados', 'route_name': 'customer.orders', 'role_codes': ['admin'],
        }, content_type='application/json')
        self.assertEqual(duplicate.status_code, 400)

        update = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{item_id}/',
            {'label': 'Historial de pedidos', 'description': 'Compras guardadas.', 'active': False,
             'role_codes': ['customer', dynamic_role.code]},
            content_type='application/json',
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()['label'], 'Historial de pedidos')
        self.assertFalse(update.json()['active'])
        persisted = next(item for item in self.client.get('/api/v1/admin/rbac/navigation/').json() if item['id'] == item_id)
        self.assertEqual(persisted['label'], 'Historial de pedidos')
        self.assertEqual(persisted['description'], 'Compras guardadas.')
        self.assertFalse(persisted['active'])
        self.assertCountEqual(persisted['role_codes'], ['customer', dynamic_role.code])

        delete = self.client.delete(f'/api/v1/admin/rbac/navigation/{item_id}/')
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(NavigationItem.objects.filter(pk=item_id).exists())

    def test_role_navigation_is_independent_from_action_permissions(self):
        NavigationItem.objects.all().delete()
        craftswoman = self.create_role_user('role-menu-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        Craftswoman.objects.create(user=craftswoman, name='Tejedora del menú', active=True)
        Customer.objects.create(user=craftswoman, name='Cliente asociado', email=craftswoman.email)
        role = AccessRole.objects.get(code=AccessRole.Code.CRAFTSWOMAN)
        RolePermission.objects.get_or_create(role=role, permission=permission_for('products', 'view'))
        RolePermission.objects.get_or_create(role=role, permission=permission_for('orders', 'view'))
        visible_item = NavigationItem.objects.create(
            label='Mis tejidos',
            route_name='craftswoman.products',
            active=True,
            permission=permission_for('products', 'view'),
        )
        visible_item.roles.add(role)
        profile_item = NavigationItem.objects.create(
            label='Mi perfil', route_name='craftswoman.profile', active=True,
        )
        profile_item.roles.add(role)
        inactive_item = NavigationItem.objects.create(
            label='Panel oculto',
            route_name='craftswoman.dashboard',
            active=False,
        )
        inactive_item.roles.add(role)
        wrong_role_item = NavigationItem.objects.create(
            label='Pedidos de cliente',
            route_name='customer.orders',
            active=True,
        )
        wrong_role_item.roles.add(role)

        self.client.force_login(craftswoman)
        response = self.client.get('/api/v1/navigation/menu/')
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [item['route_name'] for item in response.json()],
            ['craftswoman.products', 'customer.orders', 'craftswoman.profile'],
        )
        own_orders = self.client.get('/api/v1/orders/')
        self.assertEqual(own_orders.status_code, 200)
        self.assertEqual(own_orders.json()['results'], [])

        UserPermissionGrant.objects.create(
            user=craftswoman,
            permission=permission_for('products', 'view'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        denied = self.client.get('/api/v1/navigation/menu/')
        self.assertEqual(denied.status_code, 200)
        self.assertCountEqual([item['route_name'] for item in denied.json()], ['customer.orders', 'craftswoman.profile'])
        self.assertEqual(self.client.get('/api/v1/craftswoman/products/').status_code, 403)

    def test_navigation_route_allowlist_accepts_dynamic_role_assignments(self):
        superadmin = self.create_role_user('role-menu-superadmin', AccessRole.Code.SUPERADMIN)
        dynamic_role = AccessRole.objects.create(code='orders_viewer', name='Consulta de pedidos')
        set_role_permission(superadmin, dynamic_role.code, 'orders', 'view', allowed=True)
        self.client.force_login(superadmin)
        invalid_route = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Ruta libre',
            'route_name': '/admin/secreto',
            'role_codes': ['admin'],
        }, content_type='application/json')
        self.assertEqual(invalid_route.status_code, 400)

        existing_view = NavigationItem.objects.filter(route_name='customer.orders').order_by('pk').first()
        self.assertIsNotNone(existing_view)
        routes = self.client.get('/api/v1/admin/rbac/navigation/routes/')
        customer_orders = next(route for route in routes.json() if route['value'] == 'customer.orders')
        self.assertIn(dynamic_role.code, customer_orders['role_codes'])
        admin_orders = next(route for route in routes.json() if route['value'] == 'admin.orders')
        self.assertIn(dynamic_role.code, admin_orders['role_codes'])
        self.assertIn(AccessRole.Code.CUSTOMER, admin_orders['role_codes'])
        for route in routes.json():
            if route['value'] == 'admin.access':
                self.assertIn(dynamic_role.code, route['role_codes'])
                self.assertEqual(
                    [permission['resource'] for permission in route['missing_permissions'][dynamic_role.code]],
                    ['roles'],
                )
            else:
                self.assertIn(dynamic_role.code, route['role_codes'])
        target = self.create_role_user('orders-viewer-menu-target', AccessRole.Code.CUSTOMER)
        assign_role(target, dynamic_role.code, actor=superadmin)
        Customer.objects.create(user=target, name='Cliente de auditoría', email=target.email)
        self.client.patch(
            f'/api/v1/admin/rbac/navigation/{existing_view.id}/',
            {'role_codes': [dynamic_role.code]}, content_type='application/json',
        )
        self.client.force_login(target)
        menu = self.client.get('/api/v1/navigation/menu/')
        self.assertIn('customer.orders', [item['route_name'] for item in menu.json()])
        own_orders = self.client.get('/api/v1/orders/')
        self.assertEqual(own_orders.status_code, 200)
        self.assertEqual(own_orders.json()['results'], [])
        self.client.force_login(superadmin)

        scope = self.client.put(f'/api/v1/admin/rbac/roles/{dynamic_role.code}/scopes/', {
            'scopes': [{'resource': 'orders', 'scope': 'all'}],
        }, content_type='application/json')
        self.assertEqual(scope.status_code, 200, scope.content)
        admin_orders_item = NavigationItem.objects.get(route_name='admin.orders')
        cross_role_view = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{admin_orders_item.id}/',
            {'role_codes': [dynamic_role.code]}, content_type='application/json',
        )
        self.assertEqual(cross_role_view.status_code, 200)
        self.assertEqual(cross_role_view.json()['role_codes'], [dynamic_role.code])
        self.client.force_login(target)
        assigned_admin_view = self.client.get('/api/v1/navigation/menu/')
        self.assertIn('admin.orders', [item['route_name'] for item in assigned_admin_view.json()])
        self.assertEqual(self.client.get('/api/v1/admin/orders/').status_code, 200)
        self.client.force_login(superadmin)
        dynamic_role.active = False
        dynamic_role.save(update_fields=('active',))
        routes = self.client.get('/api/v1/admin/rbac/navigation/routes/')
        customer_orders = next(route for route in routes.json() if route['value'] == 'customer.orders')
        self.assertNotIn(dynamic_role.code, customer_orders['role_codes'])
        admin_orders = next(route for route in routes.json() if route['value'] == 'admin.orders')
        self.assertNotIn(dynamic_role.code, admin_orders['role_codes'])
        inactive_assignment = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{admin_orders_item.id}/',
            {'role_codes': [dynamic_role.code]}, content_type='application/json',
        )
        self.assertEqual(inactive_assignment.status_code, 400)

    def test_navigation_assignment_supports_empty_set_and_role_removal_without_affecting_other_roles(self):
        superadmin = self.create_role_user('navigation-empty-root', AccessRole.Code.SUPERADMIN)
        dynamic_role = AccessRole.objects.create(code='navigation_editor_dynamic', name='Editor dinámico')
        set_role_permission(superadmin, dynamic_role.code, 'orders', 'view', allowed=True)
        dynamic_user = self.create_role_user('navigation-empty-dynamic-user', AccessRole.Code.CUSTOMER)
        Customer.objects.create(user=dynamic_user, name='Cliente dinámico', email=dynamic_user.email)
        customer_user = self.create_role_user('navigation-empty-customer-user', AccessRole.Code.CUSTOMER)
        assign_role(dynamic_user, dynamic_role.code, actor=superadmin)
        NavigationItem.objects.filter(route_name='craftswoman.inventory').delete()
        self.client.force_login(superadmin)
        hidden_create = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Inventario de tejedora', 'route_name': 'craftswoman.inventory', 'role_codes': [],
        }, content_type='application/json')
        self.assertEqual(hidden_create.status_code, 201, hidden_create.content)
        self.assertEqual(hidden_create.json()['role_codes'], [])

        item = NavigationItem.objects.get(route_name='customer.orders')

        assigned = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{item.id}/',
            {'role_codes': ['customer', dynamic_role.code]}, content_type='application/json',
        )
        self.assertEqual(assigned.status_code, 200, assigned.content)
        self.assertCountEqual(assigned.json()['role_codes'], ['customer', dynamic_role.code])
        persisted = next(row for row in self.client.get('/api/v1/admin/rbac/navigation/').json() if row['id'] == item.id)
        self.assertCountEqual(persisted['role_codes'], ['customer', dynamic_role.code])

        self.client.force_login(dynamic_user)
        self.assertIn('customer.orders', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.client.force_login(superadmin)
        removed_customer = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{item.id}/',
            {'role_codes': [dynamic_role.code]}, content_type='application/json',
        )
        self.assertEqual(removed_customer.status_code, 200, removed_customer.content)
        self.client.force_login(customer_user)
        self.assertNotIn('customer.orders', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.client.force_login(dynamic_user)
        self.assertIn('customer.orders', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])

        self.client.force_login(superadmin)
        removed_all = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{item.id}/',
            {'role_codes': []}, content_type='application/json',
        )
        self.assertEqual(removed_all.status_code, 200, removed_all.content)
        self.assertEqual(removed_all.json()['role_codes'], [])
        persisted = next(row for row in self.client.get('/api/v1/admin/rbac/navigation/').json() if row['id'] == item.id)
        self.assertEqual(persisted['role_codes'], [])
        self.client.force_login(dynamic_user)
        self.assertNotIn('customer.orders', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.client.force_login(customer_user)
        self.assertNotIn('craftswoman.inventory', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])

    def test_navigation_view_assignment_does_not_grant_action_or_api_access(self):
        customer = self.create_role_user('navigation-view-only-customer', AccessRole.Code.CUSTOMER)
        Customer.objects.create(user=customer, name='Cliente de navegación', email=customer.email)
        superadmin = self.create_role_user('navigation-view-only-root', AccessRole.Code.SUPERADMIN)
        set_role_permission(superadmin, AccessRole.Code.CUSTOMER, 'products', 'view', allowed=True)
        self.client.force_login(superadmin)
        existing_view = NavigationItem.objects.filter(route_name='admin.products').order_by('pk').first()
        self.assertIsNotNone(existing_view)
        scope = self.client.put('/api/v1/admin/rbac/roles/customer/scopes/', {
            'scopes': [{'resource': 'products', 'scope': 'all'}],
        }, content_type='application/json')
        self.assertEqual(scope.status_code, 200, scope.content)
        created = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{existing_view.id}/',
            {'role_codes': ['customer']}, content_type='application/json',
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()['role_codes'], ['customer'])
        self.client.force_login(customer)
        menu = self.client.get('/api/v1/navigation/menu/')
        direct_data = self.client.get('/api/v1/admin/products/')
        self.assertEqual(menu.status_code, 200)
        menu_routes = [item['route_name'] for item in menu.json()]
        self.assertIn('admin.products', menu_routes)
        self.assertIn('customer.orders', menu_routes)
        self.assertFalse(has_permission(customer, 'products', 'publish'))
        self.assertEqual(direct_data.status_code, 200)
        self.assertEqual(self.client.patch('/api/v1/admin/products/999999/', {'active': True}, content_type='application/json').status_code, 403)


    def test_non_superadmin_cannot_manage_navigation(self):
        admin_user = self.create_role_user('rbac-navigation-admin', AccessRole.Code.ADMIN)
        navigation_item = NavigationItem.objects.filter(route_name='customer.orders').first()
        self.assertIsNotNone(navigation_item)
        self.client.force_login(admin_user)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/navigation/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/navigation/routes/').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/admin/rbac/navigation/', {}, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.patch(
            f'/api/v1/admin/rbac/navigation/{navigation_item.id}/', {}, content_type='application/json',
        ).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/v1/admin/rbac/navigation/{navigation_item.id}/').status_code, 403)

    def test_superadmin_navigation_and_roles_work_through_bypass_without_grants(self):
        superadmin = self.create_role_user('rbac-navigation-bypass-root', AccessRole.Code.SUPERADMIN)
        role = superadmin.access_profile.role
        RBACGrant.objects.filter(role=role).delete()
        RolePermission.objects.filter(role=role).delete()
        superadmin.user_permissions.clear()
        NavigationItem.objects.filter(route_name='customer.profile').delete()
        self.client.force_login(superadmin)

        self.assertEqual(self.client.get('/api/v1/admin/rbac/navigation/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/navigation/routes/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200)
        created = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Mi perfil', 'route_name': 'customer.profile', 'role_codes': ['customer'],
        }, content_type='application/json')
        self.assertEqual(created.status_code, 201, created.content)
        updated = self.client.patch(
            f"/api/v1/admin/rbac/navigation/{created.json()['id']}/",
            {'label': 'Datos personales'}, content_type='application/json',
        )
        self.assertEqual(updated.status_code, 200, updated.content)

        access_item = NavigationItem.objects.get(route_name='admin.access')
        access_item.permission = permission_for('roles', 'view')
        access_item.save(update_fields=('permission',))
        RBACCapability.objects.filter(resource__code='roles', action__code='view').delete()
        menu = self.client.get('/api/v1/navigation/menu/')
        self.assertEqual(menu.status_code, 200)
        self.assertIn('admin.access', [item['route_name'] for item in menu.json()])

    def test_dynamic_roles_can_be_created_edited_assigned_and_deactivated(self):
        superadmin = self.create_role_user('dynamic-role-root', AccessRole.Code.SUPERADMIN)
        target = self.create_role_user('dynamic-role-target', AccessRole.Code.CUSTOMER)
        self.client.force_login(superadmin)

        created = self.client.post('/api/v1/admin/rbac/roles/', {
            'code': 'order_auditor', 'name': 'Auditor de pedidos', 'description': 'Consulta operativa.', 'priority': 12,
        }, content_type='application/json')
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.json()['code'], 'order_auditor')
        self.assertFalse(created.json()['system'])

        assigned = assign_role(target, 'order_auditor', actor=superadmin)
        self.assertEqual(assigned.code, 'order_auditor')
        changed = self.client.patch('/api/v1/admin/rbac/roles/order_auditor/', {
            'name': 'Auditor', 'description': 'Rol revisado.',
        }, content_type='application/json')
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertEqual(AccessRole.objects.get(code='order_auditor').name, 'Auditor')

        disabled = self.client.patch('/api/v1/admin/rbac/roles/order_auditor/', {'active': False}, content_type='application/json')
        self.assertEqual(disabled.status_code, 200, disabled.content)
        self.assertIsNone(role_for_user(target))
        self.assertTrue(UserRole.objects.filter(user=target, role__code='order_auditor').exists())
        reenabled = self.client.patch('/api/v1/admin/rbac/roles/order_auditor/', {'active': True}, content_type='application/json')
        self.assertEqual(reenabled.status_code, 200, reenabled.content)
        self.assertEqual(role_for_user(target).code, 'order_auditor')
        self.assertTrue(RolePermission.objects.filter(role__code='admin').exists())
        root_role = AccessRole.objects.get(code=AccessRole.Code.SUPERADMIN)
        root_role.active = False
        with self.assertRaises(ValidationError):
            root_role.save(update_fields=('active',))

    def test_dynamic_catalog_capabilities_and_user_deny_precedence(self):
        superadmin = self.create_role_user('dynamic-grants-root', AccessRole.Code.SUPERADMIN)
        target = self.create_role_user('dynamic-grants-target', AccessRole.Code.CUSTOMER)
        role = AccessRole.objects.create(code='workflow_reviewer', name='Revisor de flujo')
        assign_role(target, role.code, actor=superadmin)
        self.client.force_login(superadmin)

        resource = self.client.post('/api/v1/admin/rbac/resources/', {
            'code': 'shipping_docs', 'name': 'Documentos de envío', 'description': 'Recursos de expedición.',
        }, content_type='application/json')
        action = self.client.post('/api/v1/admin/rbac/actions/', {
            'code': 'dispatch', 'name': 'Despachar', 'description': 'Confirmar expedición autorizada.',
        }, content_type='application/json')
        self.assertEqual(resource.status_code, 201, resource.content)
        self.assertEqual(action.status_code, 201, action.content)
        capability = self.client.post('/api/v1/admin/rbac/capabilities/', {
            'resource': 'shipping_docs', 'action': 'dispatch',
        }, content_type='application/json')
        self.assertEqual(capability.status_code, 201, capability.content)
        set_role_permission(superadmin, role.code, 'orders', 'view', effect=RBACGrant.Effect.DENY)
        self.assertFalse(has_permission(target, 'orders', 'view'))
        set_user_permission(superadmin, target, 'orders', 'view', UserPermissionGrant.Effect.ALLOW)
        self.assertFalse(has_permission(target, 'orders', 'view'))
        self.assertNotIn('orders.view', effective_permission_keys(target))
        set_role_permission(superadmin, role.code, 'orders', 'view', effect=None)
        self.assertTrue(has_permission(target, 'orders', 'view'))
        self.assertIn('orders.view', effective_permission_keys(target))
        set_user_permission(superadmin, target, 'orders', 'view', UserPermissionGrant.Effect.DENY)
        self.assertFalse(has_permission(target, 'orders', 'view'))

        set_role_permission(superadmin, role.code, 'shipping_docs', 'dispatch', allowed=True)
        self.assertTrue(has_permission(target, 'shipping_docs', 'dispatch'))
        self.assertTrue(RBACCapability.objects.filter(resource__code='shipping_docs', action__code='dispatch').exists())

    def test_view_grant_does_not_grant_data_access_and_custom_role_keeps_row_isolation(self):
        superadmin = self.create_role_user('dynamic-view-root', AccessRole.Code.SUPERADMIN)
        target = self.create_role_user('dynamic-view-target', AccessRole.Code.CUSTOMER)
        Customer.objects.create(user=target, name='Cliente auditor', email=target.email)
        role = AccessRole.objects.create(code='order_auditor', name='Auditor')
        assign_role(target, role.code, actor=superadmin)
        set_role_permission(superadmin, role.code, 'orders', 'view', allowed=True)
        item = NavigationItem.objects.create(label='Pedidos', route_name='customer.orders')
        item.roles.add(role)
        customer = Customer.objects.get(user=self.user)
        order = Order.objects.create(customer=customer, shipping_address='Dirección privada')

        self.client.force_login(target)
        menu = self.client.get('/api/v1/navigation/menu/')
        self.assertEqual(menu.status_code, 200)
        self.assertEqual([row['label'] for row in menu.json()], ['Pedidos'])
        self.assertEqual(self.client.get('/api/v1/admin/orders/').status_code, 403)

        listing = self.client.get('/api/v1/orders/')
        detail = self.client.get(f'/api/v1/orders/{order.id}/')
        administrative_listing = self.client.get('/api/v1/admin/orders/')
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()['results'], [])
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(administrative_listing.status_code, 403)
        self.assertEqual(self.client.get('/mi-cuenta/').status_code, 403)

        self.client.force_login(superadmin)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/superadmin/scopes/').status_code, 200)
        root_scope_write = self.client.put('/api/v1/admin/rbac/roles/superadmin/scopes/', {
            'scopes': [{'resource': 'orders', 'scope': 'none'}],
        }, content_type='application/json')
        self.assertEqual(root_scope_write.status_code, 400)
        role_scope = self.client.put('/api/v1/admin/rbac/roles/order_auditor/scopes/', {
            'scopes': [{'resource': 'orders', 'scope': 'all'}],
        }, content_type='application/json')
        self.assertEqual(role_scope.status_code, 200, role_scope.content)
        self.client.force_login(target)
        self.assertEqual(self.client.get('/api/v1/admin/orders/').status_code, 200)

        self.client.force_login(superadmin)
        self.assertEqual(self.client.get(f'/api/v1/admin/rbac/users/{superadmin.id}/scopes/').status_code, 403)
        user_scope = self.client.put(f'/api/v1/admin/rbac/users/{target.id}/scopes/', {
            'scopes': [{'resource': 'orders', 'scope': 'none'}],
        }, content_type='application/json')
        self.assertEqual(user_scope.status_code, 200, user_scope.content)
        self.client.force_login(target)
        self.assertEqual(self.client.get('/api/v1/admin/orders/').status_code, 403)


    def test_dynamic_navigation_catalog_allows_admin_access_for_any_role_with_roles_view(self):
        root = self.create_role_user('navigation-catalog-root', AccessRole.Code.SUPERADMIN)
        admin_user = self.create_role_user('navigation-catalog-admin', AccessRole.Code.ADMIN)
        craftswoman_user = self.create_role_user('navigation-catalog-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        no_view_role = AccessRole.objects.create(code='roles_hidden', name='Sin consultar roles')
        set_role_permission(root, AccessRole.Code.ADMIN, 'roles', 'view', allowed=True)
        set_role_permission(root, AccessRole.Code.CRAFTSWOMAN, 'roles', 'view', allowed=True)
        self.client.force_login(root)
        response = self.client.get('/api/v1/admin/rbac/navigation/routes/')
        self.assertEqual(response.status_code, 200)
        root_route = next(route for route in response.json() if route['value'] == 'admin.access')
        self.assertEqual(
            set(root_route['role_codes']),
            set(AccessRole.objects.filter(active=True).values_list('code', flat=True)),
        )
        self.assertEqual(root_route['panel'], 'admin')
        self.assertEqual(root_route['section'], 'access')
        self.assertIsNone(root_route['django_url_name'])
        self.assertEqual(root_route['missing_permissions']['admin'], [])
        self.assertIn('admin.products', [route['value'] for route in response.json()])
        access_item = NavigationItem.objects.get(route_name='admin.access')
        self.assertIn('admin.access', [entry['route_name'] for entry in self.client.get('/api/v1/navigation/menu/').json()])
        self.assertCountEqual(
            access_item.roles.values_list('code', flat=True),
            [AccessRole.Code.SUPERADMIN, AccessRole.Code.ADMIN],
        )
        missing_view = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{access_item.id}/', {'role_codes': [no_view_role.code]},
            content_type='application/json',
        )
        self.assertEqual(missing_view.status_code, 200, missing_view.content)
        self.assertEqual(missing_view.json()['role_codes'], [no_view_role.code])
        craftswoman_profile_item = NavigationItem.objects.get(route_name='craftswoman.profile')
        self.assertEqual(list(craftswoman_profile_item.roles.values_list('code', flat=True)), [AccessRole.Code.CRAFTSWOMAN])
        NavigationItem.objects.filter(route_name='customer.profile').delete()
        renamed = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{access_item.id}/',
            {'route_name': 'customer.profile', 'role_codes': ['customer']}, content_type='application/json',
        )
        self.assertEqual(renamed.status_code, 400)
        disabled = self.client.patch(f'/api/v1/admin/rbac/navigation/{access_item.id}/', {'active': False}, content_type='application/json')
        self.assertEqual(disabled.status_code, 400)
        assigned = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{access_item.id}/', {'role_codes': ['superadmin', 'admin']}, content_type='application/json',
        )
        self.assertEqual(assigned.status_code, 200, assigned.content)
        incompatible = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{access_item.id}/', {'role_codes': ['superadmin', 'admin', 'craftswoman']}, content_type='application/json',
        )
        self.assertEqual(incompatible.status_code, 200, incompatible.content)
        self.assertIn('craftswoman', incompatible.json()['role_codes'])
        deleted = self.client.delete(f'/api/v1/admin/rbac/navigation/{access_item.id}/')
        self.assertEqual(deleted.status_code, 400)
        self.client.force_login(admin_user)
        self.assertIn('admin.access', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/admin/rbac/roles/', {
            'code': 'unapproved_role', 'name': 'Sin permiso de crear',
        }, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/navigation/routes/').status_code, 200)
        self.client.force_login(craftswoman_user)
        self.assertIn('admin.access', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200)

    def test_admin_access_assignment_grants_only_the_roles_view_screen_requirement(self):
        root = self.create_role_user('rbac-access-readonly-root', AccessRole.Code.SUPERADMIN)
        viewer = self.create_role_user('rbac-access-readonly-user', AccessRole.Code.CUSTOMER)
        Customer.objects.create(user=viewer, name='RBAC customer viewer', email=viewer.email)
        role = AccessRole.objects.create(code='roles_observer', name='Observador de roles')
        assign_role(viewer, role.code, actor=root)
        access_item = NavigationItem.objects.get(route_name='admin.access')
        access_item.roles.add(role)

        self.client.force_login(viewer)
        menu = self.client.get('/api/v1/navigation/menu/')
        self.assertEqual(menu.status_code, 200)
        self.assertNotIn('admin.access', [row['route_name'] for row in menu.json()])
        self.assertFalse(has_permission(viewer, 'roles', 'view'))
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 403)
        self.client.force_login(root)
        set_role_permission(root, role.code, 'roles', 'view', allowed=True)
        self.client.force_login(viewer)
        menu_with_view = self.client.get('/api/v1/navigation/menu/')
        self.assertEqual(menu_with_view.status_code, 200)
        self.assertIn('admin.access', [row['route_name'] for row in menu_with_view.json()])
        self.assertTrue(has_permission(viewer, 'roles', 'view'))
        self.assertFalse(has_permission(viewer, 'roles', 'create'))
        self.assertFalse(has_permission(viewer, 'permissions', 'edit'))
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/admin/rbac/roles/', {
            'code': 'forbidden_create', 'name': 'No autorizado',
        }, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.patch('/api/v1/admin/rbac/roles/admin/', {
            'description': 'No autorizado',
        }, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/admin/permissions/').status_code, 403)
        self.assertEqual(self.client.put('/api/v1/admin/rbac/roles/admin/permissions/', {
            'permissions': [{'resource': 'products', 'action': 'view', 'effect': 'deny'}],
        }, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/catalog/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/navigation/').status_code, 403)

        panel_user = self.create_role_user('rbac-access-custom-panel-user', AccessRole.Code.ADMIN)
        assign_role(panel_user, role.code, actor=root)
        self.client.force_login(panel_user)
        panel_menu = self.client.get('/api/v1/navigation/menu/')
        self.assertIn('admin.access', [row['route_name'] for row in panel_menu.json()])
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200)

    def test_categories_assignment_is_independent_of_data_and_crud_grants(self):
        root = self.create_role_user('category-assignment-root', AccessRole.Code.SUPERADMIN)
        admin_user = self.create_role_user('category-assignment-admin', AccessRole.Code.ADMIN)
        craftswoman_user = self.create_role_user('category-assignment-worker', AccessRole.Code.CRAFTSWOMAN)
        customer_user = self.create_role_user('category-assignment-customer', AccessRole.Code.CUSTOMER)
        Customer.objects.get_or_create(user=customer_user, defaults={'name': 'Assigned customer', 'email': customer_user.email})
        Craftswoman.objects.get_or_create(user=craftswoman_user, defaults={'name': 'Assigned weaver', 'active': True})
        custom_role = AccessRole.objects.create(code='category_viewer', name='Visor de categorías')
        custom_user = self.create_role_user('category-assignment-custom', AccessRole.Code.ADMIN)
        assign_role(custom_user, custom_role.code, actor=root)
        role_users = [
            (AccessRole.Code.ADMIN, admin_user),
            (AccessRole.Code.CRAFTSWOMAN, craftswoman_user),
            (AccessRole.Code.CUSTOMER, customer_user),
            (custom_role.code, custom_user),
        ]
        category_item = NavigationItem.objects.get(route_name='admin.categories')
        role_codes = [code for code, _target in role_users]
        permissions_before = {
            code: set(effective_permission_keys(target))
            for code, target in role_users
        }

        self.client.force_login(root)
        assigned = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{category_item.pk}/',
            {'role_codes': role_codes}, content_type='application/json',
        )
        self.assertEqual(assigned.status_code, 200, assigned.content)
        self.assertCountEqual(assigned.json()['role_codes'], role_codes)

        for code, target in role_users:
            self.assertEqual(set(effective_permission_keys(target)), permissions_before[code], code)
            self.client.force_login(target)
            menu = self.client.get('/api/v1/navigation/menu/')
            self.assertEqual(menu.status_code, 200, code)
            menu_routes = [row['route_name'] for row in menu.json()]
            can_view = has_permission(target, 'categories', 'view')
            self.assertEqual('admin.categories' in menu_routes, can_view, code)
            self.assertEqual(self.client.get('/api/v1/admin/categories/').status_code, 200 if can_view else 403, code)

        # A navigation assignment alone does not grant data access or CRUD.
        set_role_permission(root, custom_role.code, 'categories', 'view', allowed=True)
        existing = Category.objects.first()
        self.assertIsNotNone(existing)
        self.assertEqual(set(effective_permission_keys(custom_user)) - permissions_before[custom_role.code], {'categories.view'})
        self.client.force_login(custom_user)
        menu = self.client.get('/api/v1/navigation/menu/')
        self.assertIn('admin.categories', [row['route_name'] for row in menu.json()])
        self.assertEqual(self.client.get('/api/v1/admin/categories/').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/admin/categories/', {
            'name': 'No write category_viewer', 'description': '', 'active': True,
        }, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.patch(
            f'/api/v1/admin/categories/{existing.pk}/', {'name': 'No edit category_viewer'},
            content_type='application/json',
        ).status_code, 403)

        self.client.force_login(root)
        revoked = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{category_item.pk}/', {'role_codes': []}, content_type='application/json',
        )
        self.assertEqual(revoked.status_code, 200, revoked.content)
        self.assertEqual(revoked.json()['role_codes'], [])

    def test_admin_receives_five_read_only_rbac_tabs_and_catalog_menu_without_cross_role_leaks(self):
        root = self.create_role_user('admin-five-tabs-root', AccessRole.Code.SUPERADMIN)
        admin = self.create_role_user('admin-five-tabs', AccessRole.Code.ADMIN)
        craftswoman = self.create_role_user('admin-five-tabs-other-role', AccessRole.Code.CRAFTSWOMAN)
        self.client.force_login(root)
        root_menu = [item['route_name'] for item in self.client.get('/api/v1/navigation/menu/').json()]
        self.assertIn('store:catalog', root_menu)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200)

        self.client.force_login(admin)

        for resource in ('roles', 'users', 'navigation', 'permissions', 'audit'):
            self.assertTrue(has_permission(admin, resource, 'view'), f'{resource}.view should be granted to admin')
        self.assertFalse(has_permission(admin, 'users', 'edit'))
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/admin/permissions/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/catalog/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/navigation/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/navigation/routes/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/audit/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/admin/users/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/admin/users/{craftswoman.id}/').status_code, 200)

        menu_routes = [item['route_name'] for item in self.client.get('/api/v1/navigation/menu/').json()]
        self.assertIn('admin.access', menu_routes)
        self.assertIn('store:catalog', menu_routes)

        self.assertEqual(self.client.post('/api/v1/admin/users/', {}, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/v1/admin/users/{craftswoman.id}/', {}, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.put('/api/v1/admin/rbac/roles/admin/permissions/', {
            'permissions': [{'resource': 'products', 'action': 'view', 'effect': 'deny'}],
        }, content_type='application/json').status_code, 403)

        viewer_role = AccessRole.objects.create(code='five_tabs_roles_viewer', name='Solo vista de roles')
        viewer = self.create_role_user('five-tabs-no-data', AccessRole.Code.CUSTOMER)
        assign_role(viewer, viewer_role.code, actor=root)
        set_role_permission(root, viewer_role.code, 'roles', 'view', allowed=True)
        self.client.force_login(viewer)
        self.assertEqual(self.client.get('/api/v1/admin/users/').status_code, 403)

    def test_rbac_actions_are_checked_per_endpoint_and_grants_cannot_escalate(self):
        root = self.create_role_user('rbac-granular-root', AccessRole.Code.SUPERADMIN)
        manager = self.create_role_user('rbac-granular-manager', AccessRole.Code.CUSTOMER)
        manager_role = AccessRole.objects.create(code='limited_rbac_manager', name='Gestor RBAC limitado')
        target_role = AccessRole.objects.create(code='rbac_target', name='Rol objetivo')
        assign_role(manager, manager_role.code, actor=root)
        for resource, action in (
            ('roles', 'view'), ('roles', 'edit'),
            ('permissions', 'view'), ('permissions', 'edit'),
            ('products', 'view'),
        ):
            set_role_permission(root, manager_role.code, resource, action, allowed=True)
        access_item = NavigationItem.objects.get(route_name='admin.access')
        access_item.roles.add(manager_role)
        self.client.force_login(manager)

        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/admin/rbac/roles/', {
            'code': 'forbidden_create', 'name': 'No autorizado',
        }, content_type='application/json').status_code, 403)
        role_edit = self.client.patch('/api/v1/admin/rbac/roles/rbac_target/', {
            'description': 'Edición permitida',
        }, content_type='application/json')
        self.assertEqual(role_edit.status_code, 200, role_edit.content)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/rbac_target/permissions/').status_code, 200)
        matrix_write = self.client.put('/api/v1/admin/rbac/roles/rbac_target/permissions/', {
            'permissions': [{'resource': 'products', 'action': 'view', 'effect': 'allow'}],
        }, content_type='application/json')
        self.assertEqual(matrix_write.status_code, 200, matrix_write.content)
        escalated_matrix_write = self.client.put('/api/v1/admin/rbac/roles/rbac_target/permissions/', {
            'permissions': [{'resource': 'users', 'action': 'create', 'effect': 'allow'}],
        }, content_type='application/json')
        self.assertEqual(escalated_matrix_write.status_code, 403)
        self.assertFalse(has_permission(manager, 'users', 'create'))
        self.assertEqual(self.client.get('/api/v1/admin/rbac/resources/').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/admin/rbac/resources/', {
            'code': 'extra_resource', 'name': 'Recurso extra',
        }, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/rbac_target/scopes/').status_code, 403)

    def test_roles_edit_does_not_enable_role_creation_or_permission_matrix_changes(self):
        root = self.create_role_user('rbac-role-edit-only-root', AccessRole.Code.SUPERADMIN)
        editor = self.create_role_user('rbac-role-edit-only-user', AccessRole.Code.CUSTOMER)
        editor_role = AccessRole.objects.create(code='roles_editor_only', name='Editor de roles')
        target_role = AccessRole.objects.create(code='roles_edit_target', name='Rol editable')
        assign_role(editor, editor_role.code, actor=root)
        set_role_permission(root, editor_role.code, 'roles', 'view', allowed=True)
        set_role_permission(root, editor_role.code, 'roles', 'edit', allowed=True)
        NavigationItem.objects.get(route_name='admin.access').roles.add(editor_role)
        self.client.force_login(editor)

        changed = self.client.patch('/api/v1/admin/rbac/roles/roles_edit_target/', {
            'description': 'Cambio autorizado',
        }, content_type='application/json')
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertEqual(self.client.post('/api/v1/admin/rbac/roles/', {
            'code': 'roles_editor_created', 'name': 'No autorizado',
        }, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/roles_edit_target/permissions/').status_code, 403)
        self.assertEqual(self.client.put('/api/v1/admin/rbac/roles/roles_edit_target/permissions/', {
            'permissions': [{'resource': 'products', 'action': 'view', 'effect': 'deny'}],
        }, content_type='application/json').status_code, 403)

    def test_navigation_requires_role_view_grants_and_hides_revoked_or_out_of_scope_screens(self):
        root = self.create_role_user('navigation-requirements-root', AccessRole.Code.SUPERADMIN)
        target = self.create_role_user('navigation-requirements-user', AccessRole.Code.CUSTOMER)
        Customer.objects.create(user=target, name='Cliente de requisitos', email=target.email)
        role = AccessRole.objects.create(code='navigation_limited_auditor', name='Auditor limitado')
        assign_role(target, role.code, actor=root)
        NavigationItem.objects.filter(route_name='customer.orders').delete()
        self.client.force_login(root)

        create_without_view = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Pedidos de auditoría', 'route_name': 'customer.orders', 'role_codes': [role.code],
        }, content_type='application/json')
        self.assertEqual(create_without_view.status_code, 400)
        self.assertIn(
            'Para habilitar esta pantalla por favor conceda el permiso de la vista Mis pedidos de consultar',
            str(create_without_view.json()),
        )

        set_role_permission(root, role.code, 'orders', 'view', allowed=True)
        created = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Pedidos de auditoría', 'route_name': 'customer.orders', 'role_codes': [role.code],
        }, content_type='application/json')
        self.assertEqual(created.status_code, 201, created.content)
        self.client.force_login(target)
        self.assertIn('customer.orders', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.assertIn('orders.view', effective_permission_keys(target))
        self.assertNotIn('orders.edit', effective_permission_keys(target))

        self.client.force_login(root)
        set_role_permission(root, role.code, 'orders', 'view', effect=RBACGrant.Effect.DENY)
        self.client.force_login(target)
        self.assertNotIn('customer.orders', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.assertEqual(self.client.get('/api/v1/orders/').status_code, 403)

        set_role_permission(root, role.code, 'orders', 'view', allowed=True)
        item = NavigationItem.objects.get(route_name='admin.orders')
        self.client.force_login(root)
        assigned_admin_view = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{item.pk}/', {'role_codes': [role.code]}, content_type='application/json',
        )
        self.assertEqual(assigned_admin_view.status_code, 400, assigned_admin_view.content)
        self.client.force_login(target)
        self.assertNotIn('admin.orders', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.assertEqual(self.client.get('/api/v1/admin/orders/').status_code, 403)

        self.client.force_login(root)
        self.client.put(f'/api/v1/admin/rbac/roles/{role.code}/scopes/', {
            'scopes': [{'resource': 'orders', 'scope': 'all'}],
        }, content_type='application/json')
        assigned_admin_view = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{item.pk}/', {'role_codes': [role.code]}, content_type='application/json',
        )
        self.assertEqual(assigned_admin_view.status_code, 200, assigned_admin_view.content)
        self.client.force_login(target)
        self.assertIn('admin.orders', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.assertEqual(self.client.get('/api/v1/admin/orders/').status_code, 200)

        self.client.force_login(root)
        forbidden_access = self.client.patch(
            f"/api/v1/admin/rbac/navigation/{NavigationItem.objects.get(route_name='admin.access').pk}/",
            {'role_codes': [role.code]}, content_type='application/json',
        )
        self.assertEqual(forbidden_access.status_code, 200, forbidden_access.content)
        self.assertEqual(forbidden_access.json()['role_codes'], [role.code])
        self.client.force_login(target)
        self.assertNotIn('admin.access', [row['route_name'] for row in self.client.get('/api/v1/navigation/menu/').json()])
        self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 403)

    def test_navigation_route_registry_exposes_a_query_requirement_for_every_real_screen(self):
        root = self.create_role_user('navigation-registry-root', AccessRole.Code.SUPERADMIN)
        self.client.force_login(root)
        response = self.client.get('/api/v1/admin/rbac/navigation/routes/')
        self.assertEqual(response.status_code, 200)
        routes = response.json()
        expected_screens = {
            'store:catalog', 'customer.orders', 'customer.designs', 'customer.profile',
            'craftswoman.dashboard', 'craftswoman.products', 'craftswoman.inventory', 'craftswoman.orders', 'craftswoman.profile',
            'admin.dashboard', 'admin.products', 'admin.inventory', 'admin.orders', 'admin.categories', 'admin.access',
        }
        self.assertEqual({row['value'] for row in routes}, expected_screens)
        self.assertEqual(set(NAVIGATION_ROUTE_CATALOG), expected_screens)
        self.assertTrue(all(row['required_permissions'] for row in routes))
        self.assertIn('admin.access', {row['value'] for row in routes})
        self.assertEqual(
            {(row['value'], row['panel'], row['section']) for row in routes},
            {
                ('store:catalog', 'shared', 'catalog'),
                ('customer.orders', 'customer', 'orders'), ('customer.designs', 'customer', 'designs'), ('customer.profile', 'customer', 'profile'),
                ('craftswoman.dashboard', 'craftswoman', 'dashboard'), ('craftswoman.products', 'craftswoman', 'products'),
                ('craftswoman.inventory', 'craftswoman', 'inventory'), ('craftswoman.orders', 'craftswoman', 'orders'), ('craftswoman.profile', 'craftswoman', 'profile'),
                ('admin.dashboard', 'admin', 'dashboard'), ('admin.products', 'admin', 'products'), ('admin.inventory', 'admin', 'inventory'),
                ('admin.orders', 'admin', 'orders'), ('admin.categories', 'admin', 'categories'), ('admin.access', 'admin', 'access'),
            },
        )
        admin_products = next(row for row in routes if row['value'] == 'admin.products')
        self.assertEqual(admin_products['required_scopes'], [{'resource': 'products', 'scope': 'all'}])
        self.assertIsNone(admin_products['django_url_name'])
        self.assertEqual(next(row for row in routes if row['value'] == 'store:catalog')['django_url_name'], 'store:catalog')
        self.assertEqual(
            set(next(row for row in routes if row['value'] == 'admin.access')['role_codes']),
            set(AccessRole.objects.filter(active=True).values_list('code', flat=True)),
        )

    def test_navigation_write_rejects_missing_scopes_and_item_specific_permissions(self):
        root = self.create_role_user('navigation-preconditions-root', AccessRole.Code.SUPERADMIN)
        role = AccessRole.objects.create(code='navigation_preconditions', name='Revisor de acceso')
        set_role_permission(root, role.code, 'products', 'view', allowed=True)
        self.client.force_login(root)

        inventory_item = NavigationItem.objects.get(route_name='admin.products')
        missing_scope = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{inventory_item.pk}/', {'role_codes': [role.code]}, content_type='application/json',
        )
        self.assertEqual(missing_scope.status_code, 400, missing_scope.content)
        self.assertIn('Alcance requerido', str(missing_scope.json()))

        set_role_permission(root, role.code, 'products', 'view', allowed=True)
        self.client.put(f'/api/v1/admin/rbac/roles/{role.code}/scopes/', {
            'scopes': [{'resource': 'products', 'scope': 'all'}],
        }, content_type='application/json')
        assigned = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{inventory_item.pk}/', {'role_codes': [role.code]}, content_type='application/json',
        )
        self.assertEqual(assigned.status_code, 200, assigned.content)

        customer_orders = NavigationItem.objects.get(route_name='customer.orders')
        set_role_permission(root, role.code, 'orders', 'view', allowed=True)
        missing_optional = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{customer_orders.pk}/', {
                'role_codes': [role.code], 'permission_resource': 'orders', 'permission_action': 'edit',
            }, content_type='application/json',
        )
        self.assertEqual(missing_optional.status_code, 400, missing_optional.content)
        set_role_permission(root, role.code, 'orders', 'edit', allowed=True)
        granted_optional = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{customer_orders.pk}/', {
                'role_codes': [role.code], 'permission_resource': 'orders', 'permission_action': 'edit',
            }, content_type='application/json',
        )
        self.assertEqual(granted_optional.status_code, 200, granted_optional.content)

    def test_assigned_admin_routes_appear_for_authorized_base_and_custom_roles(self):
        root = self.create_role_user('navigation-panel-boundary-root', AccessRole.Code.SUPERADMIN)
        customer = self.create_role_user('navigation-panel-boundary-customer', AccessRole.Code.CUSTOMER)
        worker = self.create_role_user('navigation-panel-boundary-worker', AccessRole.Code.CRAFTSWOMAN)
        admin = self.create_role_user('navigation-panel-boundary-admin', AccessRole.Code.ADMIN)
        custom_role = AccessRole.objects.create(code='navigation_panel_reader', name='Lector de pantallas')
        custom = self.create_role_user('navigation-panel-boundary-custom', AccessRole.Code.ADMIN)
        assign_role(custom, custom_role.code, actor=root)
        Customer.objects.create(user=customer, name='Cliente panel', email=customer.email)
        Craftswoman.objects.create(user=worker, name='Tejedora panel', active=True)
        role_users = [
            (AccessRole.Code.SUPERADMIN, root),
            (AccessRole.Code.ADMIN, admin),
            (AccessRole.Code.CRAFTSWOMAN, worker),
            (AccessRole.Code.CUSTOMER, customer),
            (custom_role.code, custom),
        ]
        for role_code, _user in role_users:
            if role_code == AccessRole.Code.SUPERADMIN:
                continue
            set_role_permission(root, role_code, 'roles', 'view', allowed=True)
            set_role_permission(root, role_code, 'categories', 'view', allowed=True)

        access_item = NavigationItem.objects.get(route_name='admin.access')
        categories_item = NavigationItem.objects.get(route_name='admin.categories')
        role_codes = [role_code for role_code, _user in role_users]
        self.client.force_login(root)
        for item in (access_item, categories_item):
            assigned = self.client.patch(
                f'/api/v1/admin/rbac/navigation/{item.pk}/',
                {'role_codes': role_codes}, content_type='application/json',
            )
            self.assertEqual(assigned.status_code, 200, assigned.content)
            self.assertCountEqual(assigned.json()['role_codes'], role_codes)

        for role_code, user in role_users:
            self.client.force_login(user)
            menu = self.client.get('/api/v1/navigation/menu/')
            self.assertEqual(menu.status_code, 200, role_code)
            route_names = [row['route_name'] for row in menu.json()]
            self.assertIn('admin.access', route_names, role_code)
            self.assertIn('admin.categories', route_names, role_code)
            self.assertEqual(self.client.get('/api/v1/admin/rbac/roles/').status_code, 200, role_code)
            self.assertEqual(self.client.get('/api/v1/admin/categories/').status_code, 200, role_code)

        self.client.force_login(custom)
        self.assertEqual(self.client.post('/api/v1/admin/rbac/roles/', {
            'code': 'must_not_escalate', 'name': 'No autorizado',
        }, content_type='application/json').status_code, 403)
        category = Category.objects.first()
        self.assertIsNotNone(category)
        self.assertEqual(self.client.post('/api/v1/admin/categories/', {
            'name': 'No autorizado', 'description': '', 'active': True,
        }, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.patch(
            f'/api/v1/admin/categories/{category.pk}/', {'name': 'No autorizado'},
            content_type='application/json',
        ).status_code, 403)

        self.client.force_login(root)
        categories_item.active = False
        categories_item.save(update_fields=('active',))
        self.client.force_login(customer)
        inactive_menu = self.client.get('/api/v1/navigation/menu/')
        self.assertNotIn('admin.categories', [row['route_name'] for row in inactive_menu.json()])

        categories_item.active = True
        categories_item.save(update_fields=('active',))
        categories_item.roles.remove(custom_role)
        self.client.force_login(custom)
        unassigned_menu = self.client.get('/api/v1/navigation/menu/')
        self.assertNotIn('admin.categories', [row['route_name'] for row in unassigned_menu.json()])
        self.assertIn('admin.access', [row['route_name'] for row in unassigned_menu.json()])

        categories_item.roles.add(custom_role)
        self.client.force_login(root)
        root_menu = self.client.get('/api/v1/navigation/menu/').json()
        root_access = next(row for row in root_menu if row['route_name'] == 'admin.access')
        self.assertEqual((root_access['panel'], root_access['section']), ('admin', 'access'))

    def test_traditional_navigation_only_reverses_explicit_django_url_names(self):
        root = self.create_role_user('navigation-django-url-root', AccessRole.Code.SUPERADMIN)
        admin_orders = NavigationItem.objects.create(label='Pedidos administrativos', route_name='admin.orders')
        admin_orders.roles.add(root.access_profile.role)
        request = RequestFactory().get('/')
        request.user = root

        items = navigation_menu(request)['navigation_items']
        self.assertNotIn('admin.orders', [item['route_name'] for item in items])
        catalog_items = [item for item in items if item['route_name'] == 'store:catalog']
        self.assertTrue(catalog_items)
        self.assertTrue(all(item['url'].startswith('/') and item['panel'] == 'shared' and item['section'] == 'catalog' for item in catalog_items))

    def test_traditional_navigation_admin_requires_view_and_protects_admin_access(self):
        NavigationItem.objects.filter(route_name='customer.orders').delete()
        role = AccessRole.objects.create(code='navigation_admin_form', name='Editor de navegación')
        data = {
            'label': 'Mis pedidos', 'route_name': 'customer.orders', 'anchor': '', 'description': '',
            'roles': [role.pk], 'permission': '', 'order': '10', 'active': 'on',
        }
        form = NavigationItemAdminForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            'Para habilitar esta pantalla por favor conceda el permiso de la vista Mis pedidos de consultar',
            ' '.join(form.errors.get('roles', [])),
        )

        root = self.create_role_user('navigation-admin-form-root', AccessRole.Code.SUPERADMIN)
        set_role_permission(root, role.code, 'orders', 'view', allowed=True)
        valid_form = NavigationItemAdminForm(data=data)
        self.assertTrue(valid_form.is_valid(), valid_form.errors)

        data.update(label='Acceso RBAC', route_name='admin.access', roles=[role.pk])
        set_role_permission(root, role.code, 'roles', 'view', allowed=True)
        protected_form = NavigationItemAdminForm(data=data, instance=NavigationItem.objects.get(route_name='admin.access'))
        self.assertTrue(protected_form.is_valid(), protected_form.errors)
        craftswoman_role = AccessRole.objects.get(code=AccessRole.Code.CRAFTSWOMAN)
        set_role_permission(root, craftswoman_role.code, 'roles', 'view', allowed=True)
        data['roles'] = [craftswoman_role.pk]
        incompatible_form = NavigationItemAdminForm(
            data=data,
            instance=NavigationItem.objects.get(route_name='admin.access'),
        )
        self.assertTrue(incompatible_form.is_valid(), incompatible_form.errors)

    def test_checkout_assigns_each_order_item_and_notifies_product_craftswoman(self):
        assigned_user = self.create_role_user('line-assigned-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        assigned_worker = Craftswoman.objects.create(user=assigned_user, name='Tejedora asignada', active=True)
        other_user = self.create_role_user('line-other-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        other_worker = Craftswoman.objects.create(user=other_user, name='Otra tejedora', active=True)
        assigned_product = Product.objects.create(
            sku='LINE-ASSIGNED-001', name='Manta asignada', category=self.category,
            craftswoman=assigned_worker, price=Decimal('50000'), stock=2, active=True,
        )
        open_product = Product.objects.create(
            sku='LINE-OPEN-001', name='Manta disponible', category=self.category,
            price=Decimal('60000'), stock=2, active=True,
        )
        CustomerCartItem.objects.create(customer=self.customer, product=assigned_product, quantity=1)
        CustomerCartItem.objects.create(customer=self.customer, product=open_product, quantity=1)

        self.client.force_login(self.user)
        checkout = self.client.post('/api/v1/checkout/', {
            'address': 'Calle 1', 'city': 'Maicao', 'payment_method': 'contact',
        }, content_type='application/json')
        self.assertEqual(checkout.status_code, 201, checkout.content)
        order = Order.objects.get(pk=checkout.json()['id'])
        assigned_item = order.items.get(product=assigned_product)
        open_item = order.items.get(product=open_product)
        self.assertEqual(assigned_item.craftswoman_id, assigned_worker.id)
        self.assertIsNone(open_item.craftswoman_id)
        self.assertIsNone(order.craftswoman_id, 'Un pedido mixto no debe asignarse como un bloque a una sola tejedora.')
        self.assertTrue(InAppNotification.objects.filter(recipient=assigned_user, order_item=assigned_item).exists())

        self.client.force_login(other_user)
        dashboard = self.client.get('/api/v1/craftswoman/dashboard/').json()
        self.assertNotIn(assigned_item.id, [item['id'] for item in dashboard['available_items']])
        self.assertNotIn(assigned_item.id, [item['id'] for item in dashboard['assigned_items']])
        self.assertIn(open_item.id, [item['id'] for item in dashboard['available_items']])
        denied = self.client.post(f'/api/v1/craftswoman/work-items/{assigned_item.id}/accept/')
        self.assertEqual(denied.status_code, 403)

        self.client.force_login(assigned_user)
        accepted_assigned = self.client.post(f'/api/v1/craftswoman/work-items/{assigned_item.id}/accept/')
        self.assertEqual(accepted_assigned.status_code, 200, accepted_assigned.content)
        self.client.force_login(other_user)
        accepted_open = self.client.post(f'/api/v1/craftswoman/work-items/{open_item.id}/accept/')
        self.assertEqual(accepted_open.status_code, 200, accepted_open.content)
        order.refresh_from_db()
        self.assertIsNone(order.craftswoman_id)
        self.assertEqual(order.status, Order.Status.ACCEPTED)

        foreign_update = self.client.patch(
            f'/api/v1/craftswoman/work-items/{assigned_item.id}/status/',
            {'status': Order.Status.WEAVING}, content_type='application/json',
        )
        self.assertEqual(foreign_update.status_code, 404)
        traditional_foreign_claim = self.client.post(f'/panel-tejedora/trabajo/{assigned_item.id}/aceptar/')
        self.assertEqual(traditional_foreign_claim.status_code, 403)
        own_update = self.client.patch(
            f'/api/v1/craftswoman/work-items/{open_item.id}/status/',
            {'status': Order.Status.WEAVING}, content_type='application/json',
        )
        self.assertEqual(own_update.status_code, 200, own_update.content)
        self.assertEqual(order.items.get(pk=open_item.id).status, Order.Status.WEAVING)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.ACCEPTED, 'El seguimiento general queda en la etapa menos avanzada de sus partidas.')

        admin_user = self.create_role_user('mixed-order-supervisor', AccessRole.Code.ADMIN)
        self.client.force_login(admin_user)
        supervised = self.client.get('/api/v1/admin/orders/')
        self.assertEqual(supervised.status_code, 200, supervised.content)
        self.assertIn(order.id, [entry['id'] for entry in supervised.json()['results']])

class RBACProtectionTransactionTests(TransactionTestCase):
    def create_superadmin(self, username):
        user = User.objects.create_user(username=username, password='ClaveSegura2026!')
        role, _ = AccessRole.objects.get_or_create(
            code=AccessRole.Code.SUPERADMIN,
            defaults={
                'name': 'Superadministrador',
                'description': 'Control global de pruebas.',
                'priority': 1,
            },
        )
        UserRole.objects.create(user=user, role=role)
        return user

    def test_last_superadmin_cannot_be_demoted_or_assignment_deleted(self):
        user = self.create_superadmin('rbac-last-superadmin')
        assignment = user.access_profile
        assignment.role = AccessRole.objects.get(code=AccessRole.Code.ADMIN)

        with self.assertRaises(ValidationError):
            assignment.save()
        with self.assertRaises(ValidationError):
            assignment.delete()

    def test_superadmin_account_and_role_cannot_be_deactivated_or_deleted(self):
        user = self.create_superadmin('rbac-protected-superadmin')
        user.is_active = False
        with self.assertRaises(ValidationError):
            user.save(update_fields=('is_active',))
        with self.assertRaises(ValidationError):
            user.delete()

        role = AccessRole.objects.get(code=AccessRole.Code.SUPERADMIN)
        role.active = False
        with self.assertRaises(ValidationError):
            role.save(update_fields=('active',))
