from json import loads as load_json

from django.db import IntegrityError
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contacts.models import Contact
from apps.orders.models import Order, OrderItem, StateType
from apps.orders.serializers import OrderItemSerializer, OrderSerializer
from apps.orders.signals import new_order


class BasketView(APIView):
    """
    Управление корзиной пользователя.
    """

    def get(self, request, *args, **kwargs):
        """
        Получение содержимого корзины пользователя.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )
        basket = (
            Order.objects.filter(user_id=request.user.id, state=StateType.BASKET)
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Добавление товаров в корзину.

        В теле запроса ожидается JSON с ключом 'items' — списком объектов,
        каждый из которых содержит 'product_info' (ID ProductInfo) и 'quantity' (целое число).

        Метод создаёт или обновляет корзину пользователя (заказ со статусом 'basket')
        и добавляет в неё указанные позиции как OrderItem.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        items = request.data.get("items")

        if items is None:
            return Response(
                {"status": False, "error": 'Поле "items" не указано'}, status=400
            )

        if not isinstance(items, list):
            return Response(
                {"status": False, "error": 'Поле "items" должно быть списком'},
                status=400,
            )

        if len(items) == 0:
            return Response(
                {"status": False, "error": "Список товаров пуст"}, status=400
            )

        basket, _ = Order.objects.get_or_create(
            user_id=request.user.id, state=StateType.BASKET
        )

        objects_created = 0
        for item in items:
            item["order"] = basket.id

            serializer = OrderItemSerializer(data=item)
            if serializer.is_valid():
                try:
                    serializer.save()
                    objects_created += 1
                except IntegrityError as e:
                    return Response(
                        {
                            "status": False,
                            "error": f"Ошибка целостности данных: {str(e)}",
                        },
                        status=400,
                    )
            else:
                return Response(
                    {"status": False, "error": serializer.errors}, status=400
                )

        return Response({"status": True, "Создано объектов": objects_created})

    def delete(self, request, *args, **kwargs):
        """
        Удаление товаров из корзины пользователя.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        items_string = request.data.get("items")
        if items_string:
            items_list = items_string.split(",")
            basket, _ = Order.objects.get_or_create(
                user_id=request.user.id, state=StateType.BASKET
            )
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return Response({"status": True, "Удалено объектов": deleted_count})
        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )

    def put(self, request, *args, **kwargs):
        """
        Обновление количества товаров в корзине.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        items_string = request.data.get("items")
        if items_string:
            try:
                items_dict = load_json(items_string)
            except ValueError:
                return Response({"status": False, "error": "Неверный формат запроса"})
            else:
                basket, _ = Order.objects.get_or_create(
                    user_id=request.user.id, state=StateType.BASKET
                )
                objects_updated = 0
                for order_item in items_dict:
                    if (
                        type(order_item["id"]) is int
                        and type(order_item["quantity"]) is int
                    ):
                        objects_updated += OrderItem.objects.filter(
                            order_id=basket.id, id=order_item["id"]
                        ).update(quantity=order_item["quantity"])

                return Response({"status": True, "Обновлено объектов": objects_updated})
        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )


class OrderView(APIView):
    """
    Получение списка заказов и оформления нового заказа из корзины.
    """

    def get(self, request, *args, **kwargs):
        """
        Получение списка всех заказов пользователя (исключая корзину).
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )
        order = (
            Order.objects.filter(user_id=request.user.id)
            .exclude(state=StateType.BASKET)
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(F("ordered_items__quantity") * F("ordered_items__price"))
            )
            .distinct()
        )

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Оформление заказа из корзины.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        if {"id", "contact"}.issubset(request.data):
            order_id = request.data["id"]
            contact_id = request.data["contact"]

            if not Contact.objects.filter(id=contact_id, user=request.user).exists():
                return Response(
                    {"status": False, "error": "Недопустимый контакт"}, status=400
                )

            if order_id.isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=order_id, state=StateType.BASKET
                    ).update(contact_id=contact_id, state=StateType.NEW)
                except IntegrityError:
                    return Response(
                        {"status": False, "error": "Неправильно указаны аргументы"}
                    )
                else:
                    if is_updated:
                        # Фиксируем цену на момент оформления заказа
                        order_items = OrderItem.objects.filter(order_id=order_id)
                        for item in order_items:
                            if item.price is None:
                                item.price = item.product_info.price
                                item.save(update_fields=["price"])

                        new_order.send(sender=self.__class__, user_id=request.user.id)
                        return Response({"status": True})

        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"}
        )


class PartnerOrderStatusView(APIView):
    """
    Обновление статуса заказа поставщиком (магазином).
    """

    def post(self, request, *args, **kwargs):
        """
        Обновление статуса заказа поставщиком.
        """
        if not request.user.is_authenticated or request.user.type != "shop":
            return Response(
                {"status": False, "error": "Только для магазинов"}, status=403
            )

        order_id = request.data.get("id")
        new_state = request.data.get("state")

        if not order_id or not new_state:
            return Response(
                {"status": False, "error": "Укажите id и state"}, status=400
            )

        if new_state not in StateType.values:
            return Response(
                {"status": False, "error": "Недопустимый статус"}, status=400
            )

        updated = Order.objects.filter(
            id=order_id, ordered_items__product_info__shop__user=request.user
        ).update(state=new_state)

        if updated:
            return Response({"status": True})
        else:
            return Response(
                {"status": False, "error": "Заказ не найден или не принадлежит вам"},
                status=404,
            )


class OrderDetailView(APIView):
    """
    Класс для получения детальной информации о конкретном заказе по его ID.
    """

    def get(self, request, *args, **kwargs):
        """
        Получение детальной информации о заказе по его ID.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        order_id = kwargs.get("pk")
        if not order_id or not str(order_id).isdigit():
            return Response(
                {"status": False, "error": "Некорректный ID заказа"}, status=400
            )

        order = get_object_or_404(
            Order.objects.filter(user_id=request.user.id)
            .exclude(state=StateType.BASKET)
            .select_related("contact")
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .annotate(
                total_sum=Sum(F("ordered_items__quantity") * F("ordered_items__price"))
            ),
            id=order_id,
        )

        serializer = OrderSerializer(order)
        return Response(serializer.data)
