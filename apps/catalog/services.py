from requests import get
from yaml import safe_load, YAMLError

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter
from apps.orders.models import OrderItem


def import_shop_data_from_url(user, url):
    """
    Импортирует данные магазина из YAML по URL.

    Логика:
    - Удаляются ТОЛЬКО те ProductInfo, на которые НЕТ заказов.
    - Если товар есть в YAML — обновляется (или создаётся).
    - Если товара нет в YAML, но на него есть заказ — он остаётся в БД
    - Параметры пересоздаются при обновлении (т.к. структура параметров может меняться).
    - user это авторизованный пользователь типа 'shop'
    """
    # Валидация URL
    validator = URLValidator()
    try:
        validator(url)
    except ValidationError as e:
        return {"status": False, "error": f"Неверный URL: {e}"}

    # Загрузка содержимого
    try:
        response = get(url.strip(), timeout=10)
        response.raise_for_status()
        content = response.content
    except Exception as e:
        return {"status": False, "error": f"Ошибка загрузки файла: {e}"}

    if not content.strip():
        return {"status": False, "error": "Файл пустой"}

    try:
        data = safe_load(content)
    except YAMLError as e:
        return {"status": False, "error": f"Неверный формат данных (YAML/JSON): {e}"}

    if not isinstance(data, dict) or not {"shop", "categories", "goods"}.issubset(
        data.keys()
    ):
        return {
            "status": False,
            "error": "Неверная структура YAML: требуются shop, categories, goods",
        }

    # Получаем/создаём магазин
    shop, created = Shop.objects.get_or_create(
        user=user, defaults={"name": data["shop"], "url": url}
    )
    if not created:
        shop.name = data["shop"]
        shop.url = url
        shop.save(update_fields=["name", "url"])

    # Обработка категорий
    category_objects = {}
    for cat in data["categories"]:
        if "id" not in cat or "name" not in cat:
            return {
                "status": False,
                "error": f"В категории отсутствует id или name: {cat}",
            }

        category, _ = Category.objects.get_or_create(
            external_id=cat["id"], defaults={"name": cat["name"]}
        )
        if category.name != cat["name"]:
            category.name = cat["name"]
            category.save(update_fields=["name"])
        category.shops.add(shop)
        category_objects[cat["id"]] = category

    # Определяем, какие ProductInfo можно безопасно удалить
    all_shop_products = ProductInfo.objects.filter(shop=shop)
    ordered_ids = OrderItem.objects.filter(
        product_info__in=all_shop_products
    ).values_list("product_info_id", flat=True)

    # Удаляем только те записи, которые НЕ используются в заказах
    safe_to_delete = all_shop_products.exclude(id__in=ordered_ids)
    safe_to_delete.delete()

    # Обработка товаров из YAML
    for item in data["goods"]:
        required_fields = {"id", "category", "name", "price", "price_rrc", "quantity"}
        if not required_fields.issubset(item.keys()):
            missing = required_fields - set(item.keys())
            return {"status": False, "error": f"В товаре отсутствуют поля: {missing}"}

        cat_id = item.get("category")
        if cat_id not in category_objects:
            return {
                "status": False,
                "error": f"Категория с external_id={cat_id} не объявлена в разделе categories",
            }

        category = category_objects[cat_id]
        product, _ = Product.objects.get_or_create(name=item["name"], category=category)

        # Обновляем или создаём ProductInfo по (shop, external_id)
        product_info, created = ProductInfo.objects.update_or_create(
            shop=shop,
            external_id=item["id"],
            defaults={
                "product": product,
                "model": item.get("model", ""),
                "price": item["price"],
                "price_rrc": item["price_rrc"],
                "quantity": item["quantity"],
            },
        )

        # Пересоздаём параметры — так как структура может измениться
        ProductParameter.objects.filter(product_info=product_info).delete()
        for param_name, param_value in item.get("parameters", {}).items():
            parameter, _ = Parameter.objects.get_or_create(name=param_name)
            ProductParameter.objects.create(
                product_info=product_info, parameter=parameter, value=str(param_value)
            )

    return {"status": True}


def strtobool(val):
    """
    Преобразует строковые представления булевых значений в булевы значения (True/False).
    """
    if isinstance(val, bool):
        return val
    val = val.lower()
    if val in {"true", "1", "t", "yes", "y", "on"}:
        return True
    elif val in {"false", "0", "f", "no", "n", "off"}:
        return False
    else:
        raise ValueError(f"Недопустимое значение {val}")
