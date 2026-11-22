from django.urls import reverse

from .models import Craftswoman, Customer, NavigationItem
from .rbac import has_permission, permission_key, record_scope_for, role_for_user


def navigation_menu(request):
    """Entrega al layout solo las vistas configuradas para el rol actual."""
    role = role_for_user(request.user)
    if role is None:
        return {'navigation_items': [], 'current_access_role': None}

    # Import at request time to avoid coupling the API module's route registry
    # to Django's template initialization order.
    from .api import NAVIGATION_ROUTE_CATALOG, navigation_requirements, navigation_role_codes, navigation_user_can_render_route

    items = []
    for item in NavigationItem.objects.filter(active=True, roles=role).distinct():
        route = NAVIGATION_ROUTE_CATALOG.get(item.route_name)
        if not route or role.code not in navigation_role_codes(item.route_name):
            continue
        if not navigation_user_can_render_route(request.user, role, item.route_name):
            continue
        if route['panel'] == 'customer' and role.code != 'customer' and not Customer.objects.filter(user=request.user).exists():
            continue
        if route['panel'] == 'craftswoman' and not Craftswoman.objects.filter(user=request.user, active=True).exists():
            continue
        if any(
            not has_permission(request.user, resource, action)
            for resource, action in navigation_requirements(item.route_name)
        ):
            continue
        if any(
            record_scope_for(request.user, resource) != 'all'
            for resource in route.get('all_scope', ())
        ):
            continue
        if item.permission_id:
            key = permission_key(item.permission)
            if not key:
                continue
            resource, action = key
            if not has_permission(request.user, resource, action):
                continue
        # Most registered names are React screen identifiers, not Django URL names.
        # Only routes explicitly mapped by the shared registry belong in templates.
        django_url_name = route.get('django_url_name')
        if not django_url_name:
            continue
        url = reverse(django_url_name)
        if item.anchor:
            url = f'{url}#{item.anchor}'
        items.append({
            'label': item.label,
            'url': url,
            'description': item.description,
            'route_name': item.route_name,
            'panel': route['panel'],
            'section': route['section'],
        })
    return {'navigation_items': items, 'current_access_role': role}
