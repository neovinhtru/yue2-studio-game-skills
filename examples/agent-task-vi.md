# Nhiệm vụ mẫu giao cho Pi / Codex / Paseo

Hãy sử dụng 5 skill của bộ `yue2-studio-game-skills` để xây dựng soundtrack nguyên gốc cho game bắn né theo hành tinh.

1. Đầu tiên dùng `yue2-studio-core` và chạy doctor. Nếu Studio chưa khởi động, báo lỗi thật, không nói đã tạo audio.
2. Dùng `yue2-game-composer` xây đề cương OST gồm Main Menu, Earth Combat, Moon Exploration, Mars Battle, Saturn Boss, Victory và Game Over. Lưu prompt đã dùng thành .json trong thư mục dự án.
3. Ưu tiên nhạc không lời. Phân biệt nhạc nền chơi lâu (ít cao trào, dễ lặp) và nhạc boss (kịch tính). Chừa không gian âm thanh cho tiếng súng và UI.
4. Dùng `yue2-game-variations` tạo 2 bản nháp `fast` cho một cảnh trước, ghi rõ job.id/seed/preset/LoRA; đợi job hoàn thành, tải FLAC, không khẳng định đã nghe khi chưa nghe.
5. Chỉ khi có phản hồi hoặc đánh giá bằng công cụ nghe thực sự mới chọn bản và chạy `quality` nếu cần.
6. Với bản được duyệt, dùng `yue2-game-export` xuất OGG loop cho Godot, giữ FLAC master, SHA256, ABC và thông tin license nguồn.
7. Không xóa bản gốc, không gửi audio ra mạng, không công bố sản phẩm thương mại khi chưa kiểm tra giấy phép model.

Đầu ra: thư mục `assets/music/` có các file gốc, file game, prompt.json và manifest.json; bảng báo cáo các job và những điểm cần kiểm tra thủ công.
