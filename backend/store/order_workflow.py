"""Shared order and custom-design status rules for API and HTML actions."""

from .models import Order


ADMIN_ACTIVE_ORDER_STATUSES = (
    Order.Status.ACCEPTED,
    Order.Status.WEAVING,
    Order.Status.PREPARING,
    Order.Status.SHIPPED,
)


# These are the transitions already represented by the order and design flows:
# a pending order is accepted only through the assignment action; craftswomen
# may start, pause, and finish weaving; administrators perform fulfillment.
# The matrix retains Sprint 1's administrative fulfillment transitions.
ORDER_TRANSITION_ACTORS = {
    Order.Status.PENDING: {
        Order.Status.ACCEPTED: frozenset({'assignment'}),
        Order.Status.PREPARING: frozenset({'admin'}),
        Order.Status.CANCELLED: frozenset({'admin'}),
    },
    Order.Status.ACCEPTED: {
        Order.Status.WEAVING: frozenset({'craftswoman'}),
        Order.Status.PREPARING: frozenset({'admin'}),
        Order.Status.CANCELLED: frozenset({'admin'}),
    },
    Order.Status.WEAVING: {
        Order.Status.ACCEPTED: frozenset({'craftswoman'}),
        Order.Status.COMPLETED: frozenset({'craftswoman'}),
        Order.Status.PREPARING: frozenset({'admin'}),
        Order.Status.CANCELLED: frozenset({'admin'}),
    },
    Order.Status.COMPLETED: {
        Order.Status.PAID: frozenset({'admin'}),
        Order.Status.PREPARING: frozenset({'admin'}),
        Order.Status.CANCELLED: frozenset({'admin'}),
    },
    Order.Status.PAID: {
        Order.Status.PREPARING: frozenset({'admin'}),
        Order.Status.CANCELLED: frozenset({'admin'}),
    },
    Order.Status.PREPARING: {
        Order.Status.SHIPPED: frozenset({'admin'}),
        Order.Status.CANCELLED: frozenset({'admin'}),
    },
    Order.Status.SHIPPED: {
        Order.Status.DELIVERED: frozenset({'admin'}),
        Order.Status.CANCELLED: frozenset({'admin'}),
    },
    Order.Status.DELIVERED: {},
    Order.Status.CANCELLED: {},
}


def allowed_order_transitions(current_status, actor):
    """Return permitted next states for one actor according to the shared matrix."""
    return [
        next_status
        for next_status, actors in ORDER_TRANSITION_ACTORS.get(current_status, {}).items()
        if actor in actors
    ]


def can_transition_order(current_status, next_status, actor):
    return next_status in allowed_order_transitions(current_status, actor)


def has_custom_design_items(order):
    if 'items' in getattr(order, '_prefetched_objects_cache', {}):
        return any(item.product.custom_design_id for item in order.items.all())
    return order.items.filter(product__custom_design__isnull=False).exists()
