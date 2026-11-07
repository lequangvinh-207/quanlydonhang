import json
from json import JSONDecodeError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from datetime import timedelta

from menu.models import Product
from .models import Order, OrderItem
from .forms import OrderCreateForm, OrderUpdateForm

@login_required
def order_create(request):
    """
    Màn hình bán hàng POS & Tạo đơn hàng:
    Bên trái là menu hoa quả còn hàng, bên phải là giỏ hàng & thông tin khách
    """
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if not form.is_valid():
            messages.error(request, f'Vui lòng kiểm tra thông tin đơn hàng: {form.errors.as_text()}')
            return redirect('orders:order_create')

        try:
            cart_items = json.loads(request.POST.get('cart_data', '[]'))
        except JSONDecodeError:
            messages.error(request, 'Dữ liệu giỏ hàng không hợp lệ. Vui lòng tạo lại đơn.')
            return redirect('orders:order_create')

        if not isinstance(cart_items, list) or not cart_items:
            messages.error(request, 'Giỏ hàng đang trống hoặc không hợp lệ. Vui lòng chọn món.')
            return redirect('orders:order_create')

        validated_items = []
        for item in cart_items:
            if not isinstance(item, dict):
                messages.error(request, 'Một món trong giỏ hàng không hợp lệ.')
                return redirect('orders:order_create')

            product_id = item.get('product_id')
            quantity = item.get('quantity')
            note = item.get('note', '')
            if (
                isinstance(product_id, bool) or not isinstance(product_id, int)
                or isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1
                or not isinstance(note, str) or len(note) > 255
            ):
                messages.error(request, 'Món hàng có mã, số lượng hoặc ghi chú không hợp lệ.')
                return redirect('orders:order_create')

            product = Product.objects.filter(pk=product_id, is_available=True).first()
            if product is None:
                messages.error(request, 'Có món trong giỏ đã hết hàng hoặc không còn tồn tại. Vui lòng kiểm tra lại.')
                return redirect('orders:order_create')

            validated_items.append((product, quantity, note.strip()))

        with transaction.atomic():
            order = Order.objects.create(**form.cleaned_data, status='new', source='message')
            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    unit_cost_price=product.cost_price,
                    quantity=quantity,
                    note=note,
                )
                for product, quantity, note in validated_items
            ])

        messages.success(request, f'Tạo đơn hàng #{order.code} thành công!')
        return redirect('orders:order_invoice', pk=order.pk)

    # GET: Tải danh sách món còn hàng để chọn
    available_products = Product.objects.filter(is_available=True).order_by('name')
    context = {
        'products': available_products,
        'title': 'Màn hình Bán hàng (POS)',
    }
    return render(request, 'orders/order_create.html', context)


@login_required
def order_list(request):
    """
    Quản lý danh sách đơn hàng có tìm kiếm và bộ lọc nâng cao
    """
    orders = Order.objects.prefetch_related('items').order_by(
        Case(
            When(status='new', then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
        '-created_at',
    )

    # Bộ lọc tìm kiếm từ khóa
    query = request.GET.get('q', '').strip()
    if query:
        orders = orders.filter(
            Q(code__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(customer_contact__icontains=query)
        )

    # Lọc theo trạng thái
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)

    # Lọc theo hình thức
    type_filter = request.GET.get('order_type', 'all')
    if type_filter != 'all':
        orders = orders.filter(order_type=type_filter)

    # Lọc theo thanh toán
    payment_status = request.GET.get('is_paid', 'all')
    if payment_status == 'paid':
        orders = orders.filter(is_paid=True)
    elif payment_status == 'unpaid':
        orders = orders.filter(is_paid=False)

    # Lọc theo ngày
    date_filter = request.GET.get('date_filter', 'all')
    today = timezone.localdate()

    if date_filter == 'today':
        orders = orders.filter(created_at__date=today)
    elif date_filter == 'yesterday':
        orders = orders.filter(created_at__date=today - timedelta(days=1))
    elif date_filter == '7days':
        orders = orders.filter(created_at__date__gte=today - timedelta(days=7))
    elif date_filter == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        if end_date:
            orders = orders.filter(created_at__date__lte=end_date)

    # Thống kê nhanh theo bộ lọc
    total_orders = orders.count()
    total_revenue = sum(o.final_total for o in orders if o.status == 'completed')
    orders = list(orders)
    for order in orders:
        order.phone_link = order.customer_contact if order.customer_contact.isdigit() else ''

    context = {
        'orders': orders,
        'query': query,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'payment_status': payment_status,
        'date_filter': date_filter,
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'latest_new_order_id': Order.objects.filter(status='new').order_by('-created_at').values_list('id', flat=True).first() or '',
        'new_order_count': Order.objects.filter(status='new').count(),
    }
    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail(request, pk):
    """
    Xem chi tiết đơn hàng
    """
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=pk)
    order.phone_link = order.customer_contact if order.customer_contact.isdigit() else ''
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def order_invoice(request, pk):
    """
    Trang xem và in hóa đơn đẹp mắt, chuẩn kích thước in
    """
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=pk)
    order.phone_link = order.customer_contact if order.customer_contact.isdigit() else ''
    return render(request, 'orders/order_invoice.html', {'order': order})


@login_required
def order_update(request, pk):
    """
    Chỉnh sửa thông tin đơn hàng
    """
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật đơn hàng #{order.code}!')
            return redirect('orders:order_detail', pk=order.pk)
    else:
        form = OrderUpdateForm(instance=order)

    return render(request, 'orders/order_edit.html', {'form': form, 'order': order})


@login_required
def order_change_status(request, pk):
    """
    Chuyển trạng thái đơn hàng nhanh 1 chạm (POST)
    """
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = dict(Order.STATUS_CHOICES).keys()
        
        if new_status in valid_statuses:
            order.status = new_status
            order.save()
            
            status_display = order.get_status_display()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'status': order.status,
                    'status_display': status_display,
                    'is_paid': order.is_paid,
                    'message': f'Đã chuyển trạng thái sang: {status_display}'
                })
            messages.success(request, f'Đã cập nhật đơn #{order.code} sang "{status_display}"!')
        else:
            messages.error(request, 'Trạng thái không hợp lệ!')

    return redirect(request.META.get('HTTP_REFERER') or 'orders:order_list')


@login_required
def order_cancel(request, pk):
    """
    Hủy đơn hàng
    """
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.status = 'cancelled'
        order.save()
        messages.success(request, f'Đã hủy đơn hàng #{order.code}!')
        return redirect('orders:order_list')

    return render(request, 'orders/order_confirm_cancel.html', {'order': order})


@login_required
def order_mark_paid(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method != 'POST':
        return redirect('orders:order_list')

    payment_method = request.POST.get('payment_method')
    if request.POST.get('is_paid') != 'on':
        messages.error(request, 'Đánh dấu đã thanh toán để xác nhận đã thu tiền.')
    elif payment_method not in {'cash', 'transfer'}:
        messages.error(request, 'Vui lòng chọn tiền mặt hoặc chuyển khoản để xác nhận đã thu tiền.')
    elif order.status in {'cancelled', 'customer_refused'}:
        messages.error(request, 'Không thể xác nhận đã thu tiền cho đơn đã hủy hoặc khách không nhận.')
    else:
        order.is_paid = True
        order.payment_method = payment_method
        order.save(update_fields=['is_paid', 'payment_method', 'updated_at'])
        messages.success(request, f'Đã ghi nhận thu tiền đơn #{order.code}.')
    return redirect(request.META.get('HTTP_REFERER') or 'orders:order_list')


@login_required
def order_print_slip(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=pk)
    order.phone_link = order.customer_contact if order.customer_contact.isdigit() else ''
    return render(request, 'orders/order_print_slip.html', {'order': order})
