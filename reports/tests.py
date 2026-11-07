from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from io import BytesIO
import openpyxl
from orders.models import Order, OrderItem
from menu.models import Product

class ReportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='password123')
        self.p = Product.objects.create(name='Xoài', price=Decimal('25000'), cost_price=Decimal('12000'))
        self.o = Order.objects.create(customer_name='Khách A', status='completed', is_paid=True)
        OrderItem.objects.create(order=self.o, product=self.p, product_name='Xoài', unit_price=Decimal('25000'), quantity=2)

    def test_dashboard_requires_login(self):
        """Dashboard yêu cầu đăng nhập"""
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/quan-ly/dang-nhap/', response.url)

    def test_dashboard_authenticated(self):
        """Đã đăng nhập xem được dashboard"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Báo Cáo & Thống Kê')

    def test_export_excel_authenticated(self):
        """Đã đăng nhập xuất được excel"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('reports:export_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_top_item_revenue_sums_each_sale_price_and_quantity(self):
        self.client.force_login(self.user)
        second_order = Order.objects.create(customer_name='Khách B', status='completed')
        OrderItem.objects.create(
            order=second_order,
            product=self.p,
            product_name='Xoài',
            unit_price=Decimal('30000'),
            quantity=1,
        )

        response = self.client.get(reverse('reports:dashboard'), {'preset': 'today'})

        self.assertEqual(response.status_code, 200)
        item = response.context['top_items'][0]
        self.assertEqual(item['name'], 'Xoài')
        self.assertEqual(item['subtotal'], Decimal('80000'))

    def test_dashboard_and_excel_only_count_completed_revenue(self):
        unpaid_completed = Order.objects.create(
            customer_name='Khách chưa thu',
            status='completed',
            is_paid=False,
        )
        OrderItem.objects.create(
            order=unpaid_completed,
            product=self.p,
            product_name='Xoài',
            unit_price=Decimal('30000'),
            quantity=1,
        )
        new_order = Order.objects.create(customer_name='Đơn mới', status='new', is_paid=False)
        OrderItem.objects.create(
            order=new_order,
            product=self.p,
            product_name='Xoài',
            unit_price=Decimal('90000'),
            quantity=1,
        )
        self.client.force_login(self.user)

        dashboard = self.client.get(reverse('reports:dashboard'), {'preset': 'today'})
        self.assertEqual(dashboard.context['today_revenue'], Decimal('80000'))
        self.assertEqual(dashboard.context['unpaid_count'], 1)
        self.assertEqual(dashboard.context['unpaid_total'], Decimal('30000'))

        response = self.client.get(reverse('reports:export_excel'))
        workbook = openpyxl.load_workbook(BytesIO(response.content), data_only=True)
        sheet = workbook.active
        summary_row = sheet.max_row
        self.assertEqual(sheet.cell(row=summary_row, column=12).value, 80000)
        self.assertEqual(sheet.cell(row=summary_row, column=13).value, 36000)
