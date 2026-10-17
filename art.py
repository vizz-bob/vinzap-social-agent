"""Sale-poster / sale-reel designer (original Vinzap design, competitor-ad style):
festival badge + headline banner, product photo, price circle (+ WAS/SAVE tags when a real
discount exists), feature chips from your product page, CTA, footer bar with your website.
scene(...) draws one frame. Poster = the finished frame; Reel = animated frames."""
import os, math, random, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
RED, YEL, BLUE, BLACK, WHITE, GOLD = (214, 28, 40), (255, 222, 30), (20, 70, 215), (16, 16, 20), (255, 255, 255), (255, 200, 40)
CHIP_COLORS = [(255, 120, 30), (40, 170, 90), (225, 45, 60), (30, 90, 220)]
FEST = {
    "navratri": dict(name="NAVRATRI", bg1=(110, 15, 90), bg2=(255, 110, 40), accent=(255, 215, 70)),
    "dussehra": dict(name="DUSSEHRA", bg1=(80, 15, 15), bg2=(255, 100, 20), accent=(255, 210, 0)),
    "diwali":   dict(name="DIWALI",   bg1=(20, 15, 70), bg2=(255, 150, 20), accent=(255, 225, 110)),
}

@functools.lru_cache(None)
def F(size): return ImageFont.truetype(FONT, max(8, int(size)))

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_back(k):
    c1 = 1.70158; c3 = c1 + 1; return 1 + c3*(k-1)**3 + c1*(k-1)**2
def pop(t, start, dur=0.45):
    """0 before start, overshoots to ~1.1 then settles at 1."""
    if t < start: return 0.0
    return ease_back(clamp((t-start)/dur))
def slide(t, start, dur=0.45):
    return 1 - (1-clamp((t-start)/dur))**3 if t >= start else 0.0

def wrap_lines(d, text, maxw, size, maxlines=2):
    words = text.split(); lines = []; cur = ""
    for w in words:
        tt = (cur+" "+w).strip()
        if d.textlength(tt, font=F(size)) <= maxw: cur = tt
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    if len(lines) > maxlines and size > 24: return wrap_lines(d, text, maxw, size-4, maxlines)
    return lines[:maxlines], size

def text_c(d, xy, text, size, fill, stroke=0, anchor="mm"):
    d.text(xy, text, font=F(size), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=BLACK)

# ---------- background ----------
_bg = {}
def background(W, H, fest, t):
    key = (W, H, fest)
    if key not in _bg:
        c = FEST[fest]; y = np.linspace(0, 1, H)[:, None, None].astype(np.float32)
        a = np.array(c["bg1"], np.float32); b = np.array(c["bg2"], np.float32)
        base = Image.fromarray((a*(1-y) + b*y).astype(np.uint8).repeat(W, axis=1)).convert("RGB")
        lay = Image.new("RGB", (W, H*2), (0, 0, 0)); d = ImageDraw.Draw(lay); r = random.Random(7)
        for _ in range(48):
            x, yy, rad = r.uniform(0, W), r.uniform(0, H*2), r.uniform(14, 62)*W/1080
            col = tuple(int(v*r.uniform(.45, .9)) for v in c["accent"])
            d.ellipse((x-rad, yy-rad, x+rad, yy+rad), fill=col)
        lay = lay.filter(ImageFilter.GaussianBlur(7*W/1080)).point(lambda v: int(v*0.6))
        _bg[key] = (base, lay)
    base, lay = _bg[key]
    off = int((t*45) % H)
    return ImageChops.screen(base, lay.crop((0, off, W, off+H)))

# ---------- shapes ----------
def burst(d, cx, cy, r, rot=0, n=18):
    pts = [(cx+(r if i % 2 == 0 else r*0.87)*math.cos(rot+math.pi*i/n), cy+(r if i % 2 == 0 else r*0.87)*math.sin(rot+math.pi*i/n)) for i in range(n*2)]
    d.polygon(pts, fill=RED); d.line(pts+[pts[0]], fill=GOLD, width=max(2, int(r*0.04)))

def diya(d, cx, cy, s, t):
    d.pieslice((cx-s, cy-s*0.5, cx+s, cy+s*0.8), 0, 180, fill=(200, 95, 30))
    f = 1+0.12*math.sin(t*14+cx)
    for rr, col in ((s*.55, (255, 140, 0)), (s*.36, (255, 205, 50)), (s*.2, (255, 250, 210))):
        d.polygon([(cx, cy-s*0.5-rr*1.6*f), (cx-rr*.5, cy-s*0.5), (cx+rr*.5, cy-s*0.5)], fill=col)

def festival_badge(img, cx, cy, r, fest, label2, t, k):
    if k <= 0.02: return
    d = ImageDraw.Draw(img); r = r*k
    burst(d, cx, cy, r, rot=t*0.35)
    d.ellipse((cx-r*0.72, cy-r*0.72, cx+r*0.72, cy+r*0.72), outline=GOLD, width=max(2, int(r*0.03)))
    text_c(d, (cx, cy-r*0.22), FEST[fest]["name"], r*0.30, WHITE, stroke=max(1, int(r*0.012)))
    text_c(d, (cx, cy+r*0.16), label2, r*0.36, YEL, stroke=max(1, int(r*0.012)))
    for dx in (-0.36, 0, 0.36): diya(d, cx+dx*r, cy+r*0.58, r*0.12, t)

def rupee(p):
    return "₹" + (f"{p:,.0f}" if float(p) == int(p) else f"{p:,.2f}")

def price_block(img, cx, cy, r, info, t, k):
    if k <= 0.02: return
    d = ImageDraw.Draw(img); pulse = 1+0.025*math.sin(t*5); r = r*k*pulse
    d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=YEL); d.ellipse((cx-r*0.89, cy-r*0.89, cx+r*0.89, cy+r*0.89), fill=BLUE)
    text_c(d, (cx, cy-r*0.52), "NOW" if info.get("was") else "ONLY", r*0.26, WHITE)
    s = rupee(info["price"]); sz = r*0.8
    while d.textlength(s, font=F(sz)) > r*1.45 and sz > 20: sz -= 3
    text_c(d, (cx, cy+r*0.08), s, sz, WHITE)
    text_c(d, (cx, cy+r*0.62), "vinzapstore.in", r*0.15, (190, 215, 255))

def was_save(img, x, y, u, info, k):
    if not info.get("was") or k <= 0.02: return
    d = ImageDraw.Draw(img); w, h = 330*u*k, 58*u
    d.rectangle((x, y, x+w, y+h), fill=YEL)
    s = "WAS " + rupee(info["was"]); text_c(d, (x+w/2, y+h/2), s, 34*u, BLACK)
    tw = d.textlength(s, font=F(34*u)); d.line((x+w/2-tw/2, y+h/2, x+w/2+tw/2, y+h/2), fill=BLACK, width=max(2, int(4*u)))
    d.rectangle((x, y+h, x+w, y+2*h), fill=RED); text_c(d, (x+w/2, y+h*1.5), "SAVE " + rupee(info["was"]-info["price"]), 34*u, WHITE)

def chip(img, x, y, w, h, text, color, k):
    if k <= 0.02: return
    d = ImageDraw.Draw(img); off = (1-k)*-w*0.6
    x += off
    d.rounded_rectangle((x, y, x+w, y+h), h//2, fill=WHITE)
    cx, cy, r = x+h/2, y+h/2, h*0.36
    d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=color)
    d.line([(cx-r*.5, cy), (cx-r*.12, cy+r*.42), (cx+r*.55, cy-r*.4)], fill=WHITE, width=max(3, int(h*0.08)))
    sz = h*0.42
    while d.textlength(text, font=F(sz)) > w-h*1.3 and sz > 16: sz -= 2
    d.text((x+h*0.95, y+h/2), text, font=F(sz), fill=(30, 30, 40), anchor="lm")

# ---------- photos ----------
def cover(im, w, h, z=1.0):
    r = max(w/im.width, h/im.height)*z
    im = im.resize((max(w, int(im.width*r)+1), max(h, int(im.height*r)+1)), Image.BILINEAR)
    l, tp = (im.width-w)//2, (im.height-h)//2
    return im.crop((l, tp, l+w, tp+h))

_mask = {}
def rmask(w, h, rad):
    if (w, h, rad) not in _mask:
        m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w, h), rad, fill=255); _mask[(w, h, rad)] = m
    return _mask[(w, h, rad)]

def photo_box(img, photos, t, dur, box, rad):
    x, y, w, h = [int(v) for v in box]
    seg = dur/len(photos); i = min(int(t/seg), len(photos)-1); lt = clamp((t-i*seg)/seg)
    tile = Image.new("RGB", (w, h))
    if i > 0 and (t-i*seg) < 0.35: tile.paste(cover(photos[i-1], w, h, 1.08))
    cur = cover(photos[i], w, h, 1+0.08*lt)
    if i > 0 and (t-i*seg) < 0.35:
        sh = int((1-(t-i*seg)/0.35)**2*w); tile.paste(cur, (sh, 0))
    else: tile.paste(cur)
    sh = Image.new("L", img.size, 0); ImageDraw.Draw(sh).rounded_rectangle((x+8, y+14, x+w+8, y+h+14), rad, fill=110)
    img.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    img.paste(tile, (x, y), rmask(w, h, rad))

# ---------- the scene ----------
def scene(W, H, info, photos, t, dur, mode="reel"):
    """mode 'reel' (9:16) or 'poster' (4:5). info keys: fest, headline, strip, price, was, feats, cta, label2, site"""
    u = W/1080; fest = info["fest"]
    img = background(W, H, fest, t); d = ImageDraw.Draw(img)
    banner_h = (205 if mode == "reel" else 175)*u; strip_h = 62*u; foot_h = 118*u
    # photo area
    if mode == "reel":
        card = (60*u, 310*u, 960*u, 940*u)
        k = slide(t, 0.05, 0.5)
        photo_box(img, photos, t, dur, (card[0], card[1]+(1-k)*60*u, card[2], card[3]), int(44*u))
    else:
        top = banner_h+strip_h; bot = H-foot_h
        photo_box(img, photos, t, dur, (0, top, W, bot-top), 0)
        g = Image.new("L", (W, int(260*u)), 0); gd = ImageDraw.Draw(g)
        for yy in range(g.height): gd.line((0, yy, W, yy), fill=int(190*yy/g.height))
        img.paste((0, 0, 0), (0, int(bot-260*u)), g); d = ImageDraw.Draw(img)
    # banner sliding down
    bk = slide(t, 0.0, 0.5); by = -banner_h*(1-bk)
    d.rectangle((0, by, W, by+banner_h), fill=RED)
    d.rectangle((0, by+banner_h, W, by+banner_h+strip_h), fill=YEL)
    lines, sz = wrap_lines(d, info["headline"].upper(), 700*u, 78*u, 2)
    lh = sz*1.08; y0 = by+banner_h/2-lh*(len(lines)-1)/2
    for n, ln in enumerate(lines): text_c(d, (W*0.64, y0+n*lh), ln, sz, WHITE, stroke=max(1, int(2*u)))
    sz2 = 34*u
    while d.textlength(info["strip"], font=F(sz2)) > 420*u and sz2 > 16: sz2 -= 2
    text_c(d, (W*0.525, by+banner_h+strip_h/2), info["strip"], sz2, (25, 25, 30))
    # brand pill on strip (right)
    bp = pop(t, 0.6)
    if bp > 0.02:
        bw, bh = 250*u*bp, 50*u; bx, byy = W-bw-24*u, by+banner_h+strip_h/2-bh/2
        d.rounded_rectangle((bx, byy, bx+bw, byy+bh), bh/2, fill=WHITE, outline=RED, width=max(2, int(3*u)))
        if bp > .85: text_c(d, (bx+bw/2, byy+bh/2), "VINZAP", 30*u, RED)
    # festival badge
    festival_badge(img, int(150*u), int(by+banner_h*0.62), 150*u, fest, info["label2"], t, pop(t, 0.25, 0.6))
    d = ImageDraw.Draw(img)
    # price + was/save
    if mode == "reel":
        price_block(img, int(215*u), int(1235*u), 150*u, info, t, pop(t, 1.6, 0.5)); was_save(img, 420*u, 1170*u, u, info, pop(t, 1.9))
        cy0 = 1360*u; ch = 92*u; gap = 22*u
        for n, f in enumerate(info["feats"][:3]):
            chip(img, 70*u, cy0+n*(ch+gap), 940*u, ch, f, CHIP_COLORS[n % 4], slide(t, 2.6+0.8*n, 0.5))
        # CTA pulse
        ck = slide(t, max(4.8, dur-6), 0.4)
        if ck > 0.02:
            p = 1+0.03*math.sin(t*6); cw, chh = 820*u*p, 82*u; cy = 1738*u
            d = ImageDraw.Draw(img); d.rounded_rectangle((W/2-cw/2, cy-chh/2, W/2+cw/2, cy+chh/2), chh/2, fill=RED, outline=YEL, width=max(3, int(5*u)))
            text_c(d, (W/2, cy), info["cta"], 42*u, WHITE)
    else:
        price_block(img, int(205*u), int(H-foot_h-165*u), 150*u, info, t, pop(t, 0.8, 0.5)); was_save(img, 70*u, H-foot_h-470*u, u, info, pop(t, 1.0))
        ch = 78*u; gap = 16*u; n_f = len(info["feats"][:3]); base_y = H-foot_h-26*u-n_f*(ch+gap)+gap
        for n, f in enumerate(info["feats"][:3]):
            chip(img, 380*u, base_y+n*(ch+gap), 660*u, ch, f, CHIP_COLORS[n % 4], 1)
    # footer
    d = ImageDraw.Draw(img); fy = H-foot_h
    d.rectangle((0, fy, W, H), fill=BLACK)
    text_c(d, (30*u, fy+34*u), "Colour/finish may vary slightly. Image for illustration only.", 19*u, (200, 200, 205), anchor="lm")
    gx, gy = 52*u, fy+82*u
    d.ellipse((gx-17*u, gy-17*u, gx+17*u, gy+17*u), outline=WHITE, width=max(2, int(3*u))); d.line((gx-17*u, gy, gx+17*u, gy), fill=WHITE, width=max(1, int(2*u)))
    d.ellipse((gx-7*u, gy-17*u, gx+7*u, gy+17*u), outline=WHITE, width=max(1, int(2*u)))
    text_c(d, (gx+30*u, gy), info.get("site", "www.vinzapstore.in"), 34*u, WHITE, anchor="lm")
    d.polygon([(W-440*u, fy), (W, fy), (W, H), (W-490*u, H)], fill=YEL)
    text_c(d, (W-235*u, fy+foot_h/2), "VINZAP STORE", 44*u, BLUE)
    return img
