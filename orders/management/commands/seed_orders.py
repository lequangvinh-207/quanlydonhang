from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from menu.models import Product
from orders.models import Order, OrderItem

class Command(BaseCommand):
    help = 'Tạo dữ liệu đơn hàng mẫu phục vụ kiểm thử và báo cáo'

    def handle(self, *args, **kwargs):
        products = list(Product.objects.all())
        if not products:
            self.stdout.write(self.style.ERROR('Chưa có món nào trong menu. Vui lòng chạy seed_data trước!'))
            return

        customers = [
            ('Trần Văn Bình', '0981234567', 'Số 12 Chùa Láng, Hà Nội', 'delivery'),
            ('Lê Thị Mai', '0978999888', '', 'takeaway'),
            ('Phạm Tuấn Anh', '0912333444', '', 'dine_in'),
            ('Hoàng Thu Trang', '0966555444', 'Tòa Keangnam, Mễ Trì', 'delivery'),
            ('Vũ Đình Long', '0904123890', '', 'dine_in'),
            ('Nguyễn Phương Linh', '0936778899', 'Số 8 Đại Cồ Việt, HBT', 'delivery'),
            ('Đỗ Hùng Dũng', '0988776655', '', 'takeaway'),
        ]

        statuses = ['new', 'preparing', 'delivering', 'completed', 'completed', 'completed', 'cancelled']
        payment_methods = ['cash', 'transfer']

        today = timezone.now()
        count = 0

        # Tạo khoảng 12 đơn hàng mẫu trải dài qua 5 ngày gần đây
        for i in range(12):
            cust_name, cust_contact, addr, otype = random.choice(customers)
            status = random.choice(statuses)
            pmethod = random.choice(payment_methods)
            is_paid = (status == 'completed') or random.choice([True, False])

            # Thời gian tạo
            days_ago = random.choice([0, 0, 0, 1, 1, 2, 3, 4])
            created_time = today - timedelta(days=days_ago, hours=random.randint(1, 10), minutes=random.randint(5, 50))

            shipping = Decimal('15000') if otype == 'delivery' else Decimal('0')
            discount_val = Decimal('10000') if random.random() < 0.25 else Decimal('0')

            order = Order(
                customer_name=cust_name,
                customer_contact=cust_contact,
                address=addr,
                order_type=otype,
                payment_method=pmethod,
                is_paid=is_paid,
                status=status,
                discount_type='amount',
                discount_value=discount_val,
                shipping_fee=shipping,
                note='Đơn mẫu kiểm thử' if random.random() < 0.4 else '',
            )
            order.save()
            # Cập nhật created_at về ngày mong muốn
            Order.objects.filter(pk=order.pk).update(created_at=created_time)

            # Chọn 1-3 món cho đơn
            selected_products = random.sample(products, k=random.randint(1, min(3, len(products))))
            for prod in selected_products:
                qty = random.randint(1, 3)
                note_item = "Mix dưa hấu, xoài, táo" if prod.is_combo else ("Thêm muối ớt" if random.random() < 0.3 else "")
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    product_name=prod.name,
                    unit_price=prod.price,
                    quantity=qty,
                    note=note_item
                )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Đã tạo thành công {count} đơn hàng mẫu đa dạng!'))
