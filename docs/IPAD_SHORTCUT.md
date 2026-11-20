# Phím tắt "Lưu TikTok" — iPad Gen 11

> Không có đường dẫn iCloud để nhận phím tắt một chạm trong bộ này. Chưa có phím tắt được ký/chia sẻ bởi một thiết bị Apple. Các bước dưới đây tạo **phím tắt thật** bằng ứng dụng Shortcuts trên iPad, không cài cấu hình lạ và không cần Apple ID của người khác.

## Trước khi bắt đầu

- Website/API phải chạy ở một địa chỉ **HTTPS truy cập được từ iPad**, ví dụ `https://video.example.com` (địa chỉ ví dụ, thay bằng tên miền thật của bạn).
- Không dùng `http://127.0.0.1:8000` trên iPad nếu máy chủ chạy ở thiết bị khác.
- Kiểm tra `https://YOUR-DOMAIN/health` trả về `{"status":"ok"}`.
- Để tải video, máy chủ phải có Internet và TikTok phải cung cấp luồng phù hợp.

## Tạo phím tắt 2 chế độ

1. Mở **Phím tắt (Shortcuts)** → nhấn **+** → tên **Lưu TikTok**.
2. Nhấn phần thông tin (i) → bật **Hiển thị trong Bảng chia sẻ** (*Show in Share Sheet*). Phần loại đầu vào chọn **URLs** và **Text**. Nếu không có đầu vào, thêm hành động **Ask for Input** kiểu URL.
3. Thêm hành động **Get URLs from Input** (*Lấy URL từ đầu vào*), đầu vào là **Shortcut Input**. Phím tắt nhận URL khi bấm **Chia sẻ** trong TikTok.
4. Thêm **Get Item from List** (*Lấy mục từ danh sách*), chọn **First Item** của danh sách URL. Đặt tên biến đầu ra là **TikTokURL** nếu muốn dễ nhìn.
5. Thêm **Choose from Menu** (*Chọn từ menu*) có 2 mục:

   **Mục 1: Tải trực tiếp**
   - Trong nhánh menu này thêm **Get Contents of URL** (*Lấy nội dung của URL*).
   - URL: `https://YOUR-DOMAIN/api/download`.
   - Nhấn mở thêm tùy chọn: **Method = POST**, **Request Body = JSON**.
   - Thêm một trường JSON: **key** `url`, kiểu **Text**, **value** là biến **TikTokURL** từ bước 4 (phải là biến màu xanh, không phải chữ gõ thủ công).
   - Thêm **Save File** (*Lưu tệp*) với đầu vào là **Contents of URL** vừa nhận; bật **Ask Where to Save** để chọn thư mục trên iPad.
   - Tùy chọn: sau khi kiểm tra tải thành công, thay **Save File** bằng **Save to Photo Album** để lưu vào Ảnh; tùy iPadOS tác vụ có thể cần chuyển đổi file/chọn tên.

   **Mục 2: Mở website**
   - Thêm hành động **URL Encode** với biến **TikTokURL**.
   - Thêm **Text** có nội dung `https://YOUR-DOMAIN/?url=` rồi nối biến URL Encode ngay sau dấu `=`.
   - Thêm **Open URLs** (*Mở URL*) cho kết quả Text vừa tạo. Safari mở web với link đã điền sẵn.

6. Kết thúc menu, lưu phím tắt. Trong TikTok, chọn video bạn có quyền tải → **Chia sẻ** → **Lưu TikTok** → chọn chế độ.

## Kiểm tra khi lỗi

- **Không thấy tên phím tắt trong Chia sẻ**: kiểm tra bật Show in Share Sheet và loại input URLs/Text. Thử chọn **Sao chép liên kết** rồi chạy phím tắt từ ứng dụng Shortcuts.
- **Không lưu được tệp**: xem kết quả hành động Get Contents of URL; JSON báo lỗi API không phải video. Với việc chạy thử, thêm **Quick Look** trước Save File để kiểm tra kết quả.
- **Mở website nhưng chưa có link**: kiểm tra hành động URL Encode và biến TikTokURL.
- **Có watermark / không tải được**: công cụ chỉ ưu tiên nguồn phát có dấu hiệu không watermark, không thể đảm bảo mọi video hoặc vượt hạn chế truy cập.

## Quyền riêng tư

Shortcuts gửi URL tới máy chủ bạn chọn. Tên miền của máy chủ sẽ xuất hiện trong hộp thoại xin quyền truy cập mạng của Shortcuts. Không nhập mật khẩu TikTok, mã OTP hoặc cookie vào phím tắt. Kiểm tra từng hành động trước khi cài phím tắt từ bất kỳ người nào.
