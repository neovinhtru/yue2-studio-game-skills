#!/usr/bin/env python3
"""Local YuE2 Studio client for Agent Skills. Python 3.10+, standard library only.

Targets https://github.com/ianiv/YuE2 docs/API.md (verified 2026-10-17).
No GPU or YuE2 imports: runs in agent shell and delegates work to local Studio API.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

API_TIMEOUT = 30
JOBS_TERMINAL = {'done', 'failed', 'cancelled'}
ALLOWED_UPLOADS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.webm', '.mp4'}


class StudioError(Exception):
    pass


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def api_root(url, allow_remote):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'http' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise StudioError('Studio URL phải là http://HOST:PORT, không chứa userinfo, đường dẫn hay query.')
    if parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} and not allow_remote:
        raise StudioError('Chỉ cho phép loopback mặc định. Dùng --allow-remote nếu thật sự tin tưởng máy chủ từ xa.')
    return url.rstrip('/')


class Studio:
    def __init__(self, url, allow_remote=False):
        self.base = api_root(url, allow_remote)

    def call(self, method, path, data=None):
        headers = {'Accept': 'application/json'}
        payload = None
        if data is not None:
            payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(self.base + path, data=payload, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as r:
                contents = r.read()
                return json.loads(contents) if contents else {}
        except urllib.error.HTTPError as ex:
            raw = ex.read().decode('utf-8', 'replace')[:4000]
            try:
                err = json.loads(raw).get('error', {})
                raw = err.get('message', raw)
            except ValueError:
                pass
            raise StudioError(f'HTTP {ex.code}: {raw}') from ex
        except urllib.error.URLError as ex:
            raise StudioError(f'Không kết nối được YuE2 Studio tại {self.base}: {ex.reason}') from ex

    def download(self, path, dest, overwrite=False):
        dest = Path(dest).expanduser().resolve()
        if dest.exists() and not overwrite:
            raise StudioError("File đầu ra đã tồn tại. Dùng --overwrite để ghi đè.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(self.base + path)
        tmp = dest.with_name(dest.name + '.part')
        try:
            with urllib.request.urlopen(req, timeout=120) as response, tmp.open('wb') as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
            os.replace(tmp, dest)
        except urllib.error.HTTPError as ex:
            tmp.unlink(missing_ok=True)
            raise StudioError(f'Download HTTP {ex.code} từ {path}') from ex
        except (OSError, urllib.error.URLError) as ex:
            tmp.unlink(missing_ok=True)
            raise StudioError(f'Không thể tải {path}: {ex}') from ex
        return {'file': str(dest), 'size_bytes': dest.stat().st_size, 'sha256': sha256_file(dest)}

    def upload(self, file):
        """Stream multipart in 1 MiB blocks (avoid loading 200 MB into RAM)."""
        file = Path(file).expanduser().resolve()
        if not file.is_file() or file.stat().st_size < 1:
            raise StudioError('File âm thanh không tồn tại hoặc rỗng.')
        if file.suffix.lower() not in ALLOWED_UPLOADS:
            raise StudioError('Định dạng upload không hỗ trợ: ' + file.suffix)
        if file.stat().st_size > 200_000_000:
            raise StudioError('File upload vượt giới hạn 200 MB của Studio.')
        boundary = '----yue2-' + uuid.uuid4().hex
        # Avoid header injection in source filenames.
        safe_name = file.name.replace('"', '_').replace('\r', '_').replace('\n', '_')
        head = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'
                f'Content-Type: application/octet-stream\r\n\r\n').encode()
        tail = f'\r\n--{boundary}--\r\n'.encode()
        p = urllib.parse.urlparse(self.base)
        conn = http.client.HTTPConnection(p.hostname, p.port or 80, timeout=120)
        try:
            conn.putrequest('POST', '/api/upload')
            conn.putheader('Content-Type', f'multipart/form-data; boundary={boundary}')
            conn.putheader('Content-Length', str(len(head) + file.stat().st_size + len(tail)))
            conn.endheaders()
            conn.send(head)
            with file.open('rb') as inp:
                while chunk := inp.read(1024 * 1024):
                    conn.send(chunk)
            conn.send(tail)
            response = conn.getresponse()
            data = response.read().decode('utf8', 'replace')
            if response.status != 201:
                raise StudioError(f'Upload HTTP {response.status}: {data[:2000]}')
            return json.loads(data)
        except (OSError, json.JSONDecodeError) as ex:
            raise StudioError(f'Upload thất bại: {ex}') from ex
        finally:
            conn.close()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def get_text_or_file(text, file, fallback=None):
    if text is not None and file is not None:
        raise StudioError('Chỉ sử dụng một trong --lyrics và --lyrics-file.')
    if file is not None:
        return Path(file).expanduser().read_text(encoding='utf-8').strip()
    return text if text is not None else fallback


def template(name):
    location = Path(__file__).resolve().parents[2] / 'yue2-game-composer' / 'assets' / 'scenes.json'
    if not location.exists():
        raise StudioError('Không tìm thấy scenes.json; hãy cài đầy đủ cả bộ skill.')
    scenes = json.loads(location.read_text(encoding='utf-8'))
    if name not in scenes:
        raise StudioError('Scene không tồn tại. Dùng lệnh scenes để xem: ' + ', '.join(sorted(scenes)))
    return scenes[name]


def loras_from_args(args, studio):
    refs = []
    if getattr(args, 'lora', None):
        for arg in args.lora:
            parts = arg.rsplit(':', 1)
            name, scale = parts[0], float(parts[1]) if len(parts) == 2 else 1.0
            if not 0 <= scale <= 4:
                raise StudioError('LoRA scale phải nằm trong khoảng 0..4.')
            refs.append({'name': name, 'scale': scale})
    if getattr(args, 'auto_instrumental_lora', False):
        if refs:
            raise StudioError('Không dùng --auto-instrumental-lora đồng thời với --lora.')
        adapters = studio.call('GET', '/api/loras').get('adapters', [])
        candidates = [i for i in adapters if i.get('valid') and i.get('kind', 'lora') == 'lora'
                      and 'inst' in i.get('name', '').lower()]
        ars = [i for i in candidates if 'ar' in i.get('parts', [])]
        nars = [i for i in candidates if i.get('parts', []) == ['nar']]
        if len(ars) == 1:
            refs.append({'name': ars[0]['name'], 'scale': 1.0})
        elif len(ars) != 0:
            raise StudioError('Có nhiều LoRA AR instrumental. Hãy chọn tên chính xác bằng --lora.')
        if len(nars) == 1:
            refs.append({'name': nars[0]['name'], 'scale': 1.0})
        elif len(nars) > 1:
            raise StudioError('Có nhiều LoRA NAR instrumental. Hãy chọn --lora tường minh.')
        if not refs:
            print('LƯU Ý: Không tìm thấy LoRA instrumental phù hợp. Gửi không có LoRA.', file=sys.stderr)
    if refs:
        allowed = {a['name'] for a in studio.call('GET', '/api/loras').get('adapters', []) if a.get('valid') and a.get('kind', 'lora') == 'lora'}
        unknown = [r['name'] for r in refs if r['name'] not in allowed]
        if unknown:
            raise StudioError('LoRA chưa có/không hợp lệ: ' + ', '.join(unknown))
    return refs


def create_params(args, scene=None):
    src = template(scene) if scene else {}
    style = args.style if args.style is not None else src.get('style')
    lyrics = get_text_or_file(args.lyrics, args.lyrics_file, src.get('lyrics', '[Intro]\n[Instrumental]\n[Outro]'))
    title = args.title if args.title is not None else src.get('title')
    if not style or not lyrics:
        raise StudioError('Cần --style và lyrics (hoặc --scene hợp lệ).')
    params = {'style': style, 'lyrics': lyrics, 'cot': args.cot or src.get('cot', 'full')}
    if title:
        params['title'] = title
    if args.seed is not None:
        params['seed'] = args.seed
    if args.cfg_scale is not None:
        params['cfg_scale'] = args.cfg_scale
    if args.abc_file:
        params['abc'] = Path(args.abc_file).expanduser().read_text(encoding='utf-8')
        if params['cot'] == 'off':
            raise StudioError('--abc-file yêu cầu --cot full hoặc melody.')
    return params


def common_body(args, studio):
    b = {'preset': args.preset}
    if getattr(args, 'track_id', None):
        b['track_id'] = args.track_id
    if getattr(args, 'lora', None) or getattr(args, 'auto_instrumental_lora', False):
        b['loras'] = loras_from_args(args, studio)
    return b


def make_song(args, studio):
    if args.action == 'create':
        params = create_params(args, args.scene)
        body = {'kind': 'create', 'params': params, **common_body(args, studio)}
    elif args.action == 'variations':
        params = create_params(args, args.scene)
        body = {'kind': 'variations', 'params': {
            'count': args.count, 'base': params, 'random_seeds': args.random_seeds,
            'label': args.label or params.get('title')}, **common_body(args, studio)}
    elif args.action == 'regenerate':
        abc = Path(args.abc_file).expanduser().read_text(encoding='utf-8').strip()
        if not abc:
            raise StudioError('ABC rỗng.')
        params = {'parent_id': args.parent_id, 'abc': abc}
        if args.style is not None:
            params['style'] = args.style
        if args.lyrics is not None or args.lyrics_file is not None:
            params['lyrics'] = get_text_or_file(args.lyrics, args.lyrics_file)
        if args.seed is not None:
            params['seed'] = args.seed
        if args.title is not None:
            params['title'] = args.title
        body = {'kind': 'regenerate', 'params': params}
        if args.preset:
            body['preset'] = args.preset
        if args.track_id:
            body['track_id'] = args.track_id
        if args.lora:
            body['loras'] = loras_from_args(args, studio)
    elif args.action in {'cover', 'hum'}:
        status = studio.call('GET', '/api/status')
        feature = status.get(args.action, {})
        if not feature.get('available'):
            raise StudioError(f'{args.action} chưa sẵn sàng: ' + '; '.join(feature.get('reasons') or ['unknown reason']))
        upload = studio.upload(args.file)
        print('Upload ID:', upload['upload_id'], file=sys.stderr)
        params = {'upload_id': upload['upload_id'], 'style': args.style,
                  'lyrics': get_text_or_file(args.lyrics, args.lyrics_file,
                                             '[Intro]\n[Instrumental]\n[Outro]')}
        if args.title:
            params['title'] = args.title
        if args.seed is not None:
            params['seed'] = args.seed
        if args.action == 'cover':
            params.update({'task': args.task, 'mode': args.mode})
            if args.clip_start is not None:
                params['clip_start_s'] = args.clip_start
            if args.clip_end is not None:
                params['clip_end_s'] = args.clip_end
        else:
            params.update({'melody': args.melody, 'hum_influence': args.hum_influence,
                           'offset_s': args.offset_s})
            if args.adapter:
                params['adapter'] = args.adapter
        body = {'kind': args.action, 'params': params, **common_body(args, studio)}
    else:
        raise StudioError('Không hỗ trợ lệnh tạo.')
    result = studio.call('POST', '/api/jobs', body)
    pretty(result)
    return result


def wait_job(studio, job_id, every=5.0, timeout=7200):
    start = time.monotonic()
    last = None
    while True:
        job = studio.call('GET', f'/api/jobs/{job_id}')['job']
        summary = (job.get('status'), (job.get('progress') or {}).get('stage'))
        if summary != last:
            print(f'{job_id}: {summary[0]} / {summary[1] or "-"}', file=sys.stderr)
            last = summary
        if job.get('status') in JOBS_TERMINAL:
            pretty(job)
            if job['status'] != 'done':
                raise StudioError(f'Job {job_id} kết thúc với {job["status"]}: {job.get("error")}')
            return job
        if timeout and (time.monotonic() - start) > timeout:
            raise StudioError(f'Đã hết timeout; job {job_id} có thể vẫn đang chạy. Dùng job/wait để xem tiếp.')
        time.sleep(every)


def audio_info(path):
    if not shutil.which('ffprobe'):
        raise StudioError('Cần ffprobe (brew install ffmpeg).')
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                             'format=duration:stream=codec_name,sample_rate,channels',
                             '-of', 'json', str(path)], capture_output=True, text=True)
    if result.returncode:
        raise StudioError('ffprobe: ' + result.stderr.strip())
    return json.loads(result.stdout)


def ffmpeg_export(args):
    src = Path(args.input).expanduser().resolve()
    if not src.is_file():
        raise StudioError('Không tìm thấy file nguồn: ' + str(src))
    dest = Path(args.out).expanduser().resolve()
    if dest == src:
        raise StudioError('Đầu ra phải khác file gốc.')
    if dest.exists() and not args.overwrite:
        raise StudioError('File đầu ra đã tồn tại. Dùng --overwrite nếu muốn ghi đè.')
    if not shutil.which('ffmpeg'):
        raise StudioError('Cần ffmpeg (brew install ffmpeg).')
    fmt = args.format
    if fmt == 'auto':
        fmt = dest.suffix.lower().lstrip('.')
    if fmt not in {'wav', 'ogg', 'mp3', 'flac'}:
        raise StudioError('Chỉ hỗ trợ WAV/OGG/MP3/FLAC.')
    dest.parent.mkdir(parents=True, exist_ok=True)
    filters = []
    if args.loop:
        details = audio_info(src)
        duration = float(details['format']['duration'])
        x = args.crossfade
        if x <= 0 or 3*x >= duration:
            raise StudioError('Với --loop, crossfade > 0 và thời lượng > 3 × crossfade.')
        # Equal-power-ish linear fade/mix of tail->head; middle starts at head_end. The cut occurs
        # at a continuous point; musical/chord coherence requires listening.
        filters = ['-filter_complex',
            f'[0:a]asplit=3[h][t][m];'
            f'[h]atrim=start=0:end={x:.6f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={x:.6f}[head];'
            f'[t]atrim=start={duration-x:.6f}:end={duration:.6f},asetpts=PTS-STARTPTS,afade=t=out:st=0:d={x:.6f}[tail];'
            f'[m]atrim=start={x:.6f}:end={duration-x:.6f},asetpts=PTS-STARTPTS[mid];'
            f'[tail][head]amix=inputs=2:duration=shortest:normalize=0[xf];'
            f'[xf][mid]concat=n=2:v=0:a=1[out]', '-map', '[out]']
    else:
        filters = ['-map', '0:a:0']
    # Export is not normalized automatically; the game audio mixer controls headroom.
    codec = {
        'wav': ['-c:a', 'pcm_s16le'],
        'ogg': ['-c:a', 'libvorbis', '-q:a', str(args.quality)],
        'mp3': ['-c:a', 'libmp3lame', '-q:a', '2'],
        'flac': ['-c:a', 'flac'],
    }[fmt]
    tmp = dest.with_name(dest.stem + '.tmp.' + uuid.uuid4().hex[:6] + '.' + fmt)
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', str(src),
           *filters, *codec, str(tmp)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            raise StudioError('ffmpeg: ' + result.stderr.strip())
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    receipt = {'source': str(src), 'file': str(dest), 'format': fmt, 'loop_crossfade_s': args.crossfade if args.loop else None,
               'sha256': sha256_file(dest), 'audio': audio_info(dest),
               'note': 'Loop phải nghe kiểm tra, FFmpeg không thể tự đảm bảo vòng hòa âm trùng khớp.' if args.loop else None}
    if args.manifest:
        p = dest.with_suffix(dest.suffix + '.json')
        p.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pretty(receipt)


def arg_create(p, require_style=True):
    p.add_argument('--scene', help='Tên scene (xem scenes)')
    p.add_argument('--title')
    p.add_argument('--style', required=False)
    p.add_argument('--lyrics')
    p.add_argument('--lyrics-file')
    p.add_argument('--cot', choices=['full', 'melody', 'off'])
    p.add_argument('--seed', type=int)
    p.add_argument('--cfg-scale', type=float)
    p.add_argument('--abc-file')
    p.add_argument('--preset', choices=['fast', 'quality'], default='fast')
    p.add_argument('--track-id')
    p.add_argument('--lora', action='append', help='Tên LoRA hoặc TÊN:SCALE, cho phép lặp lại')
    p.add_argument('--auto-instrumental-lora', action='store_true')


def build_parser():
    p = argparse.ArgumentParser(description='YuE2 Studio API + nhạc game (Python stdlib, không cần SDK)')
    p.add_argument('--url', default=os.environ.get('YUE2_STUDIO_URL', 'http://127.0.0.1:8765'))
    p.add_argument('--allow-remote', action='store_true', help='Rủi ro: chỉ dùng với Studio tin cậy')
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('doctor', help='Kiểm tra server, model, ffmpeg, RAM, LoRA')
    sub.add_parser('status')
    sub.add_parser('loras')
    sub.add_parser('scenes')
    ls = sub.add_parser('jobs')
    ls.add_argument('--status', choices=['queued', 'running', 'done', 'failed', 'cancelled'])
    ls.add_argument('--limit', type=int, default=20)
    for a in ('job', 'cancel'):
        sub.add_parser(a).add_argument('job_id')
    w = sub.add_parser('wait')
    w.add_argument('job_id')
    w.add_argument('--interval', type=float, default=5.0)
    w.add_argument('--timeout', type=float, default=7200)
    d = sub.add_parser('download')
    d.add_argument('job_id')
    d.add_argument('--format', choices=['flac', 'mp3', 'abc', 'plan', 'zip'], default='flac')
    d.add_argument('--out', required=True)
    d.add_argument('--overwrite', action='store_true')
    for a in ('create', 'variations'):
        item = sub.add_parser(a)
        arg_create(item)
        if a == 'variations':
            item.add_argument('--count', type=int, default=3, choices=range(2, 17))
            item.add_argument('--random-seeds', action='store_true')
            item.add_argument('--label')
    reg = sub.add_parser('regenerate')
    reg.add_argument('--parent-id', required=True)
    reg.add_argument('--abc-file', required=True)
    reg.add_argument('--style')
    reg.add_argument('--lyrics')
    reg.add_argument('--lyrics-file')
    reg.add_argument('--title')
    reg.add_argument('--seed', type=int)
    reg.add_argument('--preset', choices=['fast', 'quality'])
    reg.add_argument('--track-id')
    reg.add_argument('--lora', action='append')
    for a in ('cover', 'hum'):
        q = sub.add_parser(a)
        q.add_argument('--file', required=True)
        q.add_argument('--style', required=True)
        q.add_argument('--lyrics')
        q.add_argument('--lyrics-file')
        q.add_argument('--title')
        q.add_argument('--seed', type=int)
        q.add_argument('--preset', choices=['fast', 'quality'], default='fast')
        q.add_argument('--track-id')
        q.add_argument('--lora', action='append')
        q.add_argument('--auto-instrumental-lora', action='store_true')
        if a == 'cover':
            q.add_argument('--task', choices=['melody-full', 'melody-vocal', 'full'], default='melody-full')
            q.add_argument('--mode', choices=['cover', 'continue'], default='cover')
            q.add_argument('--clip-start', type=float)
            q.add_argument('--clip-end', type=float)
        else:
            q.add_argument('--melody', choices=['continue', 'hum_only', 'ignore'], default='continue')
            q.add_argument('--adapter')
            q.add_argument('--hum-influence', type=float, default=1.0)
            q.add_argument('--offset-s', type=float, default=0.0)
    # Curated soundtrack project; keep operations explicit (never auto-select takes).
    a = sub.add_parser('project-new'); a.add_argument('--name', required=True); a.add_argument('--description', default='')
    a = sub.add_parser('track-new'); a.add_argument('project_id'); a.add_argument('--name', required=True)
    a = sub.add_parser('track-add'); a.add_argument('track_id'); a.add_argument('job_ids', nargs='+')
    a = sub.add_parser('take-rate'); a.add_argument('job_id'); a.add_argument('--stars', type=int, choices=range(1, 6)); a.add_argument('--note')
    a = sub.add_parser('track-choose'); a.add_argument('track_id'); a.add_argument('job_id')
    a = sub.add_parser('album-download'); a.add_argument('project_id'); a.add_argument('--format', choices=['flac', 'mp3'], default='flac'); a.add_argument('--out', required=True); a.add_argument('--overwrite', action='store_true')
    a = sub.add_parser('export')
    a.add_argument('--input', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--format', choices=['auto', 'wav', 'ogg', 'mp3', 'flac'], default='auto')
    a.add_argument('--loop', action='store_true', help='Crossfade cuối -> đầu; phải nghe kiểm tra')
    a.add_argument('--crossfade', type=float, default=1.5)
    a.add_argument('--quality', type=int, default=5, choices=range(0, 11), help='OGG Vorbis q 0..10')
    a.add_argument('--manifest', action='store_true')
    a.add_argument('--overwrite', action='store_true')
    a = sub.add_parser('analyze'); a.add_argument('--input', required=True)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.action == 'scenes':
        location = Path(__file__).resolve().parents[2] / 'yue2-game-composer' / 'assets' / 'scenes.json'
        pretty({k: {'title': v['title'], 'use': v.get('use', '')} for k, v in json.loads(location.read_text()).items()})
        return
    if args.action == 'analyze':
        pretty(audio_info(Path(args.input).expanduser()))
        return
    if args.action == 'export':
        ffmpeg_export(args)
        return
    s = Studio(args.url, args.allow_remote)
    if args.action == 'doctor':
        st = s.call('GET', '/api/status')
        mem = st.get('memory', {})
        out = {'server_url': s.base, 'models_ready': st.get('models', {}).get('present'),
               'fake_mode': st.get('fake'), 'queue': st.get('queue'), 'ram_gib': mem.get('machine_ram_gib'),
               'low_memory_effective': mem.get('low_memory_effective'), 'cover': st.get('cover'),
               'hum': st.get('hum'), 'loras': [i['name'] for i in st.get('loras', {}).get('adapters', []) if i.get('valid')],
               'ffmpeg_local': shutil.which('ffmpeg') is not None,
               'ffprobe_local': shutil.which('ffprobe') is not None, 'ffmpeg_server': st.get('ffmpeg')}
        pretty(out)
        if out['fake_mode']:
            print('CẢNH BÁO: Studio chạy --fake: âm thanh tạo ra là silent mock!', file=sys.stderr)
        if not out['models_ready']:
            raise StudioError('Weights chưa sẵn sàng: chạy setup.py trong repo YuE2 Studio.')
    elif args.action == 'status':
        pretty(s.call('GET', '/api/status'))
    elif args.action == 'loras':
        pretty(s.call('GET', '/api/loras'))
    elif args.action == 'jobs':
        query = urllib.parse.urlencode({'limit': args.limit, **({'status': args.status} if args.status else {})})
        pretty(s.call('GET', '/api/jobs?' + query))
    elif args.action == 'job':
        pretty(s.call('GET', '/api/jobs/' + args.job_id))
    elif args.action == 'cancel':
        pretty(s.call('POST', '/api/jobs/' + args.job_id + '/cancel'))
    elif args.action == 'wait':
        if args.interval <= 0 or args.timeout < 0:
            raise StudioError('Interval phải >0, timeout phải >=0.')
        wait_job(s, args.job_id, args.interval, args.timeout)
    elif args.action == 'download':
        mapping = {'flac': 'audio.flac', 'mp3': 'audio.mp3', 'abc': 'score.abc', 'plan': 'plan.json', 'zip': 'artifacts.zip'}
        pretty(s.download(f'/api/songs/{args.job_id}/{mapping[args.format]}', args.out, args.overwrite))
    elif args.action in {'create', 'variations', 'regenerate', 'cover', 'hum'}:
        make_song(args, s)
    elif args.action == 'project-new':
        pretty(s.call('POST', '/api/projects', {'name': args.name, 'description': args.description}))
    elif args.action == 'track-new':
        pretty(s.call('POST', f'/api/projects/{args.project_id}/tracks', {'name': args.name}))
    elif args.action == 'track-add':
        pretty(s.call('POST', f'/api/tracks/{args.track_id}/takes', {'job_ids': args.job_ids}))
    elif args.action == 'take-rate':
        if args.stars is None and args.note is None:
            raise StudioError('Cần --stars hoặc --note.')
        pretty(s.call('PATCH', f'/api/takes/{args.job_id}', {k: v for k, v in {'stars': args.stars, 'note': args.note}.items() if v is not None}))
    elif args.action == 'track-choose':
        pretty(s.call('PATCH', f'/api/tracks/{args.track_id}', {'chosen_job_id': args.job_id}))
    elif args.action == 'album-download':
        pretty(s.download(f'/api/projects/{args.project_id}/album.zip?' + urllib.parse.urlencode({'format': args.format}), args.out, args.overwrite))


if __name__ == '__main__':
    try:
        main()
    except (StudioError, ValueError, OSError, json.JSONDecodeError) as exc:
        print('LỖI:', exc, file=sys.stderr)
        sys.exit(1)
