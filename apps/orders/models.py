from django.db import models
from apps.catalog.models import ProductInfo
from apps.contacts.models import Contact
from apps.users.models import User


class StateType(models.TextChoices):
    BASKET = "basket", "Статус корзины"
    NEW = "new", "Новый"
    CONFIRMED = "confirmed", "Подтвержден"
    ASSEMBLED = "assembled", "Собран"
    SENT = "sent", "Отправлен"
    DELIVERED = "delivered", "Доставлен"
    CANCELED = "canceled", "Отменен"


class Order(models.Model):
    """
    Модель заказа пользователя.
    Статус 'basket' используется для корзины.
    """

    objects = models.manager.Manager()
    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        related_name="orders",
        blank=True,
        on_delete=models.CASCADE,
    )
    dt = models.DateTimeField(auto_now_add=True)
    state = models.CharField(
        verbose_name="Статус", choices=StateType.choices, max_length=15
    )
    contact = models.ForeignKey(
        Contact, verbose_name="Контакт", blank=True, null=True, on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Список заказов"
        ordering = ("-dt",)

    def __str__(self):
        return str(self.dt)


class OrderItem(models.Model):
    """
    Модель позиции в заказе.
    Связывает заказ с конкретной информацией о продукте.
    """

    objects = models.manager.Manager()
    order = models.ForeignKey(
        Order,
        verbose_name="Заказ",
        related_name="ordered_items",
        blank=True,
        on_delete=models.CASCADE,
    )

    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name="Информация о продукте",
        related_name="ordered_items",
        blank=True,
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")

    price = models.PositiveIntegerField(
        verbose_name="Цена на момент заказа", null=True, blank=True
    )

    class Meta:
        verbose_name = "Заказанная позиция"
        verbose_name_plural = "Список заказанных позиций"
        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "product_info"], name="unique_order_item"
            ),
        ]
