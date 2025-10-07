from django.urls import path

from apps.orders.views import (
    BasketView,
    OrderDetailView,
    OrderView,
)

app_name = "orders"
urlpatterns = [
    path("basket", BasketView.as_view(), name="basket"),
    path("order", OrderView.as_view(), name="order"),
    path("<int:pk>", OrderDetailView.as_view(), name="order-detail"),
]
