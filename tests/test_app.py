import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app, validate_url

@pytest.mark.parametrize('url', [
    'https://evil.test/abc', 'http://www.tiktok.com/@a/video/1',
    'https://www.tiktok.com.evil.test/@a/video/1',
    'https://user:pass@tiktok.com/@a/video/1',
    'https://tiktok.com:8888/@a/video/1',
    'https://tiktok.com/@a/video/1%0a',
    'https://tiktok.com/@a/../../private',
])
def test_rejects_bad_url(url):
    with pytest.raises(HTTPException):
        validate_url(url)

@pytest.mark.parametrize('url', [
    'https://www.tiktok.com/@abc/video/123?is_from_webapp=1',
    'https://vm.tiktok.com/ABC123/', 'https://vt.tiktok.com/ABC123/',
])
def test_accepts_tiktok_url(url):
    clean = validate_url(url)
    assert clean.startswith('https://')
    assert '?' not in clean


def test_home_and_headers():
    c = TestClient(app)
    r = c.get('/')
    assert r.status_code == 200
    assert 'TikTok Save' in r.text
    assert r.headers['X-Content-Type-Options'] == 'nosniff'
    assert c.get('/health').json() == {'status': 'ok'}


def test_download_rejects_invalid_before_network():
    c = TestClient(app)
    r = c.post('/api/download', json={'url': 'https://www.example.com/@x/video/1'})
    assert r.status_code == 400
