"""Isolated child process. Exits with nonzero status on download failure."""
import json
import os
import re
import sys
from pathlib import Path
from yt_dlp import YoutubeDL

MAX_BYTES = int(os.environ.get('MAX_BYTES', 150 * 1024 * 1024))


def _is_explicitly_watermarked(f):
    """Reject only formats the extractor explicitly labels watermarked.

    Format IDs like ``download_addr`` aren't proof of a watermark on their own.
    """
    fid = str(f.get('format_id') or '').lower()
    note = str(f.get('format_note') or '').lower()
    label = f'{fid} {note}'
    if any(term in label for term in ('no_watermark', 'nowm', 'without watermark', 'no watermark', 'watermark-free')):
        return False
    return ('watermarked' in label or 'with watermark' in label or
            bool(re.search(r'(^|[_\s-])wm([_\s-]|$)', label)))


def pick_clean_format(info):
    """Choose the best *not explicitly watermarked* TikTok video format.

    TikTok's yt-dlp extractor also produces format IDs such as
    h264_540p_... and bytevc1_1080p_..., not just play/download/nowm.
    A missing watermark label is NOT proof the actual frames are clean.
    """
    candidates = []
    for f in info.get('formats') or []:
        fid = str(f.get('format_id') or '')
        if not fid or f.get('vcodec') in (None, 'none') or _is_explicitly_watermarked(f):
            continue
        if not f.get('url'):
            continue
        # Stay with actual downloadable video, not a storyboard/thumbnail.
        ext = str(f.get('ext') or '').lower()
        if ext in ('mhtml', 'jpg', 'jpeg', 'png', 'webp'):
            continue
        note = str(f.get('format_note') or '').lower()
        fid_lower = fid.lower()
        explicit_clean = any(x in (fid_lower + ' ' + note) for x in ('nowm', 'no_watermark', 'without watermark', 'no watermark'))
        # Prioritize explicit clean streams; otherwise prioritize resolution.
        # The latter is a best-effort choice, not a verified no-watermark promise.
        score = (
            int(explicit_clean),
            (f.get('width') or 0) * (f.get('height') or 0),
            f.get('height') or 0,
            f.get('tbr') or 0,
            int(f.get('acodec') not in (None, 'none')),
        )
        candidates.append((score, fid))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


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
        formats = info.get('formats') or []
        videos = [f for f in formats if f.get('vcodec') not in (None, 'none')]
        marked = [f for f in videos if _is_explicitly_watermarked(f)]
        # Print aggregate counts only, never links, signed media URLs or tokens.
        print(f'FORMAT_DIAGNOSTIC total={len(formats)} video={len(videos)} explicitly_watermarked={len(marked)} unrecognized={len(videos)-len(marked)}', file=sys.stderr, flush=True)
        raise ValueError('Không tìm thấy nguồn phát không bị đánh dấu watermark')
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
