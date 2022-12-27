import codecs
import csv

from django.db.models import Count, F, Sum
from django.db.models.functions import Coalesce, TruncMonth
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from inventory_api.custom_methods import IsAuthenticatedCustom
from user_control.models import CustomUser
from inventory_api.utils import CustomPagination, get_query

from .models import Inventory, InventoryGroup, Invoice, InvoiceItems, Shop
from .serializers import (InventoryGroupSerializer, InventorySerializer,
                          InventoryWithSumSerializer, InvoiceSerializer,
                          ShopSerializer, ShopWithAmountSerializer)


class InventoryView(ModelViewSet):

    http_method_names = ["post"]
    queryset = Inventory.objects.select_related("group", "created_by")
    serializer_class = InventorySerializer
    permission_class = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset

        data = self.request.query_params.dict()
        data.pop("page")
        keyword = data.pop("keyword", None)

        results = self.queryset(**data)

        if keyword:
            search_fields = (
                "code",
                "created_by__fullname",
                "created_by__email",
                "group__name",
                "name",
            )
            query = get_query(keyword, search_fields)
            return results.filter(query)

        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)


class InventoryGroupView(ModelViewSet):

    http_method_names = ["post"]
    queryset = InventoryGroup.objects.select_related(
        "created_by", "belongs_to"
    ).prefetch_related("inventories")
    serializer_class = InventoryGroupSerializer
    permission_class = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset

        data = self.request.query_params.dict()
        data.pop("page")
        keyword = data.pop("keyword", None)

        results = self.queryset(**data)

        if keyword:
            search_fields = (
                "created_by__fullname",
                "created_by__email",
                "name",
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results.annotate(total_items=Count("inventories"))

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)


class ShopView(ModelViewSet):

    http_method_names = ["post"]
    queryset = Shop.objects.select_related("created_by")
    serializer_class = ShopSerializer
    permission_class = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset

        data = self.request.query_params.dict()
        data.pop("page")
        keyword = data.pop("keyword", None)

        results = self.queryset(**data)

        if keyword:
            search_fields = (
                "created_by__fullname",
                "created_by__email",
                "name",
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)


class InvoiceView(ModelViewSet):
    http_method_names = ["post"]
    queryset = Invoice.objects.select_related("created_by", "shop").prefetch_related(
        "invoice_items"
    )
    serializer_class = InvoiceSerializer
    permission_class = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return self.queryset

        data = self.request.query_params.dict()
        data.pop("page")
        keyword = data.pop("keyword", None)

        results = self.queryset(**data)

        if keyword:
            search_fields = (
                "created_by__fullname",
                "created_by__email",
                "shop__name",
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        return super().create(request, *args, **kwargs)


class SummaryView(ModelViewSet):
    http_method_names = ["get"]
    queryset = InventoryView.queryset
    permission_class = (IsAuthenticatedCustom,)

    def list(self, request, *args, **kwargs):
        total_inventory = InventoryView.queryset.filter(remaining__gt=0).count()
        total_group = InventoryGroupView.queryset.count()
        total_shop = ShopView.queryset.count()
        total_users = CustomUser.object.filter(is_superuser=False).count()

        return Response(
            {
                "total_inventory": total_inventory,
                "total_group": total_group,
                "total_shop": total_shop,
                "total_users": total_users,
            }
        )


class SalesPerformanceView(ModelViewSet):
    http_method_names = ["get"]
    queryset = InventoryView.queryset
    permission_class = (IsAuthenticatedCustom,)

    def list(self, request, *args, **kwargs):
        query_data = request.query_params.dict()
        total = query_data.get("total", None)
        query = self.queryset

        if not total:
            start_date = query_data.get("start_date", None)
            end_data = query_data.get("end_date", None)

            if start_date:
                query = query.filter(
                    inventory_invoices__created_at__range=[start_date, end_data]
                )

        items = query.annotate(
            sum_of_items_sold=Coalesce(Sum("inventory_invoices__quantity"), 0)
        ).order_by("-sum_of_items_sold")[0:10]

        response_data = InventoryWithSumSerializer(items, many=True).data
        return Response(response_data)


class SaleByShopView(ModelViewSet):
    http_method_names = ["get"]
    queryset = InventoryView.queryset
    permission_class = (IsAuthenticatedCustom,)
    serializer_class = InventoryWithSumSerializer

    def list(self, request, *args, **kwargs):
        query_data = request.query_params.dict()
        total = query_data.get("total", None)
        monthly = query_data.get("monthly", None)
        query = ShopView.queryset

        if not total:
            start_date = query_data.get("start_date", None)
            end_data = query_data.get("end_date", None)

            if start_date:
                query = query.filter(
                    sale_shop__created_at__range=[start_date, end_data]
                )

        if monthly:
            shops = (
                query.annotate(month=TruncMonth("created_at"))
                .values("month", "name")
                .annotate(
                    amount_total=Sum(
                        F("sales_shop__invoice_items__quantity")
                        * F("sales_shop__invoice_items__amount")
                    )
                )
            ).order_by("-amount_total")

        else:
            shops = query.annotate(
                amount_total=Sum(
                    F("sales_shop__invoice_items__quantity")
                    * F("sales_shop__invoice_items__amount")
                )
            ).order_by("-amount_total")

        response_data = ShopWithAmountSerializer(shops, many=True).data
        return Response(response_data)


class PurshaseView(ModelViewSet):
    http_method_names = ["get"]
    queryset = InventoryView.queryset
    permission_class = (IsAuthenticatedCustom,)
    queryset = InvoiceView.queryset

    def list(self, request, *args, **kwargs):
        query_data = request.query_params.dict()
        total = query_data.get("total", None)
        query = InvoiceItems.objects.select_related("invoice", "item")

        if not total:
            start_date = query_data.get("start_date", None)
            end_data = query_data.get("end_date", None)

            if start_date:
                query = query.filter(
                    inventory_invoices__created_at__range=[start_date, end_data]
                )

        query = query.aggregate(
            amount_total=Sum(F("amount") * F("quantity")), total=Sum("quantity")
        )

        return Response(
            {
                "price": "0,00"
                if query.get("amount_total")
                else query.get("amount_total")
            },
            {"count": 0 if query.get("total") else query.get("total")},
        )


class InventoryCSVLoaderView(ModelViewSet):
    http_method_names = ["post"]
    queryset = InventoryView
    permission_classes = (IsAuthenticatedCustom,)
    serializer_class = InventorySerializer

    def create(self, request, *args, **kwargs):
        try:
            data = request.FILES["data"]
        except Exception as e:
            raise Exception("Envie um arquivo CSV com a lista de produtos")

        inventory_items = []

        try:
            csv_reader = csv.reader(codecs.iterdecode(data, "utf-8"))
            for row in csv_reader:
                if not row[0]:
                    continue
                inventory_items.append(
                    {
                        "group_id": row[0],
                        "toral": row[1],
                        "name": row[2],
                        "price": row[3],
                        "photo": row[4],
                        "created_by_id": request.user.id,
                    }
                )
        except csv.Error as e:
            raise Exception(e)

        if not inventory_items:
            raise Exception("Erro ao ler arquivo .csv")

        data_validation = self.serializer_class(data=inventory_items, many=True)
        data_validation.is_valid(raise_exception=True)
        data_validation.save()

        return Response({"success": "Items adicionados com sucesso"})
