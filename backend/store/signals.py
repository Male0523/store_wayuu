from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from .models import AccessRole, UserRole, revoke_admin_scope


@receiver(pre_save, sender=User)
def protect_superadmin_account_on_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    assignment = UserRole.objects.select_related('role').filter(
        user_id=instance.pk,
    ).first()
    if assignment and assignment.role.code == AccessRole.Code.SUPERADMIN and not instance.is_active:
        raise ValidationError('La cuenta superadmin protegida no se puede desactivar.')
    if (
        assignment
        and assignment.role.code == AccessRole.Code.ADMIN
        and assignment.user.is_active
        and not instance.is_active
    ):
        revoke_admin_scope(instance.pk)


@receiver(pre_delete, sender=User)
def protect_superadmin_account_on_delete(sender, instance, **kwargs):
    assignment = UserRole.objects.select_related('role').filter(
        user_id=instance.pk,
    ).first()
    if assignment and assignment.role.code == AccessRole.Code.SUPERADMIN:
        raise ValidationError('La cuenta superadmin protegida no se puede eliminar.')
    if assignment and assignment.role.code == AccessRole.Code.ADMIN:
        revoke_admin_scope(instance.pk)
