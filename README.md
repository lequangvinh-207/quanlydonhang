Hãy viết cho tôi một web quản lý đơn hàng chạy local cho shop bán hoa quả cắt sẵn. Viết đầy đủ code, chia file rõ ràng, và hướng dẫn chạy từng bước.

## 1. Công nghệ
- Python 3.10+, Django, SQLite, Bootstrap 5 (dùng CDN), template Django thuần (không cần React).
- Chạy local bằng `python manage.py runserver`, không cần deploy.
- Giao diện tiếng Việt, dùng tốt trên cả máy tính và điện thoại.
- Tiền tệ hiển thị dạng 25.000đ.

## 2. Bối cảnh
Shop bán hộp hoa quả cắt sẵn. Menu chính là các loại hoa quả mà shop đang có. Người dùng là chủ shop và vài thành viên trong nhóm, dùng chung một máy nên chưa cần phân quyền.

## 3. Chức năng

### 3.1 Quản lý menu (hoa quả)
- Thêm / sửa / xóa món: tên, giá bán, giá nhập (không bắt buộc), ảnh (không bắt buộc), mô tả ngắn.
- Nút bật/tắt "Còn hàng / Hết hàng" ngay trên danh sách, không cần vào trang sửa.
- Món hết hàng vẫn hiện trong menu quản lý nhưng không chọn được khi tạo đơn.
- Tìm kiếm món theo tên.

### 3.2 Tạo đơn hàng
- Màn hình bán hàng: bên trái là lưới các món còn hàng (bấm để thêm vào đơn), bên phải là giỏ đơn hiện tại.
- Trong giỏ: chỉnh số lượng, xóa món, ghi chú cho từng món (ví dụ "không dưa hấu").
- Thông tin khách: tên, SĐT hoặc tài khoản mạng xã hội, địa chỉ giao (không bắt buộc).
- Phí ship, giảm giá (theo số tiền hoặc %), tự động tính tổng tiền.
- Hình thức: tại chỗ / mang đi / giao hàng.
- Thanh toán: tiền mặt / chuyển khoản, và trạng thái đã thanh toán hay chưa.
- Hỗ trợ "Hộp mix đồng giá": cho phép tạo một món dạng combo có giá cố định (ví dụ 25.000đ/hộp), khi đặt thì ghi chú loại hoa quả khách chọn cho vào hộp. Món nào là combo thì tick vào ô "Là hộp mix đồng giá", giá lấy theo hộp thay vì cộng từng loại.
- Sau khi lưu có trang xem hóa đơn đẹp, có nút in.

### 3.3 Quản lý đơn hàng
- Danh sách đơn: mã đơn, ngày giờ, khách, tổng tiền, trạng thái.
- Lọc theo ngày, trạng thái, hình thức; tìm theo tên hoặc SĐT khách.
- Trạng thái: Mới → Đang chuẩn bị → Đang giao → Hoàn thành, hoặc Hủy. Đổi trạng thái bằng một nút bấm.
- Xem chi tiết, sửa, hủy đơn.

### 3.4 Báo cáo
- Dashboard: doanh thu hôm nay, số đơn hôm nay, doanh thu tháng này, đơn chưa thanh toán.
- Lọc báo cáo theo khoảng ngày: doanh thu, số đơn, giá trị đơn trung bình.
- Top món bán chạy (theo số lượng).
- Biểu đồ doanh thu theo ngày (dùng Chart.js qua CDN).
- Nếu món có giá nhập, tính thêm lợi nhuận ước tính.
- Nút xuất báo cáo và danh sách đơn ra Excel (openpyxl).

## 4. Cấu trúc dữ liệu gợi ý
- Product: name, price, cost_price, image, description, is_available, is_combo, created_at
- Order: code, customer_name, customer_contact, address, order_type, payment_method, is_paid, status, discount_type, discount_value, shipping_fee, note, created_at
- OrderItem: order (FK), product (FK), product_name, unit_price (lưu giá tại thời điểm bán), quantity, note
Tính tổng tiền bằng property/method trong model. Lưu giá tại thời điểm bán để sau này đổi giá menu không làm sai đơn cũ.

## 5. Yêu cầu chất lượng
- Cấu trúc project gọn: một project `shop`, app `menu`, app `orders`, app `reports`, thư mục `templates` dùng chung `base.html` có thanh điều hướng.
- Đăng ký model vào Django admin để quản lý nhanh.
- Có file `requirements.txt` và lệnh tạo database, tạo tài khoản admin.
- Có lệnh/seed dữ liệu mẫu khoảng 8 loại hoa quả (dưa hấu, xoài, thanh long, dứa, ổi, cam, nho, táo) để chạy thử.
- Validate dữ liệu cơ bản (số lượng > 0, giá >= 0), có thông báo thành công/lỗi.
- Code có comment ngắn bằng tiếng Việt ở các chỗ quan trọng.

## 6. Cách làm việc
Hãy làm theo từng bước và dừng lại sau mỗi bước để tôi chạy thử:
Bước 1: Khởi tạo project, model, quản lý menu.
Bước 2: Tạo đơn hàng và hóa đơn.
Bước 3: Quản lý đơn hàng và trạng thái.
Bước 4: Dashboard, báo cáo, xuất Excel.
Bắt đầu từ Bước 1.

## Cài đặt và chạy local

Yêu cầu Python 3.10 trở lên. Mở PowerShell tại thư mục dự án, sau đó chạy:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data
python manage.py runserver
```

Mở `http://127.0.0.1:8000/` để xem menu; đăng nhập khu quản lý tại
`http://127.0.0.1:8000/quan-ly/dang-nhap/`. Database SQLite nằm trong `db.sqlite3`.

## Deploy lên máy chủ

Ứng dụng dùng Gunicorn, WhiteNoise và PostgreSQL khi chạy trên máy chủ. Cấu hình các
biến môi trường sau trong dịch vụ deploy (không đưa khóa bí mật vào Git):

- `SECRET_KEY`: khóa bí mật Django dài, ngẫu nhiên.
- `DEBUG`: đặt `False`.
- `ALLOWED_HOSTS`: danh sách hostname, phân cách bằng dấu phẩy, ví dụ `shop.example.com`.
- `CSRF_TRUSTED_ORIGINS`: các origin HTTPS, phân cách bằng dấu phẩy, ví dụ `https://shop.example.com`.
- `DATABASE_URL`: URL PostgreSQL do dịch vụ cơ sở dữ liệu cung cấp.

Các bước triển khai tổng quát:

1. Tạo ứng dụng web và cơ sở dữ liệu PostgreSQL trên nền tảng hosting.
2. Kết nối kho mã nguồn và cài dependencies bằng `pip install -r requirements.txt`.
3. Khai báo các biến môi trường ở trên; bảo đảm tên miền đã có trong `ALLOWED_HOSTS`.
4. Chạy `python manage.py migrate` để tạo/cập nhật cấu trúc database.
5. Chạy `python manage.py collectstatic --noinput` để thu thập static files.
6. Tạo tài khoản quản lý bằng `python manage.py createsuperuser`.
7. Khởi chạy web bằng lệnh trong `Procfile` (`gunicorn shop.wsgi:application --bind 0.0.0.0:$PORT`).
8. Gắn tên miền và HTTPS. Khi `DEBUG=False`, Django tự bật chuyển hướng HTTPS và cookie bảo mật.

Không cần thiết lập `DATABASE_URL` khi chạy local: ứng dụng tiếp tục dùng SQLite.
Static files được phục vụ qua WhiteNoise; ảnh sản phẩm nên đặt trong static, không phụ
thuộc vào ổ đĩa tạm của hosting.