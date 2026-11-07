from django import forms
import re
from .models import Order


class CustomerOrderForm(forms.Form):
    customer_name = forms.CharField(
        label='Họ và tên',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
    )
    customer_contact = forms.CharField(
        label='Số điện thoại',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'tel',
            'autocomplete': 'tel',
            'placeholder': 'VD: 0912345678',
        }),
    )
    address = forms.CharField(
        label='Địa chỉ giao hàng',
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'autocomplete': 'street-address',
        }),
    )
    note = forms.CharField(
        label='Ghi chú đơn hàng',
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
    desired_time = forms.CharField(
        label='Thời gian muốn nhận',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'VD: Sau 18:00 hôm nay',
        }),
    )
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'tabindex': '-1',
            'autocomplete': 'off',
            'aria-hidden': 'true',
        }),
    )

    def clean_customer_name(self):
        name = self.cleaned_data['customer_name'].strip()
        if not name:
            raise forms.ValidationError('Vui lòng nhập họ tên.')
        return name

    def clean_customer_contact(self):
        phone = re.sub(r'[\s().-]', '', self.cleaned_data['customer_contact'])
        if not re.fullmatch(r'(?:\+?84|0)(?:3|5|7|8|9)\d{8}', phone):
            raise forms.ValidationError('Vui lòng nhập số điện thoại di động Việt Nam hợp lệ.')
        return phone

    def clean_address(self):
        address = self.cleaned_data['address'].strip()
        if not address:
            raise forms.ValidationError('Vui lòng nhập địa chỉ giao hàng.')
        return address


class OrderCreateForm(forms.ModelForm):
    customer_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = Order
        fields = [
            'customer_name', 'customer_contact', 'address',
            'order_type', 'payment_method', 'is_paid',
            'discount_type', 'discount_value', 'shipping_fee', 'note',
        ]

    def clean_customer_name(self):
        return self.cleaned_data.get('customer_name', '').strip() or 'Khách lẻ'

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get('discount_type') == 'percent'
            and cleaned_data.get('discount_value', 0) > 100
        ):
            self.add_error('discount_value', 'Mức giảm theo phần trăm không được vượt quá 100%.')
        return cleaned_data


class OrderUpdateForm(forms.ModelForm):
    """
    Form cập nhật thông tin đơn hàng
    """
    class Meta:
        model = Order
        fields = [
            'customer_name', 'customer_contact', 'address',
            'order_type', 'payment_method', 'is_paid', 'status',
            'discount_type', 'discount_value', 'shipping_fee', 'note'
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SĐT hoặc Facebook / Zalo'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Địa chỉ giao hàng nếu có'}),
            'order_type': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is_paid'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'shipping_fee': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú cho đơn hàng...'}),
        }
        labels = {
            'customer_name': 'Tên khách hàng',
            'customer_contact': 'SĐT / Mạng xã hội',
            'address': 'Địa chỉ giao hàng',
            'order_type': 'Hình thức phục vụ',
            'payment_method': 'Phương thức thanh toán',
            'is_paid': 'Đã thanh toán',
            'status': 'Trạng thái đơn',
            'discount_type': 'Kiểu giảm giá',
            'discount_value': 'Giá trị giảm',
            'shipping_fee': 'Phí giao hàng (VNĐ)',
            'note': 'Ghi chú đơn hàng',
        }

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get('discount_type') == 'percent'
            and cleaned_data.get('discount_value', 0) > 100
        ):
            self.add_error('discount_value', 'Mức giảm theo phần trăm không được vượt quá 100%.')
        return cleaned_data
