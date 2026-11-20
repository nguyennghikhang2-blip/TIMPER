# Chạy thử trên web, không cần Python hay Docker

## Bước 1 — Đưa mã nguồn lên GitHub
1. Đăng nhập GitHub; tạo repository mới (nên chọn **Private**).
2. Chọn **Add file → Upload files**.
3. Giải nén file ZIP và tải **nội dung bên trong** thư mục `tiktok_shortcut_web` lên **thư mục gốc** của repository. Phải có `render.yaml`, `Dockerfile`, `requirements.txt`, `app/`, `static/` ở thư mục gốc.
4. Chọn **Commit changes**.

## Bước 2 — Triển khai trên Render
1. Truy cập https://dashboard.render.com/blueprints; đăng nhập bằng tài khoản Render.
2. Chọn **New Blueprint Instance** (hoặc **New → Blueprint**, tùy giao diện).
3. Kết nối GitHub và chọn repository vừa tạo. Chỉ cấp quyền cho repository này nếu có tùy chọn.
4. Render đọc `render.yaml`; xem lại chi phí và chọn triển khai. Cấu hình đề xuất là `plan: free`.
5. Sau khi trạng thái hiển thị **Live**, mở URL có dạng `https://tiktok-save-private-xxxx.onrender.com`.

## Bước 3 — Test
1. Mở trang vừa được cấp qua HTTPS.
2. Dán link: `https://www.tiktok.com/@rawrmusi/video/7688298692083846418`.
3. Chọn **Tải video**. Nếu nhận MP4, mở video và xem nhiều đoạn để xác định watermark; máy chủ **không tự xác minh** watermark.
4. Nếu lỗi, vào Render → Service → Logs để xem lỗi máy chủ; xóa thông tin nhạy cảm trước khi chia sẻ.

## Lưu ý bảo mật và giới hạn
- URL website của dịch vụ có thể bị người khác truy cập. Repo GitHub Private không làm website Private. **Không dùng cấu hình này cho website công khai rộng rãi**, vì chưa có xác thực đăng nhập và chưa cô lập tiến trình tải trong mạng riêng.
- Không nhập cookie TikTok, mật khẩu Apple ID hoặc token bí mật.
- Không tải video riêng tư hoặc video không có quyền sử dụng.
- Render Free có thể ngủ khi không hoạt động, khởi động chậm và bị giới hạn RAM, thời lượng chạy và tài nguyên. TikTok cũng có thể chặn truy cập từ IP hosting.
- Không có đảm bảo mọi video sẽ không watermark; cần mở video kiểm tra thực tế.
- Khi đã có URL HTTPS của riêng bạn, xem `docs/IPAD_SHORTCUT.md` và thay URL API theo tên miền Render.
