from django.urls import path

from . import api

app_name = 'api'

urlpatterns = [
    path('', api.api_health, name='health'),
    path('csrf/', api.csrf_cookie, name='csrf'),
    path('categories/', api.CategoryListView.as_view(), name='categories'),
    path('products/', api.ProductListView.as_view(), name='products'),
    path('products/<int:product_id>/', api.ProductDetailView.as_view(), name='product-detail'),
    path('admin/categories/', api.AdminCategoryListView.as_view(), name='admin-categories'),
    path('admin/categories/<int:category_id>/', api.AdminCategoryDetailView.as_view(), name='admin-category-detail'),
    path('admin/products/', api.AdminProductListView.as_view(), name='admin-products'),
    path('admin/products/<int:product_id>/', api.AdminProductDetailView.as_view(), name='admin-product-detail'),
    path('admin/orders/<int:order_id>/status/', api.AdminOrderStatusView.as_view(), name='admin-order-status'),
    path('auth/register/', api.CustomerRegistrationView.as_view(), name='register'),
    path('auth/register/craftswoman/', api.CraftswomanRegistrationView.as_view(), name='register-craftswoman'),
    path('auth/login/', api.LoginView.as_view(), name='login'),
    path('auth/logout/', api.LogoutView.as_view(), name='logout'),
    path('auth/me/', api.CurrentUserView.as_view(), name='me'),
    path('profile/', api.CustomerProfileView.as_view(), name='profile'),
    path('cart/', api.CartView.as_view(), name='cart'),
    path('cart/items/', api.CartItemListView.as_view(), name='cart-items'),
    path('cart/items/<int:product_id>/', api.CartItemDetailView.as_view(), name='cart-item-detail'),
    path('checkout/', api.CheckoutView.as_view(), name='checkout'),
    path('orders/', api.OrderListView.as_view(), name='orders'),
    path('orders/<int:order_id>/', api.OrderDetailView.as_view(), name='order-detail'),
    path('designs/', api.CustomDesignListView.as_view(), name='designs'),
    path('craftswoman/dashboard/', api.CraftswomanDashboardView.as_view(), name='craftswoman-dashboard'),
    path('craftswoman/orders/<int:order_id>/accept/', api.AcceptOrderView.as_view(), name='accept-order'),
    path('craftswoman/orders/<int:order_id>/status/', api.CraftswomanOrderStatusView.as_view(), name='order-status'),
    path('craftswoman/designs/<int:design_id>/status/', api.CraftswomanDesignStatusView.as_view(), name='design-status'),
]