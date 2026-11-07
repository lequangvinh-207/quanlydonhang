from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Product(models.Model):
    """
    Model lưu thông tin hoa quả / món ăn trong menu
    """
    name = models.CharField(max_length=150, verbose_name="Tên món")
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=Decimal('25000'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Giá bán (đ)"
    )
    cost_price = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Giá nhập (đ)"
    )
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="Hình ảnh")
    description = models.TextField(blank=True, verbose_name="Mô tả ngắn")
    is_available = models.BooleanField(default=True, verbose_name="Còn hàng")
    is_combo = models.BooleanField(default=False, verbose_name="Là hộp mix đồng giá")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "Món ăn / Hoa quả"
        verbose_name_plural = "Menu hoa quả"
        ordering = ['-is_available', 'name']

    def __str__(self):
        status_text = "" if self.is_available else " (Hết hàng)"
        combo_text = " [Hộp mix]" if self.is_combo else ""
        return f"{self.name}{combo_text} - {self.price:,.0f}đ{status_text}"
