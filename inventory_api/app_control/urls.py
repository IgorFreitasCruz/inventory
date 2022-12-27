from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (InventoryCSVLoaderView, InventoryGroupView, InventoryView,
                    InvoiceView, PurshaseView, SaleByShopView,
                    SalesPerformanceView, ShopView, SummaryView)

router = DefaultRouter(trailing_slash=False)

router.register("inventory", InventoryView, "inventory")
router.register("inventory-csv", InventoryCSVLoaderView, "inventory-csv")
router.register("shop", ShopView, "shop")
router.register("summary", SummaryView, "summanry")
router.register("purchase-summary", PurshaseView, "purchase-summary")
router.register("sales-by-shop", SaleByShopView, "sales-by-shop")
router.register("group", InventoryGroupView, "group")
router.register("top-selling", SalesPerformanceView, "top-selling")
router.register("invoice", InvoiceView, "invoice")


urlpatterns = [
    path("", include(router.urls))
]
