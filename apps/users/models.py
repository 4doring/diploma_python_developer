from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django_rest_passwordreset.tokens import get_token_generator
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserType(models.TextChoices):
    SHOP = "shop", "Магазин"
    BUYER = "buyer", "Покупатель"


class UserManager(BaseUserManager):
    """
    Менеджер для модели пользователя.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Необходимо указать адрес электронной почты.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("У суперпользователя должно быть is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("У суперпользователя должно быть is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Модель пользователя.
    """

    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = "email"
    email = models.EmailField(_("email address"), unique=True)
    company = models.CharField(verbose_name="Компания", max_length=40, blank=True)
    position = models.CharField(verbose_name="Должность", max_length=40, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _("username"),
        max_length=150,
        help_text=_(
            "Требуется 150 символов или меньше. Буквы, цифры и @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("Пользователь с таким именем уже существует."),
        },
    )
    is_active = models.BooleanField(
        _("active"),
        default=False,
        help_text=_(
            "Указывает, следует ли считать данного пользователя активным."
            "Снимите этот флаг вместо удаления учетных записей."
        ),
    )
    type = models.CharField(
        verbose_name="Тип пользователя",
        choices=UserType.choices,
        max_length=5,
        default=UserType.BUYER,
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Список пользователей"
        ordering = ("email",)


class ConfirmEmailToken(models.Model):
    objects = models.manager.Manager()
    """
    Модель токена для подтверждения email при регистрации пользователя.
    """

    class Meta:
        verbose_name = "Токен подтверждения Email"
        verbose_name_plural = "Токены подтверждения Email"

    @staticmethod
    def generate_key():
        """Генерирует токен с использованием генератора токенов Django Rest Passwordreset."""
        return get_token_generator().generate_token()

    user = models.ForeignKey(
        User,
        related_name="confirm_email_tokens",
        on_delete=models.CASCADE,
        verbose_name=_("Пользователь, связанный с этим токеном подтверждения email"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Дата создания токена")
    )

    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return "Токен подтверждения email для пользователя {user}".format(
            user=self.user
        )
