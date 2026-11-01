from django.urls import NoReverseMatch, reverse

from .models import NavigationItem
from .rbac import has_permission, permission_key, role_for_user


def navigation_menu(request):
    """Entrega al layout solo las vistas configuradas para el rol actual."""
    role = role_for_user(request.user)
    if role is None:
        return {'navigation_items': [], 'current_access_role': None}

    items = []
    for item in NavigationItem.objects.filter(active=True, roles=role).select_related(
        'permission__content_type',
    ).distinct():
        if item.permission_id:
            key = permission_key(item.permission)
            if not key or not has_permission(request.user, *key):
                continue
        try:
            url = reverse(item.route_name)
        except NoReverseMatch:
            # La vista se mantiene editable sin hacer fallar el sitio si una ruta cambia.
            continue
        if item.anchor:
            url = f'{url}#{item.anchor}'
        items.append({'label': item.label, 'url': url, 'description': item.description, 'route_name': item.route_name})
    return {'navigation_items': items, 'current_access_role': role}
