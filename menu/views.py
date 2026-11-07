from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from .models import Product
from .forms import ProductForm
from orders.customer_views import cart_count

def client_home(request):
    """
    Trang chủ công khai cho khách hàng: Xem menu các món còn hàng
    """
    products = Product.objects.filter(is_available=True)
    return render(request, 'client/home.html', {
        'products': products,
        'cart_count': cart_count(request),
    })

@login_required
def product_list(request):
    """
    Danh sách toàn bộ món trong menu (bao gồm cả còn hàng và hết hàng),
    có tìm kiếm và lọc.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    
    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if status_filter == 'available':
        products = products.filter(is_available=True)
    elif status_filter == 'unavailable':
        products = products.filter(is_available=False)
    elif status_filter == 'combo':
        products = products.filter(is_combo=True)

    # Thống kê nhanh
    total_count = Product.objects.count()
    available_count = Product.objects.filter(is_available=True).count()
    unavailable_count = total_count - available_count

    context = {
        'products': products,
        'query': query,
        'status_filter': status_filter,
        'total_count': total_count,
        'available_count': available_count,
        'unavailable_count': unavailable_count,
    }
    return render(request, 'menu/product_list.html', context)


@login_required
def product_create(request):
    """
    Thêm món mới vào menu
    """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Đã thêm món "{product.name}" vào menu thành công!')
            return redirect('menu:product_list')
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin nhập!')
    else:
        form = ProductForm()

    return render(request, 'menu/product_form.html', {
        'form': form,
        'title': 'Thêm món mới vào Menu',
        'btn_text': 'Lưu món mới',
    })


@login_required
def product_update(request, pk):
    """
    Chỉnh sửa thông tin món
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Đã cập nhật món "{product.name}" thành công!')
            return redirect('menu:product_list')
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin nhập!')
    else:
        form = ProductForm(instance=product)

    return render(request, 'menu/product_form.html', {
        'form': form,
        'product': product,
        'title': f'Chỉnh sửa món: {product.name}',
        'btn_text': 'Lưu thay đổi',
    })


@login_required
def product_delete(request, pk):
    """
    Xóa món khỏi menu
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Đã xóa món "{product_name}" khỏi menu!')
        return redirect('menu:product_list')

    return render(request, 'menu/product_confirm_delete.html', {'product': product})


@login_required
def product_toggle_status(request, pk):
    """
    Bật / Tắt trạng thái Còn hàng / Hết hàng ngay tại danh sách
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_available = not product.is_available
        product.save()

        status_text = "Còn hàng" if product.is_available else "Hết hàng"

        # Nếu là request AJAX fetch từ giao diện
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'is_available': product.is_available,
                'message': f'Đã đổi trạng thái sang: {status_text}'
            })

        messages.success(request, f'Đã chuyển món "{product.name}" sang trạng thái: {status_text}')
    
    return redirect('menu:product_list')
