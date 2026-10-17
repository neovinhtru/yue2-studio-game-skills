"""Local HTTP mock contract tests; no YuE2 weights, network, or GPU needed."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'skills' / 'yue2-studio-core' / 'scripts' / 'yue2.py'


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    jobs = {}
    last_body = None
    def log_message(self, *args):
        pass
    def respond(self, obj, code=200):
        payload = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/status':
            return self.respond({'models': {'present': True}, 'fake': False, 'memory': {'machine_ram_gib': 24.0, 'low_memory_effective': True},
                                 'loras': {'adapters': []}, 'queue': {'queued': 0}, 'cover': {'available': True},
                                 'hum': {'available': True}, 'ffmpeg': True})
        if path == '/api/loras':
            return self.respond({'adapters': [{'name': 'ar_inst', 'valid': True, 'kind': 'lora', 'parts': ['ar']} ]})
        if path == '/api/jobs':
            return self.respond({'jobs': list(Handler.jobs.values()), 'total': len(Handler.jobs)})
        if path.startswith('/api/jobs/'):
            key = path.split('/')[-1]
            return self.respond({'job': Handler.jobs[key]}) if key in Handler.jobs else self.respond({'error': {'message': 'unknown'}}, 404)
        if path.startswith('/api/songs/'):
            data = b'fLaCfake\x00\x01\x02'
            self.send_response(200)
            self.send_header('Content-Type', 'audio/flac')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return self.respond({'error': {'message': path}}, 404)
    def do_POST(self):
        path = urlsplit(self.path).path
        raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        if path == '/api/upload':
            Handler.last_body = raw
            return self.respond({'upload_id': 'upload123', 'filename': 'test.wav'}, 201)
        body = json.loads(raw)
        Handler.last_body = body
        if path == '/api/jobs':
            if body['kind'] == 'variations':
                jobs = []
                base = body['params']['base']
                for i in range(body['params']['count']):
                    job = {'id': f'id{i}', 'seed': base['seed']+i, 'status': 'done', 'params': base}
                    Handler.jobs[job['id']] = job
                    jobs.append(job)
                return self.respond({'group': {'id': 'group1'}, 'jobs': jobs}, 201)
            job = {'id': 'id-single', 'status': 'done', 'seed': body['params'].get('seed', 123), 'params': body['params']}
            Handler.jobs[job['id']] = job
            return self.respond({'job': job}, 201)
        if path == '/api/projects':
            return self.respond({'project': {'id': 'p1'}}, 201)
        if path.endswith('/tracks'):
            return self.respond({'track': {'id': 't1'}}, 201)
        return self.respond({'error': {'message': path}}, 404)
    def do_PATCH(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        Handler.last_body = json.loads(raw)
        return self.respond({'track': {'id': 't1'}})


class TestCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.srv.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def run_cli(self, *args, ok=True):
        proc = subprocess.run([sys.executable, str(CLI), '--url', self.url, *args], capture_output=True, text=True, timeout=35)
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stderr)
        else:
            self.assertNotEqual(proc.returncode, 0)
        return proc

    def test_doctor(self):
        data = json.loads(self.run_cli('doctor').stdout)
        self.assertTrue(data['models_ready'])
        self.assertTrue(data['low_memory_effective'])

    def test_scenes(self):
        scenes = json.loads(self.run_cli('scenes').stdout)
        self.assertIn('saturn-boss', scenes)

    def test_create_scene(self):
        data = json.loads(self.run_cli('create', '--scene', 'earth-combat', '--seed', '100').stdout)
        self.assertEqual(data['job']['seed'], 100)
        self.assertIn('no vocals', str(Handler.last_body).lower())

    def test_variations_seeds(self):
        data = json.loads(self.run_cli('variations', '--scene', 'saturn-boss', '--seed', '300', '--count', '3').stdout)
        self.assertEqual([x['seed'] for x in data['jobs']], [300, 301, 302])

    def test_wait_and_download_no_overwrite(self):
        self.run_cli('create', '--scene', 'mars-battle')
        self.run_cli('wait', 'id-single', '--interval', '0.01', '--timeout', '1')
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'audio.flac'
            self.run_cli('download', 'id-single', '--out', str(output))
            self.assertEqual(output.read_bytes()[:4], b'fLaC')
            self.run_cli('download', 'id-single', '--out', str(output), ok=False)
            self.run_cli('download', 'id-single', '--out', str(output), '--overwrite')

    def test_instrumental_lora(self):
        self.run_cli('create', '--scene', 'menu', '--auto-instrumental-lora')
        self.assertEqual(Handler.last_body['loras'], [{'name': 'ar_inst', 'scale': 1.0}])

    def test_regenerate(self):
        with tempfile.TemporaryDirectory() as td:
            score = Path(td) / 's.abc'
            score.write_text('X:1\nT:My Song\nM:4/4\nL:1/8\nK:C\nCDEF GABc|', encoding='utf-8')
            self.run_cli('regenerate', '--parent-id', 'orig', '--abc-file', str(score), '--preset', 'quality')
            self.assertEqual(Handler.last_body['params']['parent_id'], 'orig')
            self.assertIn('CDEF', Handler.last_body['params']['abc'])

    def test_upload_cover(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'test.wav'
            path.write_bytes(b'RIFF0000WAVEfmtnotreallyaudio')
            self.run_cli('cover', '--file', str(path), '--style', 'instrumental space rock')
            self.assertEqual(Handler.last_body['kind'], 'cover')
            self.assertEqual(Handler.last_body['params']['upload_id'], 'upload123')

    def test_remote_rejected(self):
        proc = subprocess.run([sys.executable, str(CLI), '--url', 'http://evil.example:8765', 'doctor'], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('loopback', proc.stderr)

    @unittest.skipUnless(subprocess.run(['which', 'ffmpeg'], stdout=subprocess.DEVNULL).returncode == 0, 'ffmpeg missing')
    def test_export_and_loop(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'source.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=7',
                            '-c:a', 'pcm_s16le', str(source)], check=True)
            out = Path(td) / 'loop.ogg'
            proc = self.run_cli('export', '--input', str(source), '--out', str(out), '--loop', '--crossfade', '1', '--manifest')
            self.assertTrue(out.stat().st_size > 1000)
            self.assertTrue(Path(str(out) + '.json').exists())
            data = json.loads(proc.stdout)
            self.assertAlmostEqual(float(data['audio']['format']['duration']), 6.0, delta=0.15)


if __name__ == '__main__':
    unittest.main()
