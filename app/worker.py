"""Isolated child process. Exits with nonzero status on download failure."""
import json
import os
import sys
from pathlib import Path
from yt_dlp import YoutubeDL

MAX_BYTES = int(os.environ.get('MAX_BYTES', 150 * 1024 * 1024))


def pick_clean_format(info):
    """Prefer play/no-watermark streams; never claim pixel-level verification."""
    candidates = []
    for f in info.get('formats') or []:
        fid = str(f.get('format_id') or '').lower()
        note = str(f.get('format_note') or '').lower()
        if not f.get('format_id') or f.get('vcodec') in (None, 'none'):
            continue
        desc = f'{fid} {note}'
        if any(word in desc for word in ('watermark', 'download', 'wm_')) and 'no_watermark' not in desc:
            continue
        if not any(word in desc for word in ('play', 'nowm', 'no_watermark')):
            continue
        score = ((f.get('width') or 0) * (f.get('height') or 0), f.get('tbr') or 0)
        candidates.append((score, str(f['format_id'])))
    return max(candidates)[1] if candidates else None


def run(url, folder):
    params = {
        'quiet': True, 'no_warnings': True, 'noplaylist': True,
        'cachedir': False, 'ignoreerrors': False, 'socket_timeout': 12,
        'retries': 1, 'fragment_retries': 1, 'max_filesize': MAX_BYTES,
        'outtmpl': str(Path(folder) / '%(id).80s.%(ext)s'),
        'restrictfilenames': True,
        'allowed_extractors': ['TikTok', 'TikTokVM', 'TikTokUser'],
    }
    with YoutubeDL(dict(params, skip_download=True)) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict) or info.get('_type') in ('playlist', 'multi_video'):
        raise ValueError('Chỉ hỗ trợ một video TikTok công khai')
    fmt = pick_clean_format(info)
    if not fmt:
        raise ValueError('Không tìm thấy nguồn phát được đánh dấu không watermark')
    # Reuse extracted metadata to avoid a second URL extraction/redirect.
    with YoutubeDL(dict(params, format=fmt)) as ydl:
        ydl.process_ie_result(info, download=True)
    files = [p for p in Path(folder).iterdir() if p.is_file() and not p.name.endswith(('.part', '.ytdl'))]
    if len(files) != 1 or files[0].stat().st_size > MAX_BYTES:
        raise ValueError('Tệp video không hợp lệ hoặc vượt giới hạn')
    print(json.dumps({'filename': files[0].name}), flush=True)


if __name__ == '__main__':
    try:
        run(sys.argv[1], sys.argv[2])
    except Exception:
        # No traceback/URLs/cookies in client-facing error.
        print('Không thể tải video. TikTok có thể đã thay đổi hoặc không cung cấp nguồn phù hợp.', file=sys.stderr)
        sys.exit(1)
