from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from decimal import Decimal
from django.test import override_settings
import json
from datetime import timedelta
from django.utils import timezone
from menu.models import Product
from orders.models import Order, OrderItem

class OrderTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='password123')
        self.product = Product.objects.create(
            name='Dưa hấu cắt sẵn',
            price=Decimal('25000'),
            cost_price=Decimal('10000'),
            is_available=True,
            is_combo=False
        )

    def test_manager_order_list_requires_login(self):
        """Khu quản lý đơn hàng yêu cầu đăng nhập"""
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/quan-ly/dang-nhap/', response.url)

    def test_manager_order_create_authenticated(self):
        """Tạo đơn thủ công trong khu quản lý khi đã đăng nhập"""
        self.client.force_login(self.user)
        url = reverse('orders:order_create')
        cart_data = json.dumps([{
            'product_id': self.product.id,
            'name': 'Tên bị sửa từ trình duyệt',
            'price': 1,
            'quantity': 2,
            'note': 'Ít đá',
        }])

        response = self.client.post(url, {
            'customer_name': 'Nguyễn Văn A',
            'customer_contact': '0912345678',
            'order_type': 'dine_in',
            'payment_method': 'cash',
            'is_paid': 'on',
            'cart_data': cart_data,
            'discount_type': 'amount',
            'discount_value': '0',
            'shipping_fee': '0',
            'note': '',
        })

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(customer_name='Nguyễn Văn A')
        self.assertEqual(order.source, 'message')
        item = order.items.get()
        self.assertEqual(item.product_name, self.product.name)
        self.assertEqual(item.unit_price, Decimal('25000'))
        self.assertEqual(item.unit_cost_price, Decimal('10000'))
        self.product.cost_price = Decimal('18000')
        self.product.save(update_fields=['cost_price'])
        self.assertEqual(order.total_cost, Decimal('20000'))

    def test_manager_order_list_prioritizes_new_orders(self):
        self.client.force_login(self.user)
        older_order = Order.objects.create(customer_name='Đơn cũ', status='preparing')
        new_order = Order.objects.create(customer_name='Đơn mới', status='new')
        Order.objects.filter(pk=older_order.pk).update(created_at=timezone.now())
        Order.objects.filter(pk=new_order.pk).update(created_at=timezone.now() - timedelta(days=1))

        response = self.client.get(reverse('orders:order_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([order.pk for order in response.context['orders']], [new_order.pk, older_order.pk])
        self.assertEqual(response.context['new_order_count'], 1)
        self.assertContains(response, 'data-latest-new-order-id')
        self.assertContains(response, 'table-warning')

    def test_completed_status_does_not_mark_order_paid_and_payment_is_explicit(self):
        self.client.force_login(self.user)
        order = Order.objects.create(customer_name='Khách A', status='new', is_paid=False)

        self.client.post(reverse('orders:order_change_status', args=[order.pk]), {'status': 'completed'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')
        self.assertFalse(order.is_paid)

        self.client.post(reverse('orders:order_mark_paid', args=[order.pk]), {
            'payment_method': 'cash',
        })
        order.refresh_from_db()
        self.assertFalse(order.is_paid)

        self.client.post(reverse('orders:order_mark_paid', args=[order.pk]), {
            'is_paid': 'on',
            'payment_method': 'transfer',
        })
        order.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(order.payment_method, 'transfer')

    def test_print_slip_requires_login_and_renders_order_summary(self):
        order = Order.objects.create(customer_name='Khách In', status='new', is_paid=False)
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1,
        )
        url = reverse('orders:order_print_slip', args=[order.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.code)
        self.assertContains(response, 'CẦN THU:')

    def test_order_create_rejects_non_positive_quantity(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('orders:order_create'), {
            'customer_name': 'Khách A',
            'order_type': 'dine_in',
            'payment_method': 'cash',
            'discount_type': 'amount',
            'discount_value': '0',
            'shipping_fee': '0',
            'cart_data': json.dumps([{
                'product_id': self.product.id,
                'quantity': 0,
                'note': '',
            }]),
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.exists())


class CustomerOrderTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        self.user = User.objects.create_user(username='admin', password='password123')
        self.product = Product.objects.create(
            name='Hộp mix',
            price=Decimal('25000'),
            cost_price=Decimal('12000'),
            is_available=True,
            is_combo=True,
        )
        self.unavailable = Product.objects.create(
            name='Táo hết hàng',
            price=Decimal('30000'),
            is_available=False,
        )

    def test_customer_menu_only_shows_available_products(self):
        response = self.client.get(reverse('client_home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hộp mix')
        self.assertNotContains(response, 'Táo hết hàng')

    def test_cart_add_update_and_remove(self):
        add_url = reverse('customer_orders:cart_add', args=[self.product.pk])
        self.assertEqual(self.client.post(add_url).status_code, 302)
        self.client.post(add_url)
        response = self.client.get(reverse('customer_orders:cart'))
        self.assertEqual(response.context['cart_count'], 2)
        self.assertContains(response, 'Loại quả muốn mix')
        self.assertContains(response, 'Muối Tây Ninh')
        self.assertContains(response, 'Muối Hảo Hảo')

        update_url = reverse('customer_orders:cart_update', args=[self.product.pk])
        self.client.post(update_url, {'quantity': '51', 'notes': ['Xoài', 'Táo']})
        self.assertEqual(self.client.session['cart'][str(self.product.pk)]['quantity'], 2)

        self.client.post(update_url, {
            'quantity': '3',
            'notes': ['Xoài', 'Dưa hấu', 'Nho'],
            'salt_choice': 'hao_hao',
        })
        self.assertEqual(self.client.session['cart'][str(self.product.pk)]['quantity'], 3)
        self.assertEqual(
            self.client.session['cart'][str(self.product.pk)]['note'],
            ['Xoài', 'Dưa hấu', 'Nho'],
        )
        self.assertEqual(
            self.client.session['cart'][str(self.product.pk)]['salt_choice'],
            'hao_hao',
        )

        remove_url = reverse('customer_orders:cart_remove', args=[self.product.pk])
        self.client.post(remove_url)
        self.assertEqual(self.client.session['cart'], {})

    @override_settings(SHOP_SHIPPING_FEE=5000)
    def test_guest_checkout_creates_cod_order_from_database_prices(self):
        session = self.client.session
        session['cart'] = {
            str(self.product.pk): {
                'quantity': 2,
                'note': ['Xoài', 'Dưa hấu'],
                'salt_choice': 'tay_ninh',
                'price': '1',
            },
        }
        session.save()

        response = self.client.post(reverse('customer_orders:checkout'), {
            'customer_name': 'Nguyễn Văn A',
            'customer_contact': ' 0912-345-678 ',
            'address': 'Số 1, Hà Nội',
            'note': 'Gọi trước khi giao',
            'desired_time': '18:00',
        })

        order = Order.objects.get()
        items = list(order.items.order_by('id'))
        self.assertRedirects(
            response,
            reverse('customer_orders:order_success', args=[order.code]),
        )
        self.assertEqual(order.customer_contact, '0912345678')
        self.assertEqual(order.order_type, 'delivery')
        self.assertEqual(order.payment_method, 'cod')
        self.assertFalse(order.is_paid)
        self.assertEqual(order.status, 'new')
        self.assertEqual(order.source, 'web')
        self.assertEqual(order.desired_time, '18:00')
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item.product_name == 'Hộp mix' for item in items))
        self.assertTrue(all(item.unit_price == Decimal('25000') for item in items))
        self.assertTrue(all(item.quantity == 1 for item in items))
        self.assertEqual([item.note for item in items], ['Xoài', 'Dưa hấu'])
        self.assertEqual([item.salt_choice for item in items], ['tay_ninh', 'tay_ninh'])
        self.assertEqual(order.final_total, Decimal('55000'))
        self.assertEqual(self.client.session['cart'], {})

        success = self.client.get(response.url)
        self.assertContains(success, 'Thanh toán khi nhận hàng.')
        self.assertContains(success, '55.000đ')
        self.assertContains(success, 'Muối Tây Ninh')
        self.assertNotContains(success, 'Chuyển khoản')

    def test_checkout_rejects_invalid_phone_and_required_address(self):
        session = self.client.session
        session['cart'] = {
            str(self.product.pk): {'quantity': 1, 'note': ''},
        }
        session.save()

        response = self.client.post(reverse('customer_orders:checkout'), {
            'customer_name': 'Nguyễn Văn A',
            'customer_contact': '123',
            'address': ' ',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertContains(response, 'số điện thoại di động Việt Nam hợp lệ')
        self.assertTrue(response.context['form'].has_error('address'))

    def test_checkout_rejects_item_that_became_unavailable(self):
        session = self.client.session
        session['cart'] = {
            str(self.product.pk): {'quantity': 1, 'note': ''},
        }
        session.save()
        self.product.is_available = False
        self.product.save(update_fields=['is_available'])

        response = self.client.post(reverse('customer_orders:checkout'), {
            'customer_name': 'Nguyễn Văn A',
            'customer_contact': '0912345678',
            'address': 'Số 1, Hà Nội',
        })

        self.assertRedirects(response, reverse('customer_orders:cart'))
        self.assertFalse(Order.objects.exists())

    def test_order_success_only_available_to_originating_session(self):
        order = Order.objects.create(
            customer_name='Khách riêng',
            customer_contact='0912345678',
            address='Địa chỉ riêng',
            order_type='delivery',
            payment_method='cod',
            source='web',
        )

        self.assertEqual(
            self.client.get(reverse('customer_orders:order_success', args=[order.code])).status_code,
            404,
        )

    def test_public_order_lookup_requires_matching_code_and_phone(self):
        order = Order.objects.create(
            customer_name='Khách riêng',
            customer_contact='0912345678',
            address='Địa chỉ riêng',
            order_type='delivery',
            payment_method='cod',
            status='preparing',
            source='web',
        )
        url = reverse('customer_orders:lookup')

        response = self.client.post(url, {
            'code': order.code.lower(),
            'phone': '0912 345 678',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['order'].code, order.code)
        self.assertContains(response, 'Đang chuẩn bị')
        self.assertNotContains(response, 'Địa chỉ riêng')
        self.assertNotContains(response, 'Khách riêng')

        response = self.client.post(url, {
            'code': order.code,
            'phone': '0987654321',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Không tìm thấy đơn')
        self.assertIsNone(response.context['order'])

    def test_checkout_honeypot_does_not_create_order(self):
        session = self.client.session
        session['cart'] = {
            str(self.product.pk): {'quantity': 1, 'note': ''},
        }
        session.save()

        response = self.client.post(reverse('customer_orders:checkout'), {
            'customer_name': 'Nguyễn Văn A',
            'customer_contact': '0912345678',
            'address': 'Số 1, Hà Nội',
            'website': 'spam.example',
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    @override_settings(SHOP_ORDER_RATE_LIMIT=1, SHOP_ORDER_RATE_WINDOW=3600)
    def test_checkout_rate_limits_orders_by_ip(self):
        checkout_url = reverse('customer_orders:checkout')
        order_data = {
            'customer_name': 'Nguyễn Văn A',
            'customer_contact': '0912345678',
            'address': 'Số 1, Hà Nội',
        }
        session = self.client.session
        session['cart'] = {str(self.product.pk): {'quantity': 1, 'note': ''}}
        session.save()
        first_response = self.client.post(checkout_url, order_data)
        self.assertRedirects(
            first_response,
            reverse('customer_orders:order_success', args=[Order.objects.get().code]),
        )

        session = self.client.session
        session['cart'] = {str(self.product.pk): {'quantity': 1, 'note': ''}}
        session.save()
        second_response = self.client.post(checkout_url, order_data)

        self.assertEqual(second_response.status_code, 429)
        self.assertEqual(Order.objects.count(), 1)
        self.assertContains(second_response, 'đặt quá nhiều đơn', status_code=429)

    def test_order_create_rejects_unavailable_product(self):
        self.client.force_login(self.user)
        self.product.is_available = False
        self.product.save(update_fields=['is_available'])

        response = self.client.post(reverse('orders:order_create'), {
            'customer_name': 'Khách A',
            'order_type': 'dine_in',
            'payment_method': 'cash',
            'discount_type': 'amount',
            'discount_value': '0',
            'shipping_fee': '0',
            'cart_data': json.dumps([{
                'product_id': self.product.id,
                'quantity': 1,
                'note': '',
            }]),
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.exists())

    def test_order_create_rejects_invalid_percentage_discount(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('orders:order_create'), {
            'customer_name': 'Khách A',
            'order_type': 'dine_in',
            'payment_method': 'cash',
            'discount_type': 'percent',
            'discount_value': '101',
            'shipping_fee': '0',
            'cart_data': json.dumps([{
                'product_id': self.product.id,
                'quantity': 1,
                'note': '',
            }]),
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.exists())
