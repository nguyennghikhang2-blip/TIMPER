"""Isolated child process. Exits with nonzero status on download failure."""
import json
import os
import re
import sys
from pathlib import Path
from yt_dlp import YoutubeDL

MAX_BYTES = int(os.environ.get('MAX_BYTES', 150 * 1024 * 1024))


def pick_clean_format(info):
    """Prefer non-watermarked video streams; labels are not pixel-level proof."""
    candidates = []
    for f in info.get('formats') or []:
        fid = str(f.get('format_id') or '').lower()
        note = str(f.get('format_note') or '').lower()
        if not fid or f.get('vcodec') in (None, 'none'):
            continue
        desc = f'{fid} {note}'
        # Refuse formats explicitly identified as containing a watermark.
        # Do NOT exclude every format with 'download' in its name: some are clean.
        if ('watermarked' in desc or 'with watermark' in desc or
                re.search(r'(^|[_\s-])wm([_\s-]|$)', desc)) and not any(
                    k in desc for k in ('no_watermark', 'nowm', 'without watermark')):
            continue
        # Only allow supported TikTok video streams, not arbitrary unknown formats.
        is_play = 'play' in fid or 'play' in note
        is_clean_download = 'download' in fid or 'download' in note
        if not (is_play or is_clean_download or 'nowm' in desc or 'no_watermark' in desc):
            continue
        priority = 2 if is_play or 'nowm' in desc or 'no_watermark' in desc else 1
        score = (priority, (f.get('width') or 0) * (f.get('height') or 0), f.get('tbr') or 0)
        candidates.append((score, str(f['format_id'])))
    return max(candidates)[1] if candidates else None


def classify_error(exc):
    """Emit only a safe diagnostic code; never expose URLs/tokens in public logs."""
    message = str(exc).lower()
    if 'không tìm thấy nguồn phát' in message:
        return 'NO_CLEAN_FORMAT'
    if any(s in message for s in ('ip address is blocked', '403 forbidden', 'http error 403', 'http error 429', 'too many requests')):
        return 'SOURCE_BLOCKED'
    if any(s in message for s in ('unable to extract', 'failed to parse', 'no video formats', 'unsupported url', 'no formats')):
        return 'EXTRACTION_FAILED'
    if any(s in message for s in ('timed out', 'temporary failure', 'connection error', 'name resolution', 'network is unreachable')):
        return 'NETWORK_ERROR'
    return 'DOWNLOAD_FAILED'


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
    except Exception as exc:
        # Safe diagnostic classification. Do not leak signed media URLs or cookies.
        print(classify_error(exc), file=sys.stderr, flush=True)
        sys.exit(1)
