from typing import Type

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django_rest_passwordreset.signals import reset_password_token_created

from apps.users.models import ConfirmEmailToken, User


new_user_registered = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправляет пользователю письмо с токеном для сброса пароля.
    """

    msg = EmailMultiAlternatives(
        subject=f"Токен сброса пароля для {reset_password_token.user}",
        body=reset_password_token.key,
        from_email=settings.EMAIL_HOST_USER,
        to=[reset_password_token.user.email],
    )
    msg.send()


@receiver(post_save, sender=User)
def new_user_registered_signal(
    sender: Type[User], instance: User, created: bool, **kwargs
):
    """
    Отправляет письмо с токеном подтверждения email при регистрации нового пользователя.
    """
    if created and not instance.is_active:
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)

        msg = EmailMultiAlternatives(
            subject=f"Подтверждение регистрации Token для {instance.email}",
            body=token.key,
            from_email=settings.EMAIL_HOST_USER,
            to=[instance.email],
        )
        msg.send()
