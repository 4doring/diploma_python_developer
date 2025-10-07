from django.urls import path

from apps.catalog.views import (
    CategoryView,
    ProductDetailView,
    ProductInfoView,
    ShopView,
)


app_name = "catalog"
urlpatterns = [
    path("categories", CategoryView.as_view(), name="categories"),
    path("shops", ShopView.as_view(), name="shops"),
    path("", ProductInfoView.as_view(), name="products"),
    path("<int:pk>", ProductDetailView.as_view(), name="product-detail"),
]
