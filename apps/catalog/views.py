from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Category, ProductInfo, Shop
from apps.catalog.serializers import (
    CategorySerializer,
    ProductInfoSerializer,
    ShopSerializer,
)
from apps.orders.models import Order, StateType
from apps.orders.serializers import OrderSerializer

from .services import import_shop_data_from_url, strtobool


class CategoryView(ListAPIView):
    """
    Для просмотра категорий.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Для просмотра списка магазинов.
    """

    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
    Для поиска товаров по фильтрам.
    """

    def get(self, request: Request, *args, **kwargs):
        """ "
        Получение списка товаров с применением фильтров.
        """
        query = Q(shop__state=True)
        shop_id = request.query_params.get("shop_id")
        category_id = request.query_params.get("category_id")
        search = request.query_params.get("search")

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        if search:
            query = query & Q(product__name__icontains=search)

        queryset = (
            ProductInfo.objects.filter(query)
            .select_related("shop", "product__category")
            .prefetch_related("product_parameters__parameter")
            .distinct()
        )

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)


class PartnerUpdate(APIView):
    """
    Обновление прайс-листа магазина из YAML-файла по указанному URL.
    Доступно только авторизованным пользователям с типом 'shop'.
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"status": False, "error": "Log in required"}, status=403)
        if request.user.type != "shop":
            return Response(
                {"status": False, "error": "Только для магазинов"}, status=403
            )

        url = request.data.get("url")
        if not url:
            return Response({"status": False, "error": "URL не указан"}, status=400)

        result = import_shop_data_from_url(user=request.user, url=url)

        if result["status"]:
            return Response({"status": True})
        else:
            return Response({"status": False, "error": result["error"]}, status=400)


class PartnerState(APIView):
    """
    Для управления статусом магазина партнёра.
    """

    def get(self, request, *args, **kwargs):
        """
        Получение текущего состояния магазина партнёра.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        if request.user.type != "shop":
            return Response(
                {"status": False, "error": "Только для магазинов"}, status=403
            )

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """
        Обновление состояния магазина.
        """
        if not request.user.is_authenticated:
            return Response(
                {"status": False, "error": "Требуется авторизация"}, status=403
            )

        if request.user.type != "shop":
            return Response(
                {"status": False, "error": "Только для магазинов"}, status=403
            )
        state = request.data.get("state")
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(
                    state=strtobool(state)
                )
                return Response({"status": True})
            except ValueError as error:
                return Response(
                    {
                        "status": False,
                        "error": f"Некорректное значение состояния: {str(error)}",
                    },
                    status=400,
                )

        return Response(
            {"status": False, "error": "Не указаны все необходимые аргументы"},
            status=400,
        )


class PartnerOrders(APIView):
    """
    Для получения заказов, связанных с магазином партнёра.
    """

    def get(self, request, *args, **kwargs):
        """
        Получение списка заказов, содержащих товары из магазина партнёра.
        """
        if not request.user.is_authenticated:
            return Response({"status": False, "error": "Требуется авторизация"}, status=403)

        if request.user.type != "shop":
            return Response(
                {"status": False, "error": "Только для магазинов"}, status=403
            )

        order = (
            Order.objects.filter(
                ordered_items__product_info__shop__user_id=request.user.id
            )
            .exclude(state=StateType.BASKET)
            .prefetch_related(
                "ordered_items__product_info__product__category",
                "ordered_items__product_info__product_parameters__parameter",
            )
            .select_related("contact")
            .annotate(
                total_sum=Sum(
                    F("ordered_items__quantity")
                    * F("ordered_items__product_info__price")
                )
            )
            .distinct()
        )

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ProductDetailView(APIView):
    """
    Класс для получения полной спецификации товара по его ID.
    """

    def get(self, request, *args, **kwargs):
        """
        Получение детальной информации о товаре по его ID.
        """
        if not request.user.is_authenticated:
            return Response({"status": False, "error": "Требуется авторизация"}, status=403)

        product_id = kwargs.get("pk")
        if not product_id or not str(product_id).isdigit():
            return Response(
                {"status": False, "error": "Invalid product ID"}, status=400
            )

        product_info = get_object_or_404(
            ProductInfo.objects.select_related(
                "shop", "product__category"
            ).prefetch_related("product_parameters__parameter"),
            id=product_id,
        )

        serializer = ProductInfoSerializer(product_info)
        return Response(serializer.data)
