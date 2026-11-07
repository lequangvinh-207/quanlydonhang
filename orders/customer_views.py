from decimal import Decimal
import hashlib
import re

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from menu.models import Product
from .forms import CustomerOrderForm
from .models import Order, OrderItem


def _shipping_fee():
    fee = Decimal(str(settings.SHOP_SHIPPING_FEE))
    if fee < 0:
        raise ValueError('SHOP_SHIPPING_FEE must not be negative.')
    return fee


def _cart(request):
    """Đọc và chuẩn hóa giỏ hàng lưu trong session."""
    raw_cart = request.session.get('cart', {})
    if not isinstance(raw_cart, dict):
        request.session['cart'] = {}
        return {}

    cart = {}
    for product_id, item in raw_cart.items():
        if not isinstance(item, dict):
            continue
        try:
            parsed_id = int(product_id)
            quantity = item.get('quantity')
        except (TypeError, ValueError):
            continue
        note = item.get('note', '')
        salt_choice = item.get('salt_choice', '')
        if (
            parsed_id < 1
            or isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or not 1 <= quantity <= 50
            or not (
                isinstance(note, str)
                or isinstance(note, list) and all(isinstance(value, str) for value in note)
            )
            or not isinstance(salt_choice, str)
        ):
            continue
        if salt_choice not in dict(OrderItem.SALT_CHOICES) and salt_choice != '':
            salt_choice = ''
        if isinstance(note, str):
            note = note[:255]
        else:
            note = [value[:255] for value in note[:50]]
        cart[str(parsed_id)] = {'quantity': quantity, 'note': note, 'salt_choice': salt_choice}

    if cart != raw_cart:
        request.session['cart'] = cart
    return cart


def cart_count(request):
    return sum(item['quantity'] for item in _cart(request).values())


def _cart_context(request):
    cart = _cart(request)
    products = Product.objects.filter(pk__in=[int(key) for key in cart]).in_bulk()
    rows = []
    subtotal = Decimal('0')
    for product_id, item in cart.items():
        product = products.get(int(product_id))
        line_total = product.price * item['quantity'] if product else Decimal('0')
        subtotal += line_total
        note = item['note']
        notes = []
        if product and product.is_combo:
            notes = note if isinstance(note, list) else [note]
            notes = (notes + [''] * item['quantity'])[:item['quantity']]
        elif isinstance(note, list):
            note = note[0] if note else ''
        rows.append({
            'product_id': int(product_id),
            'product': product,
            'quantity': item['quantity'],
            'note': note,
            'notes': notes,
            'salt_choice': item['salt_choice'],
            'line_total': line_total,
        })
    shipping_fee = _shipping_fee()
    return {
        'cart_rows': rows,
        'cart_count': sum(item['quantity'] for item in cart.values()),
        'cart_subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'final_total': subtotal + shipping_fee,
    }


def cart_view(request):
    return render(request, 'client/cart.html', _cart_context(request))


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_available=True)
    cart = _cart(request)
    key = str(product.pk)
    existing = cart.get(key, {
        'quantity': 0,
        'note': [] if product.is_combo else '',
        'salt_choice': '',
    })
    current_quantity = existing['quantity']
    if current_quantity >= 50:
        messages.error(request, 'Mỗi món chỉ có thể đặt tối đa 50 hộp.')
    else:
        note = existing['note']
        if product.is_combo:
            note = note if isinstance(note, list) else [note] * current_quantity
            note.append('')
        cart[key] = {
            'quantity': current_quantity + 1,
            'note': note,
            'salt_choice': existing.get('salt_choice', ''),
        }
        request.session['cart'] = cart
        messages.success(request, f'Đã thêm "{product.name}" vào giỏ hàng.')
    return redirect('client_home')


@require_POST
def cart_update(request, product_id):
    cart = _cart(request)
    key = str(product_id)
    if key not in cart:
        messages.error(request, 'Món này không có trong giỏ hàng.')
        return redirect('customer_orders:cart')

    try:
        quantity = int(request.POST.get('quantity', ''))
    except (TypeError, ValueError):
        quantity = 0
    if not 1 <= quantity <= 50:
        messages.error(request, 'Số lượng mỗi món phải từ 1 đến 50.')
    else:
        salt_choice = request.POST.get('salt_choice', '')
        if salt_choice not in dict(OrderItem.SALT_CHOICES) and salt_choice != '':
            messages.error(request, 'Loại muối không hợp lệ.')
            return redirect('customer_orders:cart')
        product = Product.objects.filter(pk=product_id).first()
        if product and product.is_combo:
            notes = request.POST.getlist('notes')
            if len(notes) != quantity or any(len(note) > 255 for note in notes):
                messages.error(request, 'Vui lòng nhập ghi chú riêng cho từng hộp mix (tối đa 255 ký tự mỗi hộp).')
                return redirect('customer_orders:cart')
            note = [value.strip() for value in notes]
        else:
            note = request.POST.get('note', '')
            if len(note) > 255:
                messages.error(request, 'Ghi chú món không được dài quá 255 ký tự.')
                return redirect('customer_orders:cart')
            note = note.strip()
        cart[key] = {
            'quantity': quantity,
            'note': note if isinstance(note, list) else note.strip(),
            'salt_choice': salt_choice,
        }
        request.session['cart'] = cart
        messages.success(request, 'Đã cập nhật giỏ hàng.')
    return redirect('customer_orders:cart')


@require_POST
def cart_remove(request, product_id):
    cart = _cart(request)
    cart.pop(str(product_id), None)
    request.session['cart'] = cart
    messages.success(request, 'Đã xóa món khỏi giỏ hàng.')
    return redirect('customer_orders:cart')


def checkout(request):
    context = _cart_context(request)
    if not context['cart_rows']:
        messages.info(request, 'Giỏ hàng đang trống. Hãy chọn món trước khi đặt hàng.')
        return redirect('client_home')

    form = CustomerOrderForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if form.cleaned_data['website']:
            return render(request, 'client/checkout.html', {
                **context,
                'form': CustomerOrderForm(),
                'checkout_url': reverse('customer_orders:checkout'),
            }, status=400)

        cart = _cart(request)
        product_ids = [int(product_id) for product_id in cart]
        available_products = Product.objects.filter(
            pk__in=product_ids,
            is_available=True,
        ).in_bulk()
        if len(available_products) != len(cart):
            messages.error(request, 'Một số món đã hết hàng hoặc không còn tồn tại. Vui lòng kiểm tra giỏ hàng.')
            return redirect('customer_orders:cart')

        client_ip = request.META.get('REMOTE_ADDR', '')
        ip_digest = hashlib.sha256(client_ip.encode('utf-8')).hexdigest()
        rate_key = f'shop:order-rate:{ip_digest}'
        rate_window = settings.SHOP_ORDER_RATE_WINDOW
        cache.add(rate_key, 0, timeout=rate_window)
        order_count = cache.incr(rate_key)
        if order_count > settings.SHOP_ORDER_RATE_LIMIT:
            messages.error(request, 'Bạn đã đặt quá nhiều đơn trong thời gian ngắn. Vui lòng thử lại sau.')
            context.update({
                'form': form,
                'checkout_url': reverse('customer_orders:checkout'),
            })
            return render(request, 'client/checkout.html', context, status=429)

        with transaction.atomic():
            available_products = Product.objects.select_for_update().filter(
                pk__in=product_ids,
                is_available=True,
            ).in_bulk()
            if len(available_products) != len(cart):
                messages.error(request, 'Một số món đã hết hàng hoặc không còn tồn tại. Vui lòng kiểm tra giỏ hàng.')
                return redirect('customer_orders:cart')

            order_items = []
            for product in available_products.values():
                item = cart[str(product.pk)]
                if product.is_combo:
                    notes = item['note']
                    if isinstance(notes, str):
                        notes = [notes] + [''] * (item['quantity'] - 1)
                    if len(notes) != item['quantity']:
                        messages.error(request, 'Vui lòng kiểm tra ghi chú cho từng hộp mix trong giỏ hàng.')
                        return redirect('customer_orders:cart')
                    order_items.extend(
                        OrderItem(
                            product=product,
                            product_name=product.name,
                            unit_price=product.price,
                            unit_cost_price=product.cost_price,
                            quantity=1,
                            note=note,
                            salt_choice=item.get('salt_choice', ''),
                        )
                        for note in notes
                    )
                else:
                    note = item['note']
                    if isinstance(note, list):
                        note = note[0] if note else ''
                    order_items.append(OrderItem(
                        product=product,
                        product_name=product.name,
                        unit_price=product.price,
                        unit_cost_price=product.cost_price,
                        quantity=item['quantity'],
                        note=note,
                        salt_choice=item.get('salt_choice', ''),
                    ))

            order = Order.objects.create(
                customer_name=form.cleaned_data['customer_name'],
                customer_contact=form.cleaned_data['customer_contact'],
                address=form.cleaned_data['address'],
                order_type='delivery',
                payment_method='cod',
                is_paid=False,
                status='new',
                discount_type='amount',
                discount_value=0,
                shipping_fee=_shipping_fee(),
                note=form.cleaned_data['note'],
                source='web',
                desired_time=form.cleaned_data['desired_time'],
            )
            for item in order_items:
                item.order = order
            OrderItem.objects.bulk_create(order_items)

        request.session['cart'] = {}
        request.session['checkout_order_code'] = order.code
        return redirect('customer_orders:order_success', code=order.code)

    context['form'] = form
    context['checkout_url'] = reverse('customer_orders:checkout')
    return render(request, 'client/checkout.html', context)


def order_lookup(request):
    order = None
    not_found = False
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        phone = re.sub(r'[\s().-]', '', request.POST.get('phone', ''))
        if len(code) == 8 and len(phone) <= 20 and re.fullmatch(r'HQ[A-HJ-NP-Z2-9]{6}', code) and re.fullmatch(
            r'(?:\+?84|0)(?:3|5|7|8|9)\d{8}', phone
        ):
            order = Order.objects.filter(
                code=code,
                customer_contact=phone,
                source='web',
            ).only('code', 'status', 'created_at').first()
        if order is None:
            not_found = True
    return render(request, 'client/order_lookup.html', {
        'order': order,
        'not_found': not_found,
        'code_value': request.POST.get('code', '').strip(),
    })


def order_success(request, code):
    if request.session.get('checkout_order_code') != code:
        raise Http404('Không tìm thấy đơn hàng.')
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        code=code,
        source='web',
    )
    return render(request, 'client/order_success.html', {'order': order})
