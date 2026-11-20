# TikTok Save — Website + phím tắt iPad (v2)

Website tự triển khai để **ưu tiên** tải video TikTok công khai không watermark khi có nguồn phát phù hợp. Tương thích Apple Shortcuts trên iPad Gen 11 qua menu Chia sẻ, với hai chế độ **Tải trực tiếp** và **Mở website**. Không có mã nguồn/phím tắt gốc của phimtat.vn và đây không phải bản sao của họ.

**Giới hạn:** Không đảm bảo 100% video không watermark; không hỗ trợ video riêng tư, video bị chặn, DRM hoặc đăng nhập/cookie. Chỉ sử dụng với video bạn sở hữu hoặc có quyền tải. Chưa có thử nghiệm end-to-end trên TikTok và iPad thực tế trong môi trường này.

## Cấu trúc

- `app/main.py`: API FastAPI, kiểm tra link TikTok, giới hạn yêu cầu cơ bản, chính sách header bảo mật, giao video và xóa file tạm.
- `app/worker.py`: xử lý `yt-dlp` trong **tiến trình con**, có timeout/kill để giảm nguy cơ tác vụ tải chạy mãi.
- `static/`: website tối ưu mobile và iPad.
- `docs/IPAD_SHORTCUT.md`: **hướng dẫn từng hành động tạo phím tắt 2 chế độ**.
- `docker-compose.yml`: chạy chỉ trên localhost để thử.
- `docker-compose.public.yml` + `Caddyfile`: mẫu triển khai HTTPS (cần bảo vệ trước khi mở Internet).
- `tests/`: kiểm thử URL và HTTP response, **không** thử tải video thật.

## Chạy cục bộ (Windows / macOS / Linux)

Cần Python 3.12+ và mạng Internet.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Mở `http://127.0.0.1:8000`. Nếu dùng Docker, chạy `docker compose up --build -d` rồi mở cùng địa chỉ trên máy chủ.

## Triển khai HTTPS cho iPad

Dùng máy chủ VPS của bạn, cấu hình DNS `A/AAAA` trỏ về VPS, mở cổng 80/443, sau đó:

```bash
cp .env.example .env
# sửa DOMAIN trong .env, ví dụ video.tenmiencuaban.com
# yêu cầu Docker + Docker Compose
# CHỈ thực hiện sau khi đã bố trí quyền truy cập riêng / bảo vệ chống lạm dụng
 docker compose -f docker-compose.public.yml up --build -d
```

Caddy tự yêu cầu chứng chỉ TLS khi tên miền trỏ đúng IP máy chủ và cổng Internet hoạt động. Thử `https://DOMAIN/health` trước khi tạo Shortcut.

**LƯU Ý BẢO MẬT:** File cấu hình public chỉ là *mẫu* triển khai, API chưa có cơ chế xác thực riêng. KHÔNG công khai cho mọi người dùng khi chưa có xác thực (VPN/Zero Trust hoặc proxy auth), hạn chế băng thông, giám sát tài nguyên và chính sách chặn egress tới mạng nội bộ chống SSRF. Nếu dùng cổng truy cập được chỉ cho cá nhân (VPN riêng/Tailscale), cũng cần cấu hình HTTPS phù hợp. Cấu hình rate-limit trong app chỉ là lớp bảo vệ sơ cấp, không thay thế reverse-proxy policy hoặc firewall. Reverse proxy có thể làm gộp IP người dùng, ảnh hưởng rate limit.

## Tạo phím tắt trên iPad

Mở **[`docs/IPAD_SHORTCUT.md`](docs/IPAD_SHORTCUT.md)** để xem từng thao tác cấu hình Apple Shortcuts. **Không có tệp `.shortcut` hoặc liên kết iCloud được ký sẵn** vì cần có thiết bị Apple/chia sẻ iCloud để tạo và kiểm tra liên kết đó. Việc dựng một đường dẫn giả có thể gây mất an toàn.

## Kiểm thử

```bash
pip install pytest httpx
pytest -q
python -m compileall -q app
```

Sau triển khai, thử với 1 video TikTok công khai của chính bạn và kiểm tra chất lượng/khả năng không watermark thật. API có thể thất bại khi TikTok thay đổi công nghệ hoặc chặn IP.

## An toàn dữ liệu

- Không thu thập username/mật khẩu/cookie TikTok.
- Không lưu lịch sử link vào database; tệp video tạm xóa khi gửi xong hoặc khi xử lý lỗi. Máy chủ/VPS, reverse proxy hoặc nhà cung cấp vẫn có thể ghi log nếu bạn tự bật.
- Liên kết được giới hạn miền TikTok HTTPS và bỏ các tham số tracking trước khi gửi yt-dlp.
- yt-dlp vẫn truy cập địa chỉ mà TikTok/redirect/extractor trả về; **chưa có sandbox egress chống SSRF toàn diện**. Không dùng cho mục đích public hosting không giám sát.
- Tiến trình con bị hủy khi vượt timeout; giới hạn bộ nhớ/dung lượng/tiến trình ở Docker Compose. Khi tải bị ngắt do mất điện/restart, file tạm của container có thể tồn tại đến khi container/tệp tmpfs dọn dẹp.
- Không đưa bí mật vào javascript client-side.

## Live test với video mẫu được cung cấp

Sau khi cài `pip install -r requirements.txt`, chạy:

```bash
python tests/live_video_check.py
```

Test sử dụng liên kết `@rawrmusi/video/7688298692083846418`, kiểm tra thông tin video, tìm format được đánh dấu không watermark, thử tải qua worker thật và lưu `test-output.mp4`. Nếu có `ffprobe`, in thêm thông tin video. **Kết quả `DOWNLOADED_NEEDS_VISUAL_WATERMARK_CHECK` không chứng minh video sạch watermark**: cần mở file và kiểm tra xuyên suốt. Không đưa file hoặc quyền truy cập video vào trang bên thứ ba không tin cậy. Bài kiểm tra cần truy cập TikTok trực tiếp qua Internet.
