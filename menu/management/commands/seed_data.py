from decimal import Decimal
from django.core.management.base import BaseCommand
from menu.models import Product

class Command(BaseCommand):
    help = 'Khởi tạo dữ liệu mẫu hoa quả cho menu shop'

    def handle(self, *args, **kwargs):
        fruits = [
            {
                'name': 'Dưa hấu cắt sẵn',
                'price': Decimal('25000'),
                'cost_price': Decimal('10000'),
                'description': 'Dưa hấu ngọt mát, ướp lạnh, bỏ hạt, đóng hộp 400g.',
                'is_available': True,
                'is_combo': False,
            },
            {
                'name': 'Xoài cát chu chín vàng',
                'price': Decimal('25000'),
                'cost_price': Decimal('13000'),
                'description': 'Xoài chín cây thơm ngọt lịm, kèm muối tôm Tây Ninh.',
                'is_available': True,
                'is_combo': False,
            },
            {
                'name': 'Thanh long ruột đỏ',
                'price': Decimal('25000'),
                'cost_price': Decimal('11000'),
                'description': 'Thanh long ruột đỏ ngọt thanh mát, giàu vitamin C.',
                'is_available': True,
                'is_combo': False,
            },
            {
                'name': 'Dứa mật thái lát',
                'price': Decimal('25000'),
                'cost_price': Decimal('9000'),
                'description': 'Dứa mật ngọt đậm không rát lưỡi, tặng kèm muối ớt.',
                'is_available': True,
                'is_combo': False,
            },
            {
                'name': 'Ổi bo giòn rụm',
                'price': Decimal('25000'),
                'cost_price': Decimal('8000'),
                'description': 'Ổi giòn ngọt, ít hạt, cắt miếng vừa ăn kèm muối xí muội.',
                'is_available': True,
                'is_combo': False,
            },
            {
                'name': 'Cam sành bóc múi',
                'price': Decimal('25000'),
                'cost_price': Decimal('15000'),
                'description': 'Múi cam mọng nước, thanh mát đã tách vỏ tiện lợi.',
                'is_available': True,
                'is_combo': False,
            },
            {
                'name': 'Nho đen không hạt',
                'price': Decimal('25000'),
                'cost_price': Decimal('14000'),
                'description': 'Nho đen giòn ngọt, cuống tươi xanh, rửa sạch sẵn.',
                'is_available': True,
                'is_combo': False,
            },
            {
                'name': 'Táo Envy giòn ngọt',
                'price': Decimal('25000'),
                'cost_price': Decimal('14000'),
                'description': 'Táo nhập khẩu gọt vỏ cắt lát ngâm nước muối loãng giữ độ tươi giòn.',
                'is_available': True,
                'is_combo': False,
            },
            {
                'name': 'Hộp hoa quả Mix đồng giá 25K',
                'price': Decimal('25000'),
                'cost_price': Decimal('12000'),
                'description': 'Khách chọn tối đa 3-4 loại quả theo sở thích (ghi chú khi đặt hàng).',
                'is_available': True,
                'is_combo': True,
            },
        ]

        count = 0
        for item in fruits:
            obj, created = Product.objects.update_or_create(
                name=item['name'],
                defaults=item
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Đã tạo thành công {count} món hoa quả mẫu vào menu!'))

