from django.urls import NoReverseMatch, reverse

from .models import AccessRole, NavigationItem, UserRole


def role_for_user(user):
    """Obtiene el rol persistente; crea uno inicial únicamente si falta."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        code = AccessRole.Code.SUPERADMIN
    elif user.is_staff:
        code = AccessRole.Code.ADMIN
    elif hasattr(user, 'craftswoman_profile'):
        code = AccessRole.Code.CRAFTSWOMAN
    else:
        code = AccessRole.Code.CUSTOMER

    role = AccessRole.objects.filter(code=code).first()
    if role is None:
        return None
    assignment, _ = UserRole.objects.get_or_create(user=user, defaults={'role': role})
    return assignment.role


def navigation_menu(request):
    """Entrega al layout solo las vistas configuradas para el rol actual."""
    role = role_for_user(request.user)
    if role is None:
        return {'navigation_items': [], 'current_access_role': None}

    items = []
    for item in NavigationItem.objects.filter(active=True, roles=role).distinct():
        try:
            url = reverse(item.route_name)
        except NoReverseMatch:
            # La vista se mantiene editable sin hacer fallar el sitio si una ruta cambia.
            continue
        if item.anchor:
            url = f'{url}#{item.anchor}'
        items.append({'label': item.label, 'url': url, 'description': item.description, 'route_name': item.route_name})
    return {'navigation_items': items, 'current_access_role': role}
