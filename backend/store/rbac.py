from .models import AccessRole, UserRole


def role_for_user(user):
    """Returns only the persisted role assignment; missing assignments fail closed."""
    if not user or not user.is_authenticated:
        return None
    assignment = UserRole.objects.select_related('role').filter(user_id=user.pk).first()
    return assignment.role if assignment else None


def assign_role(user, role_code):
    """Assigns an existing role and lets UserRole synchronize Django staff flags."""
    role = AccessRole.objects.get(code=role_code)
    assignment, _ = UserRole.objects.update_or_create(user=user, defaults={'role': role})
    return assignment.role


def has_role(user, *role_codes):
    role = role_for_user(user)
    return role is not None and role.code in role_codes