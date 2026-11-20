"""Personal TikTok saver; only handle public videos you may lawfully download."""
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title='TikTok Save - Private', docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/assets', StaticFiles(directory=ROOT / 'static'), name='assets')

ALLOWED = {'tiktok.com', 'www.tiktok.com', 'm.tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'}
LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT', '8'))
MAX_BYTES = int(os.getenv('MAX_BYTES', str(150 * 1024 * 1024)))
TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', '95'))
BUCKETS: dict[str, deque] = defaultdict(deque)
LOCK = asyncio.Lock()
JOBS = asyncio.Semaphore(2)

class VideoRequest(BaseModel):
    url: str = Field(min_length=16, max_length=1000)


def validate_url(raw: str) -> str:
    raw = raw.strip()
    try:
        p = urlsplit(raw)
        host = (p.hostname or '').lower().rstrip('.')
        port = p.port
    except ValueError:
        raise HTTPException(400, 'Liên kết không hợp lệ')
    if (p.scheme != 'https' or host not in ALLOWED or p.username or p.password
            or port not in (None, 443) or not p.path.startswith('/')):
        raise HTTPException(400, 'Chỉ nhận liên kết HTTPS của TikTok')
    if ('%' in p.path or '..' in p.path or '//' in p.path
            or not re.fullmatch(r'[a-zA-Z0-9_/@.-]+', p.path)):
        raise HTTPException(400, 'Đường dẫn TikTok không hợp lệ')
    if not (p.path.startswith('/@') or p.path.startswith('/t/') or p.path.startswith('/video/')
            or host in {'vm.tiktok.com', 'vt.tiktok.com'}):
        raise HTTPException(400, 'Không phải liên kết video TikTok được hỗ trợ')
    # Discard tracking/query fragments before forwarding to yt-dlp.
    return urlunsplit(('https', host, p.path, '', ''))


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in {
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'X-Frame-Options': 'DENY',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        'Cache-Control': 'no-store',
    }.items():
        response.headers[key] = value
    return response


@app.get('/')
def home():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/health')
def health():
    return {'status': 'ok'}


async def run_worker(url: str, folder: str) -> Path:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, '-m', 'app.worker', url, folder,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env={**os.environ, 'MAX_BYTES': str(MAX_BYTES)},
        start_new_session=True,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        proc.kill()
        await proc.communicate()
        raise
    if proc.returncode != 0:
        # Worker emits only a safe diagnostic code; never return raw stderr.
        code = _.decode('utf-8', errors='replace').strip().splitlines()[-1:] if _ else []
        code = code[0] if code else 'DOWNLOAD_FAILED'
        errors = {
            'SOURCE_BLOCKED': 'TikTok có thể đang chặn địa chỉ IP của máy chủ Render (403/429).',
            'EXTRACTION_FAILED': 'Không trích xuất được dữ liệu video từ TikTok. Có thể TikTok đã đổi cách cung cấp dữ liệu.',
            'NETWORK_ERROR': 'Máy chủ không kết nối được tới nguồn video TikTok.',
            'NO_CLEAN_FORMAT': 'Không tìm thấy luồng video phù hợp để ưu tiên tải không watermark.',
            'DOWNLOAD_FAILED': 'Không tải được tệp video từ nguồn TikTok. Hãy xem nhật ký Render.'
        }
        print(f'TikTok download diagnostic: {code if code in errors else "DOWNLOAD_FAILED"}', file=sys.stderr, flush=True)
        raise ValueError(errors.get(code, errors['DOWNLOAD_FAILED']))
    try:
        name = json.loads(stdout.decode('utf-8'))['filename']
        file = (Path(folder) / name).resolve()
        if file.parent != Path(folder).resolve() or not file.is_file():
            raise ValueError('Invalid output')
        if not (0 < file.stat().st_size <= MAX_BYTES):
            raise ValueError('Invalid size')
    except (ValueError, KeyError, UnicodeError, OSError) as exc:
        raise ValueError('Tệp video trả về không hợp lệ') from exc
    return file


@app.post('/api/download')
async def download(body: VideoRequest, request: Request):
    url = validate_url(body.url)
    # Only trustworthy if server is NOT exposed via arbitrary forwarding proxy.
    remote = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    async with LOCK:
        q = BUCKETS[remote]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= LIMIT_REQUESTS:
            raise HTTPException(429, 'Quá nhiều yêu cầu. Thử lại sau một phút.')
        q.append(now)
        if len(BUCKETS) > 5000:
            for key in list(BUCKETS):
                if not BUCKETS[key] or now - BUCKETS[key][-1] > 60:
                    BUCKETS.pop(key, None)
    folder = tempfile.mkdtemp(prefix='tiktok-save-')
    try:
        async with JOBS:
            file = await run_worker(url, folder)
        suffix = file.suffix.lower()
        return FileResponse(file, media_type='video/mp4' if suffix == '.mp4' else 'application/octet-stream',
                            filename='tiktok-video' + suffix,
                            background=BackgroundTask(shutil.rmtree, folder, ignore_errors=True))
    except asyncio.TimeoutError:
        raise HTTPException(504, 'Tải video quá thời gian cho phép')
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    finally:
        # On a successful response, background task owns cleanup. On an error clean now.
        if 'file' not in locals():
            shutil.rmtree(folder, ignore_errors=True)
