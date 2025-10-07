from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import Signal, receiver

from apps.orders.models import Order
from apps.users.models import User

new_order = Signal()


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Обработчик сигнала `new_order`.
    Отправляет два email-уведомления:
    1. Покупателю - подтверждение заказа и общая сумма.
    2. Администратору - детальная накладная.
    """

    user = User.objects.get(id=user_id)

    order = (
        Order.objects.filter(user_id=user_id, state="new")
        .select_related("contact")
        .prefetch_related(
            "ordered_items__product_info__shop", "ordered_items__product_info__product"
        )
        .first()
    )

    if not order:
        return

    total_sum = sum(item.quantity * item.price for item in order.ordered_items.all())

    # Письмо покупателю
    buyer_subject = f"Ваш заказ №{order.id} принят"
    buyer_body = f"Заказ успешно сформирован.\nОбщая сумма заказа: {total_sum} руб."
    buyer_msg = EmailMultiAlternatives(
        subject=buyer_subject,
        body=buyer_body,
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email],
    )
    buyer_msg.send()

    # Письмо администратору
    shop_items = {}
    for item in order.ordered_items.all():
        shop_name = item.product_info.shop.name
        if shop_name not in shop_items:
            shop_items[shop_name] = []
        shop_items[shop_name].append(
            {
                "product": item.product_info.product.name,
                "quantity": item.quantity,
                "price": item.price,
                "total": item.quantity * item.price,
            }
        )

    lines = [
        f"НАКЛАДНАЯ №{order.id}",
        "",
        f"Заказчик: {user.first_name} {user.last_name}",
        f"Email: {user.email}",
        f"Компания: {user.company or '—'}",
    ]

    if order.contact:
        contact = order.contact
        lines.append(f"Адрес: {contact.city}, ул. {contact.street}, д. {contact.house}")
    else:
        lines.append("Адрес: не указан")

    lines.append("")
    lines.append("Товары по магазинам:")

    for shop_name, items in shop_items.items():
        lines.append(f"\nМагазин: {shop_name}")
        shop_total = 0
        for item in items:
            line = f"  • {item['product']} — {item['quantity']} шт × {item['price']} руб = {item['total']} руб"
            lines.append(line)
            shop_total += item["total"]
        lines.append(f"  Итого по магазину: {shop_total} руб")

    lines.append("")
    lines.append(f"Общая сумма заказа: {total_sum} руб")

    admin_body = "\n".join(lines)

    admin_email = getattr(settings, "ADMIN_EMAIL")

    admin_msg = EmailMultiAlternatives(
        subject=f"Накладная №{order.id} — новый заказ",
        body=admin_body,
        from_email=settings.EMAIL_HOST_USER,
        to=[admin_email],
    )
    admin_msg.send()
