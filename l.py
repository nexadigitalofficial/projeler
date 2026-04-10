#!/usr/bin/env python3
"""
patch_l.py — l.py'yi imgbb destekli versiyona çevirir.
Kullanım:
    python patch_l.py          # l.py ile aynı klasörde çalıştır
"""

from pathlib import Path
import sys

TARGET = Path("l.py")
BACKUP = Path("l.py.bak")

if not TARGET.exists():
    print("❌ l.py bulunamadı. Bu scripti l.py ile aynı klasörde çalıştır.")
    sys.exit(1)

code = TARGET.read_text(encoding="utf-8")

# ─────────────────────────────────────────────────────────────
# PATCH 1: import satırına requests ve time ekle
# ─────────────────────────────────────────────────────────────
OLD_IMPORT = "import os, io, json, base64, textwrap, html, re, hashlib, pickle, shutil\nfrom pathlib import Path\nfrom datetime import datetime"
NEW_IMPORT = """\
import os, io, json, base64, textwrap, html, re, hashlib, pickle, shutil
import time
import requests
from pathlib import Path
from datetime import datetime"""

if OLD_IMPORT not in code:
    print("⚠  Import bloğu beklenenden farklı — manuel kontrol gerekebilir.")
else:
    code = code.replace(OLD_IMPORT, NEW_IMPORT, 1)
    print("✓  PATCH 1: import satırları güncellendi")

# ─────────────────────────────────────────────────────────────
# PATCH 2: AYARLAR bloğuna imgbb ayarlarını ekle
# ─────────────────────────────────────────────────────────────
OLD_ASSETS = 'ASSETS_DIR       = "sunum_assets"'
NEW_ASSETS = '''\
ASSETS_DIR       = "sunum_assets"   # sadece PDF ve video için kullanılacak

# ── imgbb ────────────────────────────────────────────────────
IMGBB_API_KEY    = "a441724ad7d0f1ad163ac49f561f8af5"
IMGBB_CACHE_FILE = "imgbb_cache.json"   # yüklenen URL\'leri saklar (resume)
IMGBB_RETRY      = 3
IMGBB_DELAY      = 0.4   # istek arası bekleme (saniye)'''

if OLD_ASSETS not in code:
    print("⚠  ASSETS_DIR satırı bulunamadı — manuel kontrol gerekebilir.")
else:
    code = code.replace(OLD_ASSETS, NEW_ASSETS, 1)
    print("✓  PATCH 2: imgbb ayarları eklendi")

# ─────────────────────────────────────────────────────────────
# PATCH 3: Asset fonksiyonlarını imgbb versiyonuyla değiştir
# ─────────────────────────────────────────────────────────────
OLD_ASSET_FUNCS = '''\
def _prepare_image(data: bytes, size: tuple) -> tuple:
    img = Image.open(io.BytesIO(data))
    img.thumbnail(size, Image.LANCZOS)
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (4, 4, 12))
        paste_img = img.convert("RGBA") if img.mode != "RGBA" else img
        bg.paste(paste_img, mask=paste_img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img

def make_thumb(data: bytes, mime: str, uid: str, size=(600, 400)) -> str:
    try:
        Path(ASSETS_DIR).mkdir(exist_ok=True)
        p = Path(ASSETS_DIR) / f"{uid}_t.jpg"
        if p.exists():
            return f"{ASSETS_DIR}/{uid}_t.jpg"
        img = _prepare_image(data, size)
        img.save(str(p), format="JPEG", quality=82, optimize=True)
        return f"{ASSETS_DIR}/{uid}_t.jpg"
    except Exception as e:
        print(f"    ⚠  Thumbnail hatası ({uid}): {e}")
        return ""

def make_large(data: bytes, mime: str, uid: str, size=(1600, 1200)) -> str:
    try:
        Path(ASSETS_DIR).mkdir(exist_ok=True)
        p = Path(ASSETS_DIR) / f"{uid}_l.jpg"
        if p.exists():
            return f"{ASSETS_DIR}/{uid}_l.jpg"
        img = _prepare_image(data, size)
        img.save(str(p), format="JPEG", quality=90, optimize=True)
        return f"{ASSETS_DIR}/{uid}_l.jpg"
    except Exception as e:
        print(f"    ⚠  Large görsel hatası ({uid}): {e}")
        return ""

def save_video(data: bytes, uid: str) -> str:
    try:
        Path(ASSETS_DIR).mkdir(exist_ok=True)
        p = Path(ASSETS_DIR) / f"{uid}.mp4"
        p.write_bytes(data)
        return f"{ASSETS_DIR}/{uid}.mp4"
    except Exception:
        return ""

def save_pdf(data: bytes, uid: str) -> str:
    try:
        Path(ASSETS_DIR).mkdir(exist_ok=True)
        p = Path(ASSETS_DIR) / f"{uid}.pdf"
        p.write_bytes(data)
        return f"{ASSETS_DIR}/{uid}.pdf"
    except Exception:
        return ""'''

NEW_ASSET_FUNCS = '''\
# ── imgbb URL önbelleği ──────────────────────────────────────
def _load_imgbb_cache() -> dict:
    p = Path(IMGBB_CACHE_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_imgbb_cache(cache: dict):
    Path(IMGBB_CACHE_FILE).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )

_imgbb_cache: dict = _load_imgbb_cache()


# ── imgbb\'ye ham bytes yükle ─────────────────────────────────
def _upload_bytes_to_imgbb(img_bytes: bytes, name: str):
    encoded = base64.b64encode(img_bytes).decode("utf-8")
    for attempt in range(1, IMGBB_RETRY + 1):
        try:
            resp = requests.post(
                "https://api.imgbb.com/1/upload",
                data={"key": IMGBB_API_KEY, "image": encoded, "name": name},
                timeout=30,
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("success"):
                    return result["data"]["url"]
            print(f"    ⚠  imgbb yanıt {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"    ⚠  imgbb deneme {attempt}/{IMGBB_RETRY}: {e}")
        if attempt < IMGBB_RETRY:
            time.sleep(2)
    return None


# ── Görsel hazırla (Pillow) ───────────────────────────────────
def _prepare_image(data: bytes, size: tuple):
    img = Image.open(io.BytesIO(data))
    img.thumbnail(size, Image.LANCZOS)
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (4, 4, 12))
        paste_img = img.convert("RGBA") if img.mode != "RGBA" else img
        bg.paste(paste_img, mask=paste_img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img

def _make_jpeg_bytes(data: bytes, size: tuple, quality: int) -> bytes:
    img = _prepare_image(data, size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


# ── Thumbnail → imgbb ────────────────────────────────────────
def make_thumb(data: bytes, mime: str, uid: str, size=(600, 400)) -> str:
    cache_key = f"{uid}_t"
    if cache_key in _imgbb_cache:
        return _imgbb_cache[cache_key]
    try:
        jpg_bytes = _make_jpeg_bytes(data, size, quality=82)
        url = _upload_bytes_to_imgbb(jpg_bytes, cache_key)
        if url:
            _imgbb_cache[cache_key] = url
            _save_imgbb_cache(_imgbb_cache)
            time.sleep(IMGBB_DELAY)
            return url
    except Exception as e:
        print(f"    ⚠  Thumbnail hatası ({uid}): {e}")
    return ""


# ── Large görsel → imgbb ─────────────────────────────────────
def make_large(data: bytes, mime: str, uid: str, size=(1600, 1200)) -> str:
    cache_key = f"{uid}_l"
    if cache_key in _imgbb_cache:
        return _imgbb_cache[cache_key]
    try:
        jpg_bytes = _make_jpeg_bytes(data, size, quality=90)
        url = _upload_bytes_to_imgbb(jpg_bytes, cache_key)
        if url:
            _imgbb_cache[cache_key] = url
            _save_imgbb_cache(_imgbb_cache)
            time.sleep(IMGBB_DELAY)
            return url
    except Exception as e:
        print(f"    ⚠  Large görsel hatası ({uid}): {e}")
    return ""


# ── Video → local (imgbb video desteklemiyor) ─────────────────
def save_video(data: bytes, uid: str) -> str:
    try:
        Path(ASSETS_DIR).mkdir(exist_ok=True)
        p = Path(ASSETS_DIR) / f"{uid}.mp4"
        p.write_bytes(data)
        return f"{ASSETS_DIR}/{uid}.mp4"
    except Exception:
        return ""


# ── PDF → local (viewer için şart) ───────────────────────────
def save_pdf(data: bytes, uid: str) -> str:
    try:
        Path(ASSETS_DIR).mkdir(exist_ok=True)
        p = Path(ASSETS_DIR) / f"{uid}.pdf"
        p.write_bytes(data)
        return f"{ASSETS_DIR}/{uid}.pdf"
    except Exception:
        return ""'''

if OLD_ASSET_FUNCS not in code:
    print("⚠  Asset fonksiyon bloğu bulunamadı — l.py değiştirilmiş olabilir.")
    print("   Manuel olarak l_degisiklikler.py dosyasındaki fonksiyonları uygula.")
else:
    code = code.replace(OLD_ASSET_FUNCS, NEW_ASSET_FUNCS, 1)
    print("✓  PATCH 3: make_thumb / make_large → imgbb versiyonuna değiştirildi")

# ─────────────────────────────────────────────────────────────
# Yedek al ve kaydet
# ─────────────────────────────────────────────────────────────
BACKUP.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
TARGET.write_text(code, encoding="utf-8")

print()
print("═" * 52)
print(f"  ✓ Yedek: {BACKUP.name}")
print(f"  ✓ Güncellendi: {TARGET.name}")
print()
print("  Kurulum:")
print("    pip install requests")
print()
print("  Çalıştır:")
print("    python l.py")
print()
print("  Görseller artık imgbb'ye yüklenir.")
print("  URL'ler imgbb_cache.json'a kaydedilir (resume destekli).")
print("  sunum_assets/ → sadece PDF ve video kalır.")
print("═" * 52)
