from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from .models import Craftswoman, CustomDesign, Category, Customer, Order, OrderItem, Product


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
        admin = User.objects.create_superuser(
            username='admin-api',
            email='admin-api@example.com',
            password='ClaveSegura2026!',
        )
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
        admin = User.objects.create_superuser(
            username='admin-category-api',
            email='admin-category-api@example.com',
            password='ClaveSegura2026!',
        )
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
        self.assertIn(self.client.get('/api/v1/cart/').status_code, (401, 403))
        self.assertIn(self.client.get('/api/v1/orders/').status_code, (401, 403))

    def test_cart_rejects_quantity_above_stock(self):
        self.client.force_login(self.user)
        response = self.client.post('/api/v1/cart/items/', {
            'product_id': self.product.id,
            'quantity': 5,
        }, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get('/api/v1/cart/').json()['count'], 0)