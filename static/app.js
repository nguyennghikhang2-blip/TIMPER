const form = document.querySelector('#downloadForm');
const status = document.querySelector('#status');
const button = document.querySelector('#submit');
const params = new URLSearchParams(location.search);
if (params.has('url')) document.querySelector('#videoUrl').value = params.get('url');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const url = document.querySelector('#videoUrl').value.trim();
  button.disabled = true;
  status.textContent = 'Đang kiểm tra video và tải tệp...';
  try {
    const r = await fetch('/api/download', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    if(!r.ok) {let msg = 'Không thể tải video'; try{msg=(await r.json()).detail || msg;}catch{} throw new Error(msg);}
    const blob = await r.blob();
    const obj = URL.createObjectURL(blob);
    const a = document.createElement('a');a.href=obj;a.download='tiktok-video.mp4';document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(obj),60000);
    status.textContent = 'Đã nhận video. Kiểm tra mục Tệp đã tải về trong Safari.';
  } catch(e) {status.textContent = e.message;} finally {button.disabled=false;}
});
