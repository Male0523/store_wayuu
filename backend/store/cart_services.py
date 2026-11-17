from django.db import transaction

from .models import Customer, CustomerCartItem, Product


MAX_CART_QUANTITY = 100


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
