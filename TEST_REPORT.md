# Báo cáo kiểm thử (17/10/2026)

**10/10 tests PASS** trên môi trường Python của hệ thống thử nghiệm, `ffmpeg`/`ffprobe` có sẵn.

Các bài thử (mock local HTTP): `doctor`, scene list, create song, variations seed tăng dần, wait, download không ghi đè mặc định, phát hiện instrumental LoRA, regenerate ABC, upload cover streaming, chặn host không phải loopback.

Kiểm thử integration với `ffmpeg` thật: tạo mẫu sine 7 giây; dựng loop 1 giây crossfade → file OGG 6 giây, probe được duration và viết manifest.

**Chưa kiểm thử:** chạy model YuE2-3B thật trên Mac M4/24 GB của người dùng; tính thẩm mỹ chất lượng nhạc; chất lượng cover/hum trên dữ liệu người dùng; tính tương thích Paseo với cấu hình Pi riêng; chất lượng loop khi lặp nhiều lần theo nhịp/hòa âm. Cần kiểm tra thực tế trước khi phát hành game.

Chạy lại:

```bash
python3 -m unittest discover -s tests -v
```
