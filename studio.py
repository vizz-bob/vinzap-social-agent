"""Video studio: makes 9:16 MP4 (Reels / Stories / Shorts) from text + optional images.
Needs: Pillow, numpy, ffmpeg. Original synthesized music = no copyright claims."""
import os, math, subprocess, random, wave, tempfile, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
EN = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
HI = os.path.join(HERE, "fonts", "FreeSansBold.ttf")
W, H, FPS = 720, 1280, 30

THEMES = {
 "navratri": dict(a=(120,10,70), b=(255,120,20), accent=(255,225,80), tag="🪔"),
 "dussehra": dict(a=(60,10,10), b=(255,90,20), accent=(255,215,0), tag="🏹"),
 "diwali":   dict(a=(15,10,60), b=(255,150,0), accent=(255,230,120), tag="🪔"),
 "product":  dict(a=(15,20,50), b=(40,110,255), accent=(255,225,60), tag=""),
 "custom":   dict(a=(20,20,40), b=(160,40,200), accent=(255,225,60), tag=""),
}

def font(text, size):
    dev = any('ऀ' <= c <= 'ॿ' for c in text)
    return ImageFont.truetype(HI if dev else EN, size)

def gradient(a, b, t=0.0):
    y = np.linspace(0, 1, H)[:, None]
    y = np.clip(y + 0.08*math.sin(t*2), 0, 1)
    arr = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        arr[:, :, i] = (a[i]*(1-y) + b[i]*y)
    return arr.astype(np.uint8)

def wrap(draw, text, size, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur+" "+w).strip()
        if draw.textlength(t, font=font(t, size)) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def text_block(img, text, y, size, fill, t, start, shadow=True):
    """pop-in centered text."""
    if t < start: return
    k = min(1, (t-start)/0.35); s = 1+0.25*math.sin(k*math.pi)*(1-k)
    d = ImageDraw.Draw(img)
    lines = wrap(d, text, size, W-90)
    lh = int(size*1.25); total = lh*len(lines)
    for i, ln in enumerate(lines):
        f = font(ln, int(size*s*min(1, 0.4+k)))
        w = d.textlength(ln, font=f); x = (W-w)/2; yy = y - total/2 + i*lh
        if shadow: d.text((x+3, yy+4), ln, font=f, fill=(0,0,0), stroke_width=2, stroke_fill=(0,0,0))
        d.text((x, yy), ln, font=f, fill=fill, stroke_width=3, stroke_fill=(0,0,0))

def sparkles(img, t, n, color, seed=1):
    r = random.Random(seed); d = ImageDraw.Draw(img)
    for i in range(n):
        x = r.uniform(0, W); sp = r.uniform(40, 140); ph = r.uniform(0, 6)
        y = (r.uniform(0, H) - t*sp) % H; s = r.uniform(2, 7)*(0.6+0.4*math.sin(t*4+ph))
        d.ellipse((x-s, y-s, x+s, y+s), fill=color)

def diya(img, cx, cy, t, accent):
    d = ImageDraw.Draw(img)
    d.pieslice((cx-60, cy-30, cx+60, cy+50), 0, 180, fill=(190, 90, 30))
    fl = 1+0.12*math.sin(t*14+cx)
    for rr, col in ((60, (255, 140, 0)), (40, (255, 200, 40)), (22, (255, 250, 200))):
        r = rr*fl
        d.polygon([(cx, cy-30-r*1.5), (cx-r*0.55, cy-30), (cx+r*0.55, cy-30)], fill=col)

def rangoli(img, cx, cy, t, accent):
    d = ImageDraw.Draw(img)
    for ring, (rad, n) in enumerate(((230, 16), (160, 12), (95, 8))):
        for i in range(n):
            a = 2*math.pi*i/n + t*(0.5 if ring % 2 else -0.5)
            x, y = cx+rad*math.cos(a), cy+rad*math.sin(a); s = 18-ring*3
            col = [(255, 90, 140), (255, 210, 60), (90, 220, 255)][(i+ring) % 3]
            d.ellipse((x-s, y-s, x+s, y+s), fill=col)
    d.ellipse((cx-24, cy-24, cx+24, cy+24), fill=accent)

def fit_cover(im, w, h):
    r = max(w/im.width, h/im.height); im = im.resize((int(im.width*r)+1, int(im.height*r)+1))
    l, t = (im.width-w)//2, (im.height-h)//2
    return im.crop((l, t, l+w, t+h))

def photo_layer(img, photos, t, dur):
    """product/custom photos on rounded card with Ken Burns + slide cuts."""
    if not photos: return
    seg = dur/len(photos); i = min(int(t/seg), len(photos)-1); lt = (t-i*seg)/seg
    z = 1+0.08*lt; cw, ch = 600, 600
    base = photos[i]; im = fit_cover(base, int(cw*z), int(ch*z))
    l, tp = (im.width-cw)//2, (im.height-ch)//2; im = im.crop((l, tp, l+cw, tp+ch))
    mask = Image.new("L", (cw, ch), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw, ch), 36, fill=255)
    slide = max(0, 1-(t-i*seg)/0.35)*W if i > 0 else 0
    img.paste(im, (int((W-cw)/2+slide), 330), mask)

def frame(spec, t, dur, photos):
    th = THEMES[spec.get("theme", "custom")]; k = spec.get("theme", "custom")
    img = Image.fromarray(gradient(th["a"], th["b"], t)).convert("RGB")
    sparkles(img, t, 40, th["accent"])
    if k in ("navratri", "diwali", "dussehra") and not photos:
        rangoli(img, W//2, 640, t, th["accent"])
    if k in ("diwali", "navratri"):
        for j, x in enumerate((150, 360, 570)): diya(img, x, 1010, t, th["accent"])
    photo_layer(img, photos, t, dur)
    d = ImageDraw.Draw(img)
    text_block(img, spec["hook"], 170, 66, th["accent"], t, 0.1)
    if spec.get("sub"): text_block(img, spec["sub"], 290, 38, (255, 255, 255), t, 0.7)
    if k in ("navratri", "diwali", "dussehra") and not photos:
        text_block(img, spec.get("main", ""), 640, 70, (255, 255, 255), t, 1.0)
    if spec.get("badge"):
        k2 = min(1, max(0, (t-2.0)/0.3)); bw = 260*k2
        if bw > 10:
            d.rounded_rectangle((W/2-bw/2, 960, W/2+bw/2, 1030), 30, fill=th["accent"])
            f = font(spec["badge"], 40); w = d.textlength(spec["badge"], font=f)
            if k2 > .9: d.text((W/2-w/2, 972), spec["badge"], font=f, fill=(20, 20, 20))
    if spec.get("offer"):
        pulse = 1+0.04*math.sin(t*6); f = font(spec["offer"], int(34*pulse)); w = d.textlength(spec["offer"], font=f)
        d.rounded_rectangle((W/2-w/2-26, 1045, W/2+w/2+26, 1115), 35, fill=(220, 30, 40), outline=(255, 255, 255), width=3)
        d.text((W/2-w/2, 1056), spec["offer"], font=f, fill=(255, 255, 255))
    if spec.get("cta") and t > dur-3: text_block(img, spec["cta"], 1130, 36, (255, 255, 255), t, dur-3)
    # progress bar
    d.rectangle((0, 0, W*t/dur, 8), fill=th["accent"])
    return img

def synth(path, dur, bpm=104, seed=3, mood="festive"):
    sr = 44100; n = int(sr*dur); rng = np.random.default_rng(seed); out = np.zeros(n)
    beat = 60/bpm; scale = [0, 2, 4, 7, 9] if mood != "minor" else [0, 3, 5, 7, 10]
    root = 220.0
    def add(start, sig):
        i = int(start*sr); j = min(n, i+len(sig));
        if i < n: out[i:j] += sig[:j-i]
    tt = np.arange(int(sr*0.25))/sr
    kick = np.sin(2*np.pi*(55+90*np.exp(-tt*30))*tt)*np.exp(-tt*14)
    hat = rng.standard_normal(len(tt)//4)*np.exp(-np.arange(len(tt)//4)/sr*90)
    b = 0
    while b*beat < dur:
        s = b*beat
        if b % 2 == 0: add(s, kick*0.9)
        add(s+beat/2, hat*0.25)
        note = root*2**(scale[(b*3+seed) % 5]/12)
        nt = np.arange(int(sr*beat*0.9))/sr
        add(s, 0.18*np.sin(2*np.pi*note*nt)*np.exp(-nt*5))
        add(s+beat/2, 0.1*np.sin(2*np.pi*note*2*nt)*np.exp(-nt*7))
        b += 1
    pad = 0.05*np.sin(2*np.pi*root/2*np.arange(n)/sr); out += pad
    out *= np.minimum(1, (dur-np.arange(n)/sr)/0.6)
    out = out/max(1e-6, np.abs(out).max())*0.8
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((out*32767).astype(np.int16).tobytes())

def render(spec, out_path, dur=15, photo_paths=()):
    """spec: theme, hook, sub, main, badge, cta. Returns out_path."""
    photos = []
    for p in photo_paths:
        try: photos.append(Image.open(p).convert("RGB"))
        except Exception: pass
    tmp = tempfile.mkdtemp(); wav = os.path.join(tmp, "m.wav"); synth(wav, dur, seed=abs(hash(spec["hook"])) % 50)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-vf", "scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(dur*FPS)):
        p.stdin.write(frame(spec, i/FPS, dur, photos).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError("ffmpeg failed")
    return out_path

def still(spec, out_png, photo_paths=(), t=1.6):
    photos = []
    for p in photo_paths:
        try: photos.append(Image.open(p).convert("RGB"))
        except Exception: pass
    frame(spec, t, 9, photos).resize((1080, 1920)).save(out_png)
    return out_png


def _pil(paths):
    out = []
    for p in paths:
        try: out.append(Image.open(p).convert("RGB"))
        except Exception: pass
    if not out: raise RuntimeError("no usable photos")
    return out

def render_sale(info, photo_paths, out_path, dur=15):
    """animated sale Reel (720x1280 -> 1080x1920) from store photos + info"""
    import art, zlib
    photos = _pil(photo_paths); tmp = tempfile.mkdtemp(); wav = os.path.join(tmp, "m.wav")
    synth(wav, dur, seed=zlib.crc32(info["headline"].encode()) % 50)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-vf", "scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(dur*FPS)):
        p.stdin.write(art.scene(W, H, info, photos, i/FPS, dur, "reel").convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError("ffmpeg failed")
    return out_path

def thumb_sale(info, photo_paths, out_jpg):
    import art
    art.scene(W, H, info, _pil(photo_paths), 6.0, 15, "reel").convert("RGB").save(out_jpg, quality=88); return out_jpg

def poster_sale(info, photo_paths, out_jpg):
    """high-quality 1080x1350 feed poster"""
    import art
    art.scene(1080, 1350, info, _pil(photo_paths)[:1], 6.0, 15, "poster").convert("RGB").save(out_jpg, quality=95); return out_jpg
