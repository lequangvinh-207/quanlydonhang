from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='vnd')
def vnd(value):
    """
    Format số tiền theo định dạng Việt Nam, ví dụ: 25000 -> 25.000đ
    """
    if value is None or value == '':
        return '0đ'
    try:
        val = int(Decimal(str(value)))
        # Format dấu chấm phân cách hàng nghìn
        formatted = f"{val:,}".replace(',', '.')
        return f"{formatted}đ"
    except (ValueError, TypeError):
        return f"{value}đ"

