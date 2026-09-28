"""Payment integration (v72) — VIP membership + paid chapters."""
from __future__ import annotations
from django.db import models


class PaymentOrder(models.Model):
    """A payment order."""
    STATUS = (
        ("pending", "待支付"),
        ("paid", "已支付"),
        ("failed", "失败"),
        ("refunded", "已退款"),
    )
    PRODUCT_TYPES = (
        ("vip_monthly", "VIP月卡"),
        ("vip_yearly", "VIP年卡"),
        ("coins", "金币充值"),
        ("chapter", "付费章节"),
    )
    
    order_no = models.CharField("订单号", max_length=64, unique=True, db_index=True)
    reader = models.ForeignKey("account.ReaderProfile", on_delete=models.CASCADE, related_name="orders")
    product_type = models.CharField("商品类型", max_length=32, choices=PRODUCT_TYPES)
    amount = models.DecimalField("金额", max_digits=10, decimal_places=2)
    currency = models.CharField("货币", max_length=8, default="CNY")
    
    # Payment provider
    provider = models.CharField("支付渠道", max_length=16, default="alipay",
        choices=[("alipay", "支付宝"), ("wechat", "微信支付"), ("paypal", "PayPal")])
    provider_order_id = models.CharField("渠道订单号", max_length=128, blank=True)
    
    status = models.CharField("状态", max_length=16, choices=STATUS, default="pending")
    paid_at = models.DateTimeField("支付时间", null=True, blank=True)
    
    # For chapter purchases
    book_id = models.IntegerField("书籍ID", null=True, blank=True)
    chapter_id = models.IntegerField("章节ID", null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account_payment_order"
        verbose_name = "支付订单"
        verbose_name_plural = verbose_name
        ordering = ("-id",)

    def __str__(self): return f"{self.order_no} ({self.status})"


def create_order(reader, product_type: str, amount: float, **kwargs) -> PaymentOrder:
    """Create a new payment order."""
    import uuid
    return PaymentOrder.objects.create(
        order_no=f"NOVEL-{uuid.uuid4().hex[:16].upper()}",
        reader=reader, product_type=product_type, amount=amount, **kwargs,
    )


def mark_paid(order_no: str, provider_order_id: str = "") -> PaymentOrder | None:
    """Mark an order as paid + apply the product."""
    from django.utils import timezone
    try:
        order = PaymentOrder.objects.get(order_no=order_no)
    except PaymentOrder.DoesNotExist:
        return None
    order.status = "paid"
    order.paid_at = timezone.now()
    if provider_order_id:
        order.provider_order_id = provider_order_id
    order.save(update_fields=["status", "paid_at", "provider_order_id"])
    
    # Apply product
    if order.product_type == "vip_monthly":
        from datetime import timedelta
        reader = order.reader
        from django.utils import timezone
        base = reader.membership_expires or timezone.now()
        reader.membership_level = "vip"
        reader.membership_expires = base + timedelta(days=30)
        reader.save(update_fields=["membership_level", "membership_expires"])
    elif order.product_type == "vip_yearly":
        from datetime import timedelta
        reader = order.reader
        from django.utils import timezone
        base = reader.membership_expires or timezone.now()
        reader.membership_level = "vip"
        reader.membership_expires = base + timedelta(days=365)
        reader.save(update_fields=["membership_level", "membership_expires"])
    elif order.product_type == "coins":
        # 1 CNY = 100 coins
        reader = order.reader
        reader.coins += int(order.amount * 100)
        reader.save(update_fields=["coins"])
    
    return order


class PaidChapter(models.Model):
    """Records which chapters a reader has paid for."""
    reader = models.ForeignKey("account.ReaderProfile", on_delete=models.CASCADE, related_name="paid_chapters")
    chapter = models.ForeignKey("novel.Chapter", on_delete=models.CASCADE)
    order = models.ForeignKey(PaymentOrder, on_delete=models.SET_NULL, null=True, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "account_paid_chapter"
        verbose_name = "付费章节"
        verbose_name_plural = verbose_name
        unique_together = ("reader", "chapter")
