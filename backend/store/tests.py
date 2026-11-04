import json
import stat
from decimal import Decimal
from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib import admin as django_admin
from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from .navigation import navigation_menu
from .admin import (
    CategoryAdmin,
    CraftswomanAdmin,
    CustomerAdmin,
    CustomDesignAdmin,
    OrderAdmin,
    OrderItemInline,
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
    PERMISSION_ACTIONS,
    PERMISSION_RESOURCES,
    assign_role,
    effective_permission_keys,
    has_permission,
    permission_catalog,
    permission_for,
    set_permission_delegation,
    set_role_permission,
    set_user_permission,
)


class StoreAPITests(TestCase):
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
            'phone': '3009876543',
            'address': 'Calle 12 # 4-10',
            'city': 'Maicao',
        }, content_type='application/json')

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['name'], 'Cliente Actualizado')
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


    def test_admin_can_manage_products_and_order_status(self):
        admin = self.create_role_user('admin-api', AccessRole.Code.ADMIN)
        order = Order.objects.create(customer=self.customer, shipping_address='Maicao, La Guajira')
        self.client.force_login(admin)

        created = self.client.post('/api/v1/admin/products/', {
            'sku': 'API-ADMIN-001',
            'name': 'Manta administrada',
            'category': self.category.id,
            'price': '40000',
            'stock': 3,
        }, content_type='application/json')
        updated = self.client.patch(
            f'/api/v1/admin/products/{self.product.id}/',
            {'price': '31000', 'stock': 8, 'active': False},
            content_type='application/json',
        )
        order_status = self.client.patch(
            f'/api/v1/admin/orders/{order.id}/status/',
            {'status': Order.Status.PREPARING},
            content_type='application/json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['sku'], 'API-ADMIN-001')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['stock'], 8)
        self.assertFalse(updated.json()['active'])
        self.assertEqual(order_status.status_code, 200)
        self.assertEqual(order_status.json()['status'], Order.Status.PREPARING)

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

        self.assertEqual(response.status_code, 400)
        self.assertTrue(AccessRole.objects.get(code=AccessRole.Code.CUSTOMER).active)
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            action='deactivate_role',
            result=AuditEvent.Result.DENIED,
        ).exists())

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

        for non_superadmin in (self.user, admin, craft_active):
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
        expected_pairs = {
            (resource, action)
            for resource in PERMISSION_RESOURCES
            for action in PERMISSION_ACTIONS
        }
        catalog_pairs = {(item['resource'], item['action']) for item in catalog}

        self.assertEqual(catalog_pairs, expected_pairs)
        self.assertTrue(all(permission_for(resource, action) for resource, action in expected_pairs))

        expected_by_role = {
            AccessRole.Code.SUPERADMIN: expected_pairs,
            AccessRole.Code.ADMIN: {
                ('products', 'view'), ('products', 'add'), ('products', 'change'),
                ('categories', 'view'), ('categories', 'add'), ('categories', 'change'),
                ('orders', 'view'), ('orders', 'change'),
            },
            AccessRole.Code.CUSTOMER: {
                ('customers', 'view'), ('customers', 'change'),
                ('orders', 'view'), ('orders', 'add'),
                ('designs', 'view'), ('designs', 'add'),
                ('cart', 'view'), ('cart', 'add'), ('cart', 'change'), ('cart', 'delete'),
            },
            AccessRole.Code.CRAFTSWOMAN: {
                ('products', 'view'), ('products', 'add'), ('products', 'change'),
                ('orders', 'view'), ('orders', 'change'),
                ('designs', 'view'), ('designs', 'change'),
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

    def test_individual_deny_restricts_superadmin_api_and_django_admin(self):
        superadmin = self.create_role_user('rbac-denied-superadmin', AccessRole.Code.SUPERADMIN)
        set_user_permission(superadmin, superadmin, 'users', 'view', UserPermissionGrant.Effect.DENY)
        set_user_permission(superadmin, superadmin, 'roles', 'view', UserPermissionGrant.Effect.DENY)
        set_user_permission(superadmin, superadmin, 'roles', 'change', UserPermissionGrant.Effect.DENY)
        self.client.force_login(superadmin)

        users_response = self.client.get('/api/v1/admin/users/')
        roles_response = self.client.get('/api/v1/admin/rbac/roles/admin/permissions/')
        django_admin_response = self.client.get('/admin/store/accessrole/')

        self.assertEqual(users_response.status_code, 403)
        self.assertEqual(roles_response.status_code, 403)
        self.assertEqual(django_admin_response.status_code, 403)
        self.assertTrue(AuditEvent.objects.filter(
            actor=superadmin,
            result=AuditEvent.Result.DENIED,
            action='denied_get',
        ).exists())

    def test_denied_permission_management_blocks_catalog_and_grant_api(self):
        superadmin = self.create_role_user('rbac-denied-permissions-superadmin', AccessRole.Code.SUPERADMIN)
        set_user_permission(
            superadmin,
            superadmin,
            'permissions',
            'view',
            UserPermissionGrant.Effect.DENY,
        )
        self.client.force_login(superadmin)
        catalog = self.client.get('/api/v1/admin/rbac/catalog/')
        self.assertEqual(catalog.status_code, 403)

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
        set_user_permission(
            superadmin,
            superadmin,
            'roles',
            'change',
            UserPermissionGrant.Effect.DENY,
        )
        with self.assertRaises(DjangoPermissionDenied):
            set_role_permission(superadmin, AccessRole.Code.ADMIN, 'products', 'delete', True)
        self.assertFalse(RolePermission.objects.filter(
            role__code=AccessRole.Code.ADMIN,
            permission=permission_for('products', 'delete'),
        ).exists())

        set_user_permission(
            superadmin,
            superadmin,
            'role_assignments',
            'change',
            UserPermissionGrant.Effect.DENY,
        )
        with self.assertRaises(DjangoPermissionDenied):
            assign_role(target, AccessRole.Code.SUPERADMIN, actor=superadmin)
        self.assertEqual(target.access_profile.role.code, AccessRole.Code.CUSTOMER)

        set_user_permission(
            superadmin,
            superadmin,
            'delegations',
            'add',
            UserPermissionGrant.Effect.DENY,
        )
        with self.assertRaises(DjangoPermissionDenied):
            set_permission_delegation(superadmin, target, 'products', 'view', True)
        self.assertFalse(PermissionDelegation.objects.filter(permission=permission_for('products', 'view')).exists())

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
        self.assertNotIn('products.view', effective_permission_keys(superadmin))
        hidden = navigation_menu(request)['navigation_items']
        self.assertNotIn('Gestión de productos', [entry['label'] for entry in hidden])

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
        UserPermissionGrant.objects.create(
            user=craft_user,
            permission=permission_for('orders', 'change'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        self.client.force_login(craft_user)

        response = self.client.post(f'/panel-tejedora/pedido/{order.id}/aceptar/')

        self.assertEqual(response.status_code, 403)
        order.refresh_from_db()
        self.assertIsNone(order.craftswoman_id)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertNotEqual(craftswoman.id, order.craftswoman_id)

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
        self.assertEqual(html_dashboard.status_code, 403)

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

        update = self.client.patch(
            f'/api/v1/admin/rbac/navigation/{item_id}/',
            {'label': 'Historial de pedidos', 'active': False},
            content_type='application/json',
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()['label'], 'Historial de pedidos')
        self.assertFalse(update.json()['active'])

        delete = self.client.delete(f'/api/v1/admin/rbac/navigation/{item_id}/')
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(NavigationItem.objects.filter(pk=item_id).exists())

    def test_role_navigation_endpoint_filters_by_role_and_effective_permissions(self):
        craftswoman = self.create_role_user('role-menu-craftswoman', AccessRole.Code.CRAFTSWOMAN)
        role = AccessRole.objects.get(code=AccessRole.Code.CRAFTSWOMAN)
        RolePermission.objects.get_or_create(role=role, permission=permission_for('products', 'view'))
        visible_item = NavigationItem.objects.create(
            label='Mis tejidos',
            route_name='craftswoman.products',
            active=True,
        )
        visible_item.roles.add(role)
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
        self.assertEqual([item['route_name'] for item in response.json()], ['craftswoman.products'])

        UserPermissionGrant.objects.create(
            user=craftswoman,
            permission=permission_for('products', 'view'),
            effect=UserPermissionGrant.Effect.DENY,
        )
        denied = self.client.get('/api/v1/navigation/menu/')
        self.assertEqual(denied.status_code, 200)
        self.assertEqual(denied.json(), [])

    def test_navigation_route_allowlist_rejects_arbitrary_routes_and_wrong_roles(self):
        superadmin = self.create_role_user('role-menu-superadmin', AccessRole.Code.SUPERADMIN)
        self.client.force_login(superadmin)
        invalid_route = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Ruta libre',
            'route_name': '/admin/secreto',
            'role_codes': ['admin'],
        }, content_type='application/json')
        self.assertEqual(invalid_route.status_code, 400)

        invalid_role = self.client.post('/api/v1/admin/rbac/navigation/', {
            'label': 'Pantalla de cliente',
            'route_name': 'customer.orders',
            'role_codes': ['admin'],
        }, content_type='application/json')
        self.assertEqual(invalid_role.status_code, 400)

    def test_non_superadmin_cannot_manage_navigation(self):
        admin_user = self.create_role_user('rbac-navigation-admin', AccessRole.Code.ADMIN)
        self.client.force_login(admin_user)
        response = self.client.get('/api/v1/admin/rbac/navigation/')
        self.assertEqual(response.status_code, 403)

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