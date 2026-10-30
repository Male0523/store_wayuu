import json
import stat
from decimal import Decimal
from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import AccessRole, Craftswoman, CustomDesign, Category, Customer, Order, OrderItem, Product, UserRole


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
        self.assertEqual(self.client.get(f'/pedido-confirmado/{foreign_assigned_order.id}/').status_code, 403)

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