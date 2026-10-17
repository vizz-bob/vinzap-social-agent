"""Reads products from your Shopify store's public feed (https://<store>/products.json)
and turns each into everything a poster/reel needs (name, price, features, hashtags)."""
import json, re, html, urllib.request, os

def fetch(store="https://www.vinzapstore.in", limit=250):
    out, page = [], 1
    while len(out) < limit:
        req = urllib.request.Request(f"{store}/products.json?limit=250&page={page}", headers={"User-Agent": "Mozilla/5.0"})
        data = json.load(urllib.request.urlopen(req, timeout=30)).get("products", [])
        if not data: break
        for p in data:
            if not p.get("images"): continue
            vs = p.get("variants") or []
            price = min(float(v["price"]) for v in vs) if vs else 0
            cmp_ = max((float(v["compare_at_price"]) for v in vs if v.get("compare_at_price")), default=0)
            out.append(dict(handle=p["handle"], title=p["title"], price=int(price) if price == int(price) else price,
                            compare_at=int(cmp_) if cmp_ > price else 0, type=p.get("product_type", ""),
                            tags=p.get("tags", []) if isinstance(p.get("tags"), list) else [t.strip() for t in p.get("tags", "").split(",")],
                            images=[i["src"] for i in p["images"][:4]], body=p.get("body_html") or "",
                            url=f"{store}/products/{p['handle']}"))
        page += 1
        if len(data) < 250: break
    return out[:limit]

HOME_KITCHEN = ("Home & Kitchen", "Kitchen Combos", "Custom Print Drinkware")
def home_kitchen(prods, types=None):
    """keep only kitchen / home products (by the store's own product type); never returns an empty list"""
    types = tuple(types or HOME_KITCHEN)
    return [p for p in prods if p.get("type") in types] or prods

def clean(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def short_name(title, n=44):
    t = title.split(":")[0]
    t = re.split(r"\s+(?:for|with|-|\|)\s+", t, maxsplit=1)[0]
    t = re.sub(r"\b\d+\s?(pcs?|pieces?|set)\b", "", t, flags=re.I).strip(" -,:")
    if len(t) < 4 or len(t) > n: t = title[:n].rsplit(" ", 1)[0]
    return t

_STOP = {"for", "and", "with", "of", "to", "in", "the", "a", "an", "or", "on", "at", "by"}
def _cut(s, n):
    if len(s) <= n: return s
    w = s[:n].rsplit(" ", 1)[0].split()
    while w and w[-1].lower() in _STOP: w.pop()
    return " ".join(w)

def features(p, k=3, maxlen=34):
    items = [clean(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", p["body"], flags=re.S | re.I)]
    out = []
    for it in items:
        it = re.sub(r"^(material|capacity|size|colou?r|pack|includes?)\s*:\s*", lambda m: m.group(1).capitalize() + ": ", it, flags=re.I)
        it = it.split(",")[0].strip()
        it = _cut(it, maxlen)
        if len(it) > 3: out.append(it)
        if len(out) == k: break
    if not out:
        first = clean(p["body"]).split(". ")[0]
        out = [_cut(first, maxlen)] if first else ["Everyday home essential"]
    return out

_TAGS = [("kitchen", "#kitchengadgets #kitchenessentials"), ("combo", "#combooffer #valuedeals"), ("storage", "#storageideas #organizer"),
         ("clean", "#cleaninghacks #homecleaning"), ("bottle", "#bottle #homeessentials"), ("mug", "#mug #giftideas"),
         ("pet", "#petlovers #petessentials"), ("lunch", "#lunchbox #tiffin"), ("bath", "#bathroomaccessories"), ("gift", "#giftideas #festivegifts")]
def hashtags(p):
    text = (p["title"] + " " + p["type"] + " " + " ".join(p["tags"])).lower(); out = ["#homekitchen", "#vinzapstore"]
    for k, v in _TAGS:
        if k in text: out += v.split()
    return " ".join(dict.fromkeys(out))[:200]

def download(urls, dest_dir, prefix):
    paths = []
    for n, u in enumerate(urls):
        fn = f"{prefix}_{n}.jpg"; fp = os.path.join(dest_dir, fn)
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            open(fp, "wb").write(urllib.request.urlopen(req, timeout=30).read()); paths.append(fn)
        except Exception: pass
    return paths
