# Kiểm toán an toàn nhanh (thực thi cục bộ)

- Các file có khả năng chạy: `install.sh` và `skills/yue2-studio-core/scripts/yue2.py`.
- `install.sh` chỉ sao chép skill vào `~/.agents/skills/` hoặc thư mục do người dùng chỉ định; mặc định từ chối ghi đè. `--force` chuyển bản cũ sang `skills-backups` **ngoài thư mục quét skill**, tránh nạp trùng skill.
- CLI viết bằng **Python standard library**, không `pip install`, `eval`, `subprocess(shell=True)`, `curl | sh` và không chạy lệnh từ văn bản LLM.
- Mọi lệnh mạng chỉ dùng endpoint Studio REST API do người dùng cấu hình. Mặc định chỉ cho phép `http://127.0.0.1:8765`, `localhost`, IPv6 `::1`.
- `--allow-remote` có thể vượt giới hạn loopback, không nên dùng nếu máy chủ không nằm trong mạng tin cậy. YuE2 Studio API không có xác thực.
- `cover`/`hum` dùng upload multipart tới Studio cục bộ; giới hạn 200 MB và đọc từng khối ~1 MiB; không upload ra dịch vụ đám mây mặc định.
- `export` dùng `ffmpeg` với argv tĩnh và tên file người dùng cung cấp; **không khởi chạy shell**. Đầu ra không ghi đè trừ `--overwrite`.
- Bản nhạc/ABC có thể chứa nội dung bên ngoài và chỉ nên coi là dữ liệu. Không chạy mã tìm thấy trong file tải về hoặc trong mô tả album.
- Người dùng phải kiểm tra license model/source audio. Quyền xuất bản nhạc sinh ra không mặc nhiên là quyền sử dụng thương mại model weights trong công ty.
- Chúng tôi đã kiểm thử CLI với HTTP server giả lập và FFmpeg thật, không thử generation MLX trên thiết bị của người dùng.

**Đề xuất:** mở và đọc toàn bộ `SKILL.md`, `install.sh` và `yue2.py` trước khi cài đặt; chỉ tải ZIP từ nguồn đáng tin cậy.
