from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from datetime import datetime, timedelta
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from orders.models import Order, OrderItem

@login_required
def dashboard(request):
    """
    Dashboard thống kê báo cáo doanh thu, đơn hàng, lợi nhuận và biểu đồ Chart.js
    """
    today = timezone.localdate()
    
    # 1. Thống kê hôm nay
    today_orders = Order.objects.filter(created_at__date=today, status='completed')
    today_count = today_orders.count()
    today_revenue = sum(o.final_total for o in today_orders)

    # 2. Thống kê tháng này
    first_day_of_month = today.replace(day=1)
    month_orders = Order.objects.filter(
        created_at__date__gte=first_day_of_month,
        created_at__date__lte=today,
        status='completed',
    )
    month_count = month_orders.count()
    month_revenue = sum(o.final_total for o in month_orders)

    # 3. Đơn chưa thanh toán
    unpaid_orders = Order.objects.filter(is_paid=False, status='completed')
    unpaid_count = unpaid_orders.count()
    unpaid_total = sum(o.final_total for o in unpaid_orders)

    # 4. Bộ lọc khoảng ngày cho chi tiết báo cáo
    date_preset = request.GET.get('preset', '7days')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if date_preset == 'today':
        start_date = today
        end_date = today
    elif date_preset == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
    elif date_preset == '7days':
        start_date = today - timedelta(days=6)
        end_date = today
    elif date_preset == '30days':
        start_date = today - timedelta(days=29)
        end_date = today
    elif date_preset == 'this_month':
        start_date = first_day_of_month
        end_date = today
    elif date_preset == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Khoảng ngày không hợp lệ. Đang hiển thị 7 ngày gần nhất.')
            start_date = today - timedelta(days=6)
            end_date = today
        if end_date < start_date:
            messages.error(request, 'Ngày kết thúc phải bằng hoặc sau ngày bắt đầu. Đang hiển thị 7 ngày gần nhất.')
            start_date = today - timedelta(days=6)
            end_date = today
    else:
        start_date = today - timedelta(days=6)
        end_date = today

    # Đơn hàng trong khoảng ngày lọc
    filtered_orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).prefetch_related('items', 'items__product')

    valid_orders = [o for o in filtered_orders if o.status == 'completed']
    filtered_order_count = len(valid_orders)
    filtered_revenue = sum(o.final_total for o in valid_orders)
    filtered_cost = sum(o.total_cost for o in valid_orders)
    filtered_profit = filtered_revenue - filtered_cost
    aov = (filtered_revenue / filtered_order_count) if filtered_order_count > 0 else Decimal('0')

    # 5. Dữ liệu biểu đồ doanh thu theo ngày (Chart.js)
    # Lặp qua từng ngày từ start_date đến end_date
    chart_labels = []
    chart_revenues = []
    chart_orders_count = []
    
    current_d = start_date
    # Giới hạn tối đa 60 ngày để biểu đồ không bị quá dày
    max_days = (end_date - start_date).days + 1
    if max_days > 60:
        current_d = end_date - timedelta(days=59)

    while current_d <= end_date:
        d_str = current_d.strftime('%d/%m')
        chart_labels.append(d_str)

        day_orders = [o for o in valid_orders if timezone.localtime(o.created_at).date() == current_d]
        day_rev = sum(o.final_total for o in day_orders)
        chart_revenues.append(int(day_rev))
        chart_orders_count.append(len(day_orders))

        current_d += timedelta(days=1)

    # 6. Top món bán chạy nhất trong khoảng ngày lọc
    order_ids = [o.id for o in valid_orders]
    top_items_qs = OrderItem.objects.filter(order_id__in=order_ids).values('product_name').annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum(ExpressionWrapper(
            F('unit_price') * F('quantity'),
            output_field=DecimalField(max_digits=24, decimal_places=0),
        )),
    ).order_by('-total_quantity')[:8]

    top_items = []
    for item in top_items_qs:
        top_items.append({
            'name': item['product_name'],
            'quantity': item['total_quantity'],
            'subtotal': item['total_sales'] or Decimal('0'),
        })

    context = {
        'today_count': today_count,
        'today_revenue': today_revenue,
        'month_count': month_count,
        'month_revenue': month_revenue,
        'unpaid_count': unpaid_count,
        'unpaid_total': unpaid_total,

        'date_preset': date_preset,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'filtered_order_count': filtered_order_count,
        'filtered_revenue': filtered_revenue,
        'filtered_cost': filtered_cost,
        'filtered_profit': filtered_profit,
        'aov': aov,

        'chart_labels': chart_labels,
        'chart_revenues': chart_revenues,
        'chart_orders_count': chart_orders_count,
        'top_items': top_items,
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
def export_excel(request):
    """
    Xuất báo cáo doanh thu và danh sách đơn hàng ra file Excel .xlsx chuyên nghiệp
    """
    # Lấy khoảng ngày lọc nếu có
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    status_filter = request.GET.get('status', 'all')

    orders = Order.objects.prefetch_related('items', 'items__product').all()

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__gte=start_date)
        except ValueError:
            messages.error(request, 'Ngày bắt đầu không hợp lệ.')
            return redirect('reports:dashboard')

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__lte=end_date)
        except ValueError:
            messages.error(request, 'Ngày kết thúc không hợp lệ.')
            return redirect('reports:dashboard')

    if start_date_str and end_date_str and start_date > end_date:
        messages.error(request, 'Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.')
        return redirect('reports:dashboard')

    if status_filter != 'all':
        if status_filter not in dict(Order.STATUS_CHOICES):
            messages.error(request, 'Trạng thái đơn hàng không hợp lệ.')
            return redirect('reports:dashboard')
        orders = orders.filter(status=status_filter)

    # Khởi tạo workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh sách đơn hàng"

    # Định dạng style
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_title = Font(name="Calibri", size=16, bold=True, color="BE185D")
    fill_header = PatternFill(start_color="EC4899", end_color="EC4899", fill_type="solid")
    fill_summary = PatternFill(start_color="FCE7F3", end_color="FCE7F3", fill_type="solid")
    border_thin = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )
    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    # Dòng Tiêu đề
    ws.merge_cells('A1:N1')
    ws['A1'] = "BÁO CÁO DOANH THU & DANH SÁCH ĐƠN HÀNG - HOA QUẢ SƠN"
    ws['A1'].font = font_title
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 40

    ws['A2'] = f"Ngày xuất báo cáo: {timezone.localtime().strftime('%d/%m/%Y %H:%M')}"
    ws['A2'].font = Font(italic=True, size=10, color="6B7280")
    ws.merge_cells('A2:N2')

    # Dòng Header bảng dữ liệu
    headers = [
        "STT", "Mã đơn", "Ngày giờ", "Khách hàng", "SĐT / Liên hệ", "Hình thức",
        "Thanh toán", "Trạng thái", "Tiền hàng (đ)", "Giảm giá (đ)", "Phí ship (đ)",
        "Tổng thanh toán (đ)", "Giá vốn ước tính (đ)", "Lợi nhuận ước tính (đ)"
    ]

    row_num = 4
    for col_num, header_title in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col_num)
        cell.value = header_title
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = border_thin
    ws.row_dimensions[row_num].height = 26

    # Ghi dữ liệu từng đơn hàng
    total_rev = Decimal('0')
    total_cost = Decimal('0')
    total_profit = Decimal('0')

    for idx, o in enumerate(orders, 1):
        row_num += 1
        rev = o.final_total if o.status == 'completed' else Decimal('0')
        cost = o.total_cost if o.status == 'completed' else Decimal('0')
        profit = rev - cost if o.status == 'completed' else Decimal('0')

        total_rev += rev
        total_cost += cost
        total_profit += profit

        ws.cell(row=row_num, column=1, value=idx).alignment = align_center
        ws.cell(row=row_num, column=2, value=o.code).alignment = align_center
        ws.cell(row=row_num, column=3, value=o.created_at.strftime('%d/%m/%Y %H:%M')).alignment = align_center
        ws.cell(row=row_num, column=4, value=o.customer_name).alignment = align_left
        ws.cell(row=row_num, column=5, value=o.customer_contact or "").alignment = align_center
        ws.cell(row=row_num, column=6, value=o.get_order_type_display()).alignment = align_center
        ws.cell(row=row_num, column=7, value=f"{o.get_payment_method_display()} ({'Đã trả' if o.is_paid else 'Chưa trả'})").alignment = align_center
        ws.cell(row=row_num, column=8, value=o.get_status_display()).alignment = align_center
        
        # Tiền tệ
        cell_subtotal = ws.cell(row=row_num, column=9, value=float(o.subtotal))
        cell_subtotal.number_format = '#,##0'
        cell_subtotal.alignment = align_right

        cell_discount = ws.cell(row=row_num, column=10, value=float(o.discount_amount))
        cell_discount.number_format = '#,##0'
        cell_discount.alignment = align_right

        cell_ship = ws.cell(row=row_num, column=11, value=float(o.shipping_fee))
        cell_ship.number_format = '#,##0'
        cell_ship.alignment = align_right

        cell_total = ws.cell(row=row_num, column=12, value=float(rev))
        cell_total.number_format = '#,##0'
        cell_total.alignment = align_right
        cell_total.font = Font(bold=True)

        cell_c = ws.cell(row=row_num, column=13, value=float(cost))
        cell_c.number_format = '#,##0'
        cell_c.alignment = align_right

        cell_p = ws.cell(row=row_num, column=14, value=float(profit))
        cell_p.number_format = '#,##0'
        cell_p.alignment = align_right
        cell_p.font = Font(bold=True, color="16A34A" if profit >= 0 else "DC2626")

        for col in range(1, 15):
            ws.cell(row=row_num, column=col).border = border_thin

    # Dòng Tổng cộng
    row_num += 1
    ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=11)
    summary_cell = ws.cell(row=row_num, column=1, value="TỔNG CỘNG DOANH THU & LỢI NHUẬN (Chỉ tính đơn hoàn thành):")
    summary_cell.font = Font(bold=True)
    summary_cell.alignment = Alignment(horizontal='right', vertical='center')

    cell_tot_rev = ws.cell(row=row_num, column=12, value=float(total_rev))
    cell_tot_rev.font = Font(bold=True, color="BE185D")
    cell_tot_rev.number_format = '#,##0'
    cell_tot_rev.alignment = align_right

    cell_tot_cost = ws.cell(row=row_num, column=13, value=float(total_cost))
    cell_tot_cost.font = Font(bold=True)
    cell_tot_cost.number_format = '#,##0'
    cell_tot_cost.alignment = align_right

    cell_tot_profit = ws.cell(row=row_num, column=14, value=float(total_profit))
    cell_tot_profit.font = Font(bold=True, color="16A34A" if total_profit >= 0 else "DC2626")
    cell_tot_profit.number_format = '#,##0'
    cell_tot_profit.alignment = align_right

    for col in range(1, 15):
        cell_s = ws.cell(row=row_num, column=col)
        cell_s.fill = fill_summary
        cell_s.border = border_thin

    # Tự động điều chỉnh độ rộng cột
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Xuất file trả về response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    timestamp = timezone.localtime().strftime('%Y%m%d_%H%M')
    response['Content-Disposition'] = f'attachment; filename=BaoCao_HoaQuaSon_{timestamp}.xlsx'
    wb.save(response)
    return response
