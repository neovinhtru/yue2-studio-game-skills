# YuE2 Studio Game Skills — bộ skill nhạc game cho Codex / Pi / Paseo

**Phiên bản 1.0.0 — đối chiếu API YuE2 Studio (ianiv/YuE2) ngày 17/10/2026.**

Bộ skill độc lập do ChatGPT tạo mới, **không sao chép runtime, script hay model weights** của YuE/YuE2. Mục tiêu là điều khiển một máy Mac đang chạy **YuE2 Studio (MLX)** từ các AI Agent và chuẩn hóa quy trình sáng tác nhạc game. Không thay thế Studio; không tự tải model.

## Tính năng

| Skill | Chức năng |
|---|---|
| `yue2-studio-core` | Kết nối REST API, kiểm tra model/LoRA, tải kết quả, quản lý album và take |
| `yue2-game-composer` | Prompt theo ngữ cảnh game, 8 cảnh bao gồm Trái Đất → Sao Thổ |
| `yue2-game-variations` | Nhiều phương án có seed, thử nghiệm và chấm điểm, chọn bản cuối |
| `yue2-game-arranger` | Tải/chỉnh ABC, regenerate, cover và hum (khi model phụ có sẵn) |
| `yue2-game-export` | FLAC → WAV/OGG/MP3, nối vòng bằng crossfade, lưu SHA-256/metadata |

## Yêu cầu

- macOS Apple Silicon, YuE2 Studio đã cài và đang chạy tại `http://127.0.0.1:8765`.
- Python 3.10+ để chạy script client **không cần pip**; `ffmpeg` và `ffprobe` để xuất asset.
- Riêng YuE2 Studio yêu cầu Python 3.12 qua `uv`, và RAM từ 16 GB. Trên M4 24 GB, chế độ low-memory `auto` là phù hợp.
- Codex hoặc Pi. Paseo khi sử dụng Pi có thể nhận các skill này nếu phiên Pi được mở trong môi trường có thể đọc chúng; việc tự động nạp phụ thuộc cấu hình Paseo/Pi.

## Cài đặt

Giải nén ZIP, sau đó chạy:

```bash
cd yue2-studio-game-skills
# Kiểm tra mã nguồn script trước khi cài skill từ bất kỳ ZIP nào.
./install.sh
# Hoặc chỉ cài vào project game cụ thể:
./install.sh --project "$HOME/projects/space-game"
```

Đích mặc định: `~/.agents/skills/` (Pi và Codex). Script không ghi đè khi gặp skill trùng tên; `--force` lưu bản cũ thành thư mục backup.

```bash
# Khởi động YuE2 Studio tại repo riêng đã cài trước đó:
uv run yue2-studio --open
# Kiểm tra kết nối từ shell:
python3 ~/.agents/skills/yue2-studio-core/scripts/yue2.py doctor
```

## Ví dụ 1: tạo nhạc trận chiến Sao Hỏa

```bash
YUE2="$HOME/.agents/skills/yue2-studio-core/scripts/yue2.py"
python3 "$YUE2" scenes
python3 "$YUE2" create --scene mars-battle --seed 4200 --preset fast
# Từ kết quả lấy job.id, ví dụ <JOB_ID>:
python3 "$YUE2" wait <JOB_ID> --timeout 7200
python3 "$YUE2" download <JOB_ID> --format flac --out ./mars-master.flac
python3 "$YUE2" export --input ./mars-master.flac --out ./mars-loop.ogg --loop --manifest
```

## Ví dụ 2: tạo ba lựa chọn nhạc boss Sao Thổ

```bash
python3 "$YUE2" variations --scene saturn-boss --count 3 --seed 12002 --preset fast
# Trả về jobs[]; mỗi job chạy tuần tự, cần wait riêng.
```

## Ví dụ 3: sáng tác bằng Pi/Codex/Paseo

Pi: `/skill:yue2-game-composer Tạo nhạc nền boss Sao Thổ theo phong cách industrial rock; tạo 3 biến thể bằng Studio local, lưu FLAC, ưu tiên không có giọng hát.`

Codex/Paseo: `Hãy dùng yue2-game-composer và yue2-game-variations, gọi API YuE2 Studio trên máy này để tạo 3 nhạc nền combat, đọc kết quả trạng thái thực, và xuất bản được chọn sang Godot OGG.`

## Cấu trúc

```text
skills/
  yue2-studio-core/SKILL.md
  yue2-studio-core/scripts/yue2.py
  yue2-game-composer/SKILL.md
  yue2-game-composer/assets/scenes.json
  yue2-game-variations/SKILL.md
  yue2-game-arranger/SKILL.md
  yue2-game-export/SKILL.md
install.sh
examples/
tests/
```

## Khả năng và giới hạn

- **Có**: tạo nhạc, nhiều biến thể, seed, preset, LoRA, ABC, regenerate, cover/hum (nếu chuẩn bị model), download, album, FFmpeg loop.
- **Không có**: âm thanh sinh ra trực tiếp từ skill (Studio phải chạy), bảo đảm không giọng hát, xuất stem độc lập, MIDI chuyên dụng, hiệu ứng sound effect ngắn chuyên biệt, tự động đánh giá chất lượng âm nhạc bằng nghe, bảo đảm nhịp chính xác/độ dài cố định.
- Script `--loop` làm trơn âm thanh bằng crossfade tail-to-head; bạn vẫn cần nghe để kiểm tra nhịp và hòa âm khi vòng lặp quay lại.
- **Bảo mật:** mặc định chỉ kết nối HTTP loopback. API Studio không có auth: không expose server ra internet. Không tự gọi dịch vụ bên ngoài hay gửi audio lên cloud.
- **Bản quyền:** Mã nguồn Studio MIT nhưng weights VAE/MLX/YuE2 chịu giấy phép riêng (theo README tác giả YuE2 hiện cho phép cá nhân kiếm tiền từ output nhưng công ty muốn dùng model weights thương mại phải liên hệ xin phép). Phải kiểm tra đúng phiên bản license đang áp dụng và tư cách sử dụng trước khi thương mại hóa game, đặc biệt nếu công ty xuất bản. Cover còn có quyền đối với bản nhạc nguồn.

## Tham chiếu

- Studio: https://github.com/ianiv/YuE2
- API: https://github.com/ianiv/YuE2/blob/main/docs/API.md
- Upstream YuE skill tham khảo về *quy trình* chứ không dùng scripts runtime: https://github.com/multimodal-art-projection/YuE/tree/main/skills/yue2-music
- Pi skills: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md
- License weights chính thức: https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE ; https://huggingface.co/m-a-p/YuE2-3B

## Kiểm thử

```bash
python3 -m unittest discover -s tests -v
```

Kiểm thử mock API không yêu cầu YuE2 weights và không đánh giá chất lượng nhạc. Để kiểm thử generation thật, cần tự chạy Studio trên Mac; sau đó dùng `doctor`, `create`, `wait` và `download`.
