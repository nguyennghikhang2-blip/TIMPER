"""Optional end-to-end check; needs network and installed project dependencies.
Run: python tests/live_video_check.py [tiktok_url]
Only use with videos you own or have permission to save.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_URL = 'https://www.tiktok.com/@rawrmusi/video/7688298692083846418?is_from_webapp=1&sender_device=pc'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from app.main import validate_url
    from app.worker import pick_clean_format
    from yt_dlp import YoutubeDL

    url = validate_url(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL)
    report = {'url': url, 'link_valid': True, 'media_downloaded': False, 'watermark_verified': False}
    print('Checking video metadata...', flush=True)
    try:
        with YoutubeDL({'quiet': True, 'no_warnings': True, 'skip_download': True,
                        'socket_timeout': 12, 'retries': 1,
                        'noplaylist': True, 'cachedir': False,
                        'allowed_extractors': ['TikTok', 'TikTokVM', 'TikTokUser']}) as dl:
            info = dl.extract_info(url, download=False)
        report.update({'video_id': info.get('id'), 'title': info.get('title'),
                       'available_formats': len(info.get('formats') or [])})
        fmt = pick_clean_format(info)
        report['preferred_clean_format'] = fmt
        if not fmt:
            report['result'] = 'NO_CLEAN_FORMAT_LABEL_FOUND'
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
        with tempfile.TemporaryDirectory(prefix='tiktok-live-check-') as tmp:
            cmd = [sys.executable, '-m', 'app.worker', url, tmp]
            try:
                p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=100)
            except subprocess.TimeoutExpired:
                report['result'] = 'DOWNLOAD_TIMEOUT'
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 3
            if p.returncode != 0:
                report['result'] = 'DOWNLOAD_FAILED'
                report['note'] = 'Check connectivity, availability and yt-dlp compatibility.'
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 4
            downloaded = Path(tmp) / json.loads(p.stdout)['filename']
            report['media_downloaded'] = True
            report['bytes'] = downloaded.stat().st_size
            if shutil.which('ffprobe'):
                probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                      'format=duration:stream=codec_type,width,height', '-of', 'json', str(downloaded)],
                      capture_output=True, text=True, timeout=20)
                if probe.returncode == 0:
                    report['media_info'] = json.loads(probe.stdout)
            out = ROOT / 'test-output.mp4'
            shutil.copyfile(downloaded, out)
            report['saved_to'] = str(out)
            report['result'] = 'DOWNLOADED_NEEDS_VISUAL_WATERMARK_CHECK'
            print(json.dumps(report, ensure_ascii=False, indent=2))
            print('\nIMPORTANT: Open test-output.mp4 and inspect moving watermark across the full video.')
            return 0
    except Exception as exc:
        report['result'] = 'EXTRACTION_OR_NETWORK_ERROR'
        report['error_type'] = type(exc).__name__
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 5


if __name__ == '__main__':
    sys.exit(main())
