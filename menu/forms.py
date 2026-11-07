from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'cost_price', 'image', 'description', 'is_combo', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Xoài cát chu cắt sẵn'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'VD: 25000', 'min': 0, 'value': 25000}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'VD: 15000 (không bắt buộc)', 'min': 0}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ghi chú ngắn về món/hộp...'}),
            'is_combo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is_combo'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is_available'}),
        }
        labels = {
            'name': 'Tên món',
            'price': 'Giá bán (VNĐ)',
            'image': 'Ảnh minh họa',
            'description': 'Mô tả ngắn',
            'is_combo': 'Là hộp mix đồng giá',
            'is_available': 'Đang còn hàng',
        }
        help_texts = {
            'is_combo': 'Món dạng combo có giá cố định, khách sẽ ghi chú loại quả khi đặt đơn.',
            'is_available': 'Bỏ tích nếu quán tạm hết món này hôm nay.',
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError("Giá bán không được nhỏ hơn 0đ.")
        return price

    def clean_cost_price(self):
        cost_price = self.cleaned_data.get('cost_price')
        if cost_price is not None and cost_price < 0:
            raise forms.ValidationError("Giá nhập không được nhỏ hơn 0đ.")
        return cost_price

