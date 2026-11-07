from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from menu.models import Product

class Order(models.Model):
    """
    Model lưu thông tin đơn hàng của shop
    """
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Tại chỗ'),
        ('takeaway', 'Mang đi'),
        ('delivery', 'Giao hàng'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Tiền mặt'),
        ('transfer', 'Chuyển khoản'),
        ('cod', 'Thu khi giao (COD)'),
    ]

    STATUS_CHOICES = [
        ('new', 'Mới'),
        ('preparing', 'Đang chuẩn bị'),
        ('delivering', 'Đang giao'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
        ('customer_refused', 'Khách không nhận'),
    ]

    DISCOUNT_TYPE_CHOICES = [
        ('amount', 'Số tiền (đ)'),
        ('percent', 'Phần trăm (%)'),
    ]

    code = models.CharField(max_length=32, unique=True, verbose_name="Mã đơn hàng", editable=False)
    customer_name = models.CharField(max_length=150, verbose_name="Tên khách hàng", default="Khách lẻ")
    customer_contact = models.CharField(max_length=150, blank=True, verbose_name="SĐT / Facebook / Zalo")
    address = models.TextField(blank=True, verbose_name="Địa chỉ nhận hàng")
    
    order_type = models.CharField(
        max_length=20, 
        choices=ORDER_TYPE_CHOICES, 
        default='dine_in', 
        verbose_name="Hình thức"
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES, 
        default='cash', 
        verbose_name="Thanh toán"
    )
    is_paid = models.BooleanField(default=False, verbose_name="Đã thanh toán")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new', 
        verbose_name="Trạng thái"
    )

    discount_type = models.CharField(
        max_length=10, 
        choices=DISCOUNT_TYPE_CHOICES, 
        default='amount', 
        verbose_name="Kiểu giảm giá"
    )
    discount_value = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=0, 
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Giá trị giảm"
    )
    shipping_fee = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=0, 
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Phí giao hàng"
    )
    note = models.TextField(blank=True, verbose_name="Ghi chú đơn hàng")
    source = models.CharField(
        max_length=20,
        choices=[
            ('web', 'Đặt qua Web'),
            ('message', 'Đặt qua Tin nhắn'),
            ('pos', 'Tạo tại quán'),
        ],
        default='pos',
        verbose_name="Nguồn đơn"
    )
    desired_time = models.CharField(max_length=100, blank=True, verbose_name="Thời gian muốn nhận")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "Đơn hàng"
        verbose_name_plural = "Danh sách đơn hàng"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            # Mã đơn khó đoán: HQ + 6 ký tự ngẫu nhiên (loại bỏ 0,O,I,1 dễ nhầm)
            import random, string
            chars = ''.join(c for c in (string.ascii_uppercase + string.digits)
                            if c not in ('O', 'I', '0', '1'))
            while True:
                candidate = 'HQ' + ''.join(random.choices(chars, k=6))
                if not Order.objects.filter(code=candidate).exists():
                    self.code = candidate
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.customer_name} ({self.get_status_display()})"

    @property
    def total_quantity(self):
        """Tổng số lượng hộp/món trong đơn"""
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        """Tổng tiền hàng trước giảm giá và ship"""
        return sum(item.subtotal for item in self.items.all())

    @property
    def discount_amount(self):
        """Tính số tiền giảm thực tế"""
        sub = self.subtotal
        if self.discount_type == 'percent':
            amt = (sub * self.discount_value) / Decimal('100')
        else:
            amt = self.discount_value
        return min(sub, amt)

    @property
    def final_total(self):
        """Tổng tiền thanh toán cuối cùng"""
        base = max(Decimal('0'), self.subtotal - self.discount_amount)
        return base + (self.shipping_fee or Decimal('0'))

    @property
    def total_cost(self):
        """Tổng giá nhập ước tính của đơn hàng để tính lợi nhuận"""
        return sum((item.total_cost for item in self.items.all()), Decimal('0'))


class OrderItem(models.Model):
    """
    Chi tiết từng món trong đơn hàng (lưu giá và lựa chọn tại thời điểm đặt).
    """

    SALT_CHOICES = [
        ('tay_ninh', 'Muối Tây Ninh'),
        ('hao_hao', 'Muối Hảo Hảo'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Đơn hàng")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Món")
    product_name = models.CharField(max_length=150, verbose_name="Tên món")
    unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Đơn giá bán tại thời điểm đặt"
    )
    unit_cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Giá nhập tại thời điểm đặt"
    )
    quantity = models.PositiveIntegerField(
        default=1, 
        validators=[MinValueValidator(1)],
        verbose_name="Số lượng"
    )
    note = models.CharField(max_length=255, blank=True, verbose_name="Ghi chú món (VD: Không dưa hấu,...)")
    salt_choice = models.CharField(
        max_length=20,
        blank=True,
        choices=SALT_CHOICES,
        verbose_name="Loại muối",
    )

    class Meta:
        verbose_name = "Món trong đơn"
        verbose_name_plural = "Các món trong đơn"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    @property
    def total_cost(self):
        cost_price = self.unit_cost_price
        if cost_price is None and self.product_id:
            cost_price = self.product.cost_price
        return (cost_price or Decimal('0')) * self.quantity
