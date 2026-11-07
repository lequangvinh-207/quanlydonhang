from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from menu.models import Product

class ProductTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='password123')
        self.p1 = Product.objects.create(
            name='Dưa hấu cắt sẵn',
            price=Decimal('25000'),
            cost_price=Decimal('10000'),
            is_available=True,
            is_combo=False
        )

    def test_client_home_public(self):
        """Khách không cần đăng nhập vẫn xem được menu trang chủ"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dưa hấu cắt sẵn')
        self.assertContains(response, reverse('customer_orders:cart_add', args=[self.p1.pk]))

    def test_manager_menu_requires_login(self):
        """Chưa đăng nhập thì bị chuyển về trang đăng nhập /quan-ly/dang-nhap/"""
        response = self.client.get(reverse('menu:product_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/quan-ly/dang-nhap/', response.url)

    def test_manager_root_requires_login(self):
        response = self.client.get('/quan-ly/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/quan-ly/dang-nhap/', response.url)

    def test_admin_uses_management_admin_path(self):
        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/quan-ly-admin/login/'))

    def test_admin_pages_use_square_corners(self):
        response = self.client.get('/quan-ly-admin/login/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'border-radius: 0 !important;')

    def test_manager_menu_authenticated(self):
        """Đã đăng nhập thì truy cập quản lý menu bình thường"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('menu:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dưa hấu cắt sẵn')
