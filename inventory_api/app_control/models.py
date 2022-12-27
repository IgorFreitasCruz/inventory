from django.db import models
from user_control.models import CustomUser
from user_control.views import add_user_activity


class InventoryGroup(models.Model):
    created_by = models.ForeignKey(
        CustomUser,
        null=True,
        related_name="inventory_groups",
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=100, unique=True)
    belongs_to = models.ForeignKey(
        "self", null=True, related_name="relations_group", on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = self.name

    def save(self, *args, **kwargs):
        action = f"Adicionou grupo '{self.name}'"
        if self.pk is not None:
            action = f"Atualizou grupo '{self.old_name}' para '{self.name}'"
        super().save(*args, **kwargs)
        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"{created_by} excluiu o grupo '{self.name}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)


class Inventory(models.Model):
    created_by = models.ForeignKey(
        CustomUser,
        null=True,
        related_name="inventory_items",
        on_delete=models.SET_NULL,
    )
    code = models.CharField(max_length=10, unique=True, null=True)
    photo = models.TextField(blank=True, null=True)
    group = models.ForeignKey(
        InventoryGroup, related_name="inventories", null=True, on_delete=models.SET_NULL
    )
    total_itens = models.PositiveIntegerField()
    remaining = models.PositiveIntegerField(null=True)
    name = models.CharField(max_length=255)
    price = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} - {self.code}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new:
            self.remaining = self.total

        super().save(*args, **kwargs)

        if is_new:
            id_length = len(str(self.id))
            code_length = 6 - id_length
            zeros = "".join("0" for i in range(code_length))
            self.code = f"SARA{zeros}{self.id}"
            self.save()

        action = f"acicionou produto código - {self.code}"

        if not is_new:
            action = f"atualizou produto código - {self.code}"

        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"{created_by} excluiu o produto '{self.code}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)


class Shop(models.Model):
    created_by = models.ForeignKey(
        CustomUser,
        null=True,
        related_name="shops",
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_name = self.name

    def save(self, *args, **kwargs):
        action = f"Adicionou loja '{self.name}'"
        if self.pk is not None:
            action = f"Atualizou loja '{self.old_name}' para '{self.name}'"
        super().save(*args, **kwargs)
        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"{created_by} excluiu a loja '{self.name}'"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)


class Invoice(models.Model):
    created_by = models.ForeignKey(
        CustomUser,
        null=True,
        related_name="invoices",
        on_delete=models.SET_NULL,
    )
    shop = models.ForeignKey(
        Shop, related_name="sale_invoice", null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        action = (
            f"recibo emitido em {self.created_at.strftime('%d/%m/%Y %H%M')} {self.name}"
        )
        super().save(*args, **kwargs)
        add_user_activity(self.created_by, action=action)

    def delete(self, *args, **kwargs):
        created_by = self.created_by
        action = f"{created_by} excluiu recibo {self.id}"
        super().delete(*args, **kwargs)
        add_user_activity(created_by, action=action)


class InvoiceItems(models.Model):
    invoice = models.ForeignKey(
        Invoice, related_name="invoice_items", on_delete=models.CASCADE
    )
    item = models.ForeignKey(
        Inventory,
        related_name="inventory_invoices",
        null=True,
        on_delete=models.SET_NULL,
    )
    item_name = models.CharField(max_length=255, null=True)
    item_code = models.CharField(max_length=20, null=True)
    quantity = models.PositiveIntegerField()
    amount = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.item_code} - {self.quantity}"

    def save(self, *args, **kwargs):
        if self.item.remaining < self.quantity:
            raise Exception(f"Produto código {self.item.code} fora de estoque")

        self.item_name = self.item.name
        self.item_code = self.item.code

        self.amount = self.amount * self.item.price
        self.item.remaining = self.item.remaining - self.quantity
        self.item.save()

        return super().save(*args, **kwargs)
