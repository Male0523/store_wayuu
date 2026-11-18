from django.db import transaction

from .models import Customer, CustomerCartItem, Product


MAX_CART_QUANTITY = 100


def unresolved_legacy_cart_items(request):
    """Expose safe references for legacy session items that could not migrate."""
    legacy_cart = request.session.get('cart')
    if not isinstance(legacy_cart, dict):
        return []
    items = []
    for index, raw_key in enumerate(legacy_cart, start=1):
        key = str(raw_key)
        label = f'Producto anterior #{key}' if key.isdigit() else f'Elemento anterior {index}'
        items.append({'key': key, 'label': label})
    return items


def discard_unresolved_legacy_cart_item(request, key):
    """Remove only the selected leftover session entry, never a persisted row."""
    legacy_cart = request.session.get('cart')
    if not isinstance(legacy_cart, dict):
        return False
    missing = object()
    raw_key = next((item_key for item_key in legacy_cart if str(item_key) == key), missing)
    if raw_key is missing:
        return False
    del legacy_cart[raw_key]
    if legacy_cart:
        request.session['cart'] = legacy_cart
    else:
        request.session.pop('cart', None)
    request.session.modified = True
    return True


def merge_legacy_session_cart(request, customer):
    """Merge a pre-persistence session cart once into its authenticated owner."""
    legacy_cart = request.session.get('cart')
    if not isinstance(legacy_cart, dict):
        return

    remaining = {}
    with transaction.atomic():
        Customer.objects.select_for_update().get(pk=customer.pk)
        for raw_product_id, raw_quantity in legacy_cart.items():
            if not str(raw_product_id).isdigit():
                remaining[raw_product_id] = raw_quantity
                continue
            try:
                quantity = int(raw_quantity)
            except (TypeError, ValueError):
                remaining[raw_product_id] = raw_quantity
                continue
            if quantity < 1:
                remaining[raw_product_id] = raw_quantity
                continue
            product = Product.objects.select_related('custom_design').filter(pk=int(raw_product_id)).first()
            if not product:
                remaining[raw_product_id] = raw_quantity
                continue
            if product.custom_design_id and product.custom_design.customer_id != customer.id:
                remaining[raw_product_id] = raw_quantity
                continue
            quantity = 1 if product.custom_design_id else min(quantity, MAX_CART_QUANTITY)
            row = CustomerCartItem.objects.select_for_update().filter(
                customer=customer, product=product,
            ).first()
            if row:
                merged = 1 if product.custom_design_id else min(row.quantity + quantity, MAX_CART_QUANTITY)
                if row.quantity != merged:
                    row.quantity = merged
                    row.save(update_fields=('quantity', 'updated_at'))
            else:
                CustomerCartItem.objects.create(
                    customer=customer,
                    product=product,
                    quantity=quantity,
                )

    if remaining:
        request.session['cart'] = remaining
    else:
        request.session.pop('cart', None)
    request.session.modified = True
