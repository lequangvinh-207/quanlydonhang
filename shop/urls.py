from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from menu.views import client_home


@login_required
def manager_home(request):
    return redirect('orders:order_list')


urlpatterns = [
    # 1. Đổi đường dẫn admin mặc định thành /quan-ly-admin/
    path('quan-ly-admin/', admin.site.urls),

    # 2. Xác thực đăng nhập / đăng xuất khu quản lý
    path('quan-ly/dang-nhap/', auth_views.LoginView.as_view(template_name='manager/login.html'), name='manager_login'),
    path(
        'quan-ly/dang-xuat/',
        login_required(auth_views.LogoutView.as_view(next_page='/quan-ly/dang-nhap/')),
        name='manager_logout',
    ),

    # 3. Khu quản trị (Tiền tố /quan-ly/)
    path('quan-ly/', manager_home, name='manager_home'),
    path('quan-ly/menu/', include('menu.urls')),
    path('quan-ly/don-hang/', include('orders.urls')),
    path('quan-ly/bao-cao/', include('reports.urls')),

    # 4. Khu khách hàng công khai
    path('', include('orders.customer_urls')),
    path('', client_home, name='client_home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
