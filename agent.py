#!/usr/bin/env python3
"""Social Agent: create Reels/Stories/Shorts, review them, auto-post on a timer, see trends + insights.
Run:  python3 agent.py   then open http://localhost:8765"""
import os, sys, json, time, threading, base64, datetime, traceback, uuid, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import studio, trends, poster, insights, products

OUT = os.path.join(HERE, "output"); UP = os.path.join(HERE, "uploads")
for d in (OUT, UP): os.makedirs(d, exist_ok=True)
CFG_FILE = os.path.join(HERE, "config.json"); Q_FILE = os.path.join(HERE, "queue.json")
LOCK = threading.RLock()
DEFAULTS = dict(dry_run=True, interval_minutes=60, daily_cap_per_platform=10, auto_approve=False, port=8765, start_hour=8, end_hour=23,
    store_url="https://www.vinzapstore.in", offer_text="FESTIVE OFFER  |  Order now", auto_refill=False,
    autopilot=True, festival_discount_percent=0)

def cfg():
    c = dict(DEFAULTS)
    if os.path.exists(CFG_FILE): c.update(json.load(open(CFG_FILE)))
    if c["autopilot"]: c["auto_approve"] = True; c["auto_refill"] = True   # autopilot = no clicking needed
    return c
def load():
    return json.load(open(Q_FILE)) if os.path.exists(Q_FILE) else {"items": [], "last_post": 0, "log": []}
def save(q): json.dump(q, open(Q_FILE, "w"), indent=1, ensure_ascii=False)
def log(q, msg):
    q["log"].append(time.strftime("%H:%M:%S ") + msg); q["log"] = q["log"][-200:]; print(msg, flush=True)

# ---------- generation (async: waits until video is really finished) ----------
RENDER_SEM = threading.Semaphore(2)
def generate(item_id):
    with LOCK: q = load(); it = next(i for i in q["items"] if i["id"] == item_id)
    try:
        with RENDER_SEM:
            photos = [os.path.join(UP, p) for p in it.get("photos", [])]; base = os.path.join(OUT, item_id)
            if it.get("style") == "sale":
                if it["kind"] == "image":
                    studio.poster_sale(it["info"], photos, base + ".jpg"); fn, th = item_id + ".jpg", item_id + ".jpg"
                else:
                    studio.thumb_sale(it["info"], photos, base + "_t.jpg"); studio.render_sale(it["info"], photos, base + ".mp4", 15); fn, th = item_id + ".mp4", item_id + "_t.jpg"
            else:
                spec = it["spec"]; studio.still(spec, base + ".png", photos)
                studio.render(spec, base + ".mp4", 15 if it["kind"] != "story" else 7, photos); fn, th = item_id + ".mp4", item_id + ".png"
        with LOCK:
            q = load(); it = next(i for i in q["items"] if i["id"] == item_id)
            it["status"] = "scheduled" if cfg()["auto_approve"] else "review"; it["file"] = fn; it["thumb"] = th
            log(q, "READY " + item_id + " " + it["title"] + (" (auto-approved)" if cfg()["auto_approve"] else " - waiting for your approval")); save(q)
    except Exception as e:
        with LOCK:
            q = load(); it = next(i for i in q["items"] if i["id"] == item_id); it["status"] = "failed"; it["error"] = str(e)[:300]
            log(q, "FAILED generate " + item_id + ": " + str(e)); save(q)

def new_item(body):
    iid = uuid.uuid4().hex[:8]; photos = []
    for n, b64 in enumerate(body.get("images", [])):
        fn = f"{iid}_{n}.jpg"; open(os.path.join(UP, fn), "wb").write(base64.b64decode(b64.split(",")[-1])); photos.append(fn)
    spec = dict(theme=body.get("theme", "custom"), hook=body["hook"], sub=body.get("sub", ""), main=body.get("main", ""),
                badge=body.get("badge", ""), offer=body.get("offer", ""), cta=body.get("cta", ""))
    it = dict(id=iid, status="generating", kind=body.get("kind", "reel"), spec=spec, photos=photos,
              caption=body.get("caption") or (spec["hook"] + "\n" + spec["main"] + "\n" + body.get("hashtags", "")),
              title=spec["hook"], platforms=body.get("platforms", ["instagram", "facebook", "youtube"]),
              posted={}, created=time.time(), after=body.get("after", 0))
    with LOCK:
        q = load(); q["items"].append(it); save(q)
    threading.Thread(target=generate, args=(iid,), daemon=True).start(); return iid

# ---------- store products (everything is captured automatically) ----------
GREET = {"navratri": "नवरात्रि की हार्दिक शुभकामनाएं 🙏", "dussehra": "दशहरा की हार्दिक शुभकामनाएं 🏹", "diwali": "दीपावली की हार्दिक शुभकामनाएं 🪔"}
def festival_tag():
    for f in trends.festival_status():
        if f["festival"] == "navratri" and f["status"] != "HAPPENING NOW": continue
        if f["status"] == "HAPPENING NOW" or f["status"].startswith("in "): return f["festival"]
    return "diwali"

def build_info(p, c):
    fest = festival_tag(); price, was = p["price"], 0; d = float(c.get("festival_discount_percent") or 0)
    if d > 0: was, price = p["price"], int(round(p["price"]*(1-d/100)))
    elif p.get("compare_at"): was = p["compare_at"]
    name = products.short_name(p["title"]); sale = bool(was); kw = products.trending_keywords(p["handle"])
    strip = f"{fest.capitalize()} {'Sale' if sale else 'Special'}  |  " + (f"Extra {int(d)}% OFF" if d > 0 else "Home & Kitchen")
    return dict(fest=fest, headline=name, strip=strip, price=price, was=was, feats=products.features(p), label2="SALE" if sale else "SPECIAL",
                cta="Comment LINK to order", site=c["store_url"].replace("https://", ""),
                kw=kw, yt_title=(name + " | " + kw[0].title()) if kw else name)

def caption_for(p, info):
    feats = "\n".join("✔ " + f for f in info["feats"])
    price = f"Only ₹{info['price']}" + (f" (was ₹{info['was']})" if info["was"] else "")
    h = trends.HASHTAGS[info["fest"]].split()
    return (f"{GREET[info['fest']]}\n\n{info['headline']}\n{feats}\n\n{price}. Comment LINK and we will send it, "
            f"or order at vinzapstore.in (link in bio).\n\n{h[0]} {h[1]} {products.hashtags(p)}"
            + ("\n" + " ".join("#" + k.replace(" ", "") for k in info.get("kw", [])) if info.get("kw") else ""))

def product_items(p, c):
    """one product -> 1 animated Reel + 1 feed poster, both fully designed from store data"""
    info = build_info(p, c); iid0 = uuid.uuid4().hex[:8]; photos = products.download(p["images"], UP, iid0)
    if not photos: raise RuntimeError("no photos for " + p["handle"])
    ids = []
    for kind, plats in (("reel", ["instagram", "facebook", "youtube"]), ("image", ["instagram", "facebook"])):
        iid = uuid.uuid4().hex[:8]
        it = dict(id=iid, status="generating", kind=kind, style="sale", info=info, spec=dict(theme="product", hook=info["headline"]), photos=photos,
                  caption=caption_for(p, info), title=(info.get("yt_title") if kind == "reel" else info["headline"]), platforms=plats, posted={}, created=time.time(), after=0,
                  handle=p["handle"], product_url=p["url"])
        with LOCK:
            q = load(); q["items"].append(it); save(q)
        threading.Thread(target=generate, args=(iid,), daemon=True).start(); ids.append(iid)
    return ids

def autofill(n):
    c = cfg(); prods = products.home_kitchen(products.fetch(c["store_url"]), c.get("product_types"))
    with LOCK: used = {i.get("handle") for i in load()["items"] if i.get("handle")}
    fresh = [p for p in prods if p["handle"] not in used]
    if not fresh and prods:   # all products used once: start a new round
        fresh = prods
    import random; random.shuffle(fresh); made = []
    for p in fresh[:n]:
        try: made += product_items(p, c)
        except Exception as e:
            with LOCK: q = load(); log(q, "SKIP product %s: %s" % (p["handle"], e)); save(q)
    return made

def refill_check():
    """autopilot: keep about a day of ready posts in the queue"""
    c = cfg()
    if not c["autopilot"] and not c["auto_refill"]: return
    with LOCK: q = load(); pending = sum(1 for i in q["items"] if i["status"] in ("generating", "review", "scheduled"))
    need = c["daily_cap_per_platform"]*2 - pending
    if need > 0: autofill(max(1, (need+1)//2))

# ---------- scheduler ----------
def posted_today(q, plat):
    t0 = datetime.datetime.now().replace(hour=0, minute=0, second=0).timestamp()
    return sum(1 for i in q["items"] for p, r in i["posted"].items() if p == plat and r.get("ts", 0) >= t0 and r.get("ok"))

def tick():
    c = cfg()
    if not (c["start_hour"] <= datetime.datetime.now().hour < c["end_hour"]): return  # only post in your daytime window
    with LOCK:
        q = load(); last = q.setdefault("last", {}); tg = poster.all_targets(c); now = time.time(); changed = False
        for tkey, (pl, m) in tg.items():
            if not c["dry_run"] and not poster.configured(m, pl): continue   # live mode: skip platforms without keys
            if now - last.get(tkey, 0) < c["interval_minutes"]*60: continue
            if posted_today(q, tkey) >= c["daily_cap_per_platform"]: continue
            for it in q["items"]:
                if it["status"] != "scheduled" or it.get("after", 0) > now or pl not in it["platforms"] or tkey in it["posted"]: continue
                vid = os.path.join(OUT, it["file"])
                try:
                    res = poster.post(m, pl, vid, it["caption"], it["kind"], it["title"], c["dry_run"], os.path.join(OUT, it["thumb"]) if it.get("thumb") and it["kind"] != "image" else None)
                    it["posted"][tkey] = dict(ok=True, ts=now, id=res, dry=c["dry_run"]); log(q, f"POSTED {tkey} {it['id']}: {res}")
                except Exception as e:
                    it["posted"][tkey] = dict(ok=False, ts=now, error=str(e)[:300]); log(q, f"FAILED post {tkey} {it['id']}: {e}")
                last[tkey] = now; q["last_post"] = now; changed = True
                wanted = [k for k, (p2, m2) in tg.items() if p2 in it["platforms"] and (c["dry_run"] or poster.configured(m2, p2))]
                if all(it["posted"].get(k, {}).get("ok") for k in wanted): it["status"] = "posted"
                break
        if changed: save(q)

def loop():
    nxt = time.time() + 5
    while True:
        try:
            tick()
            if time.time() >= nxt: nxt = time.time() + 300; refill_check()
        except Exception: traceback.print_exc()
        time.sleep(15)

# ---------- HTTP ----------
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ct="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        try:
            self.send_response(code); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser closed a video preview early; harmless
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/": return self.send(200, open(os.path.join(HERE, "dashboard.html"), "rb").read(), "text/html; charset=utf-8")
        if p.startswith("/files/"):
            f = os.path.join(OUT, os.path.basename(p))
            if os.path.exists(f):
                data = open(f, "rb").read(); return self.send(200, data, "video/mp4" if f.endswith("mp4") else ("image/jpeg" if f.endswith("jpg") else "image/png"))
            return self.send(404, {})
        if p == "/api/state":
            c = cfg(); q = load()
            return self.send(200, dict(items=q["items"][::-1], log=q["log"][-40:], last_post=q["last_post"], now=time.time(),
                cfg=dict(dry_run=c["dry_run"], interval_minutes=c["interval_minutes"], daily_cap=c["daily_cap_per_platform"], start_hour=c["start_hour"], end_hour=c["end_hour"], auto_approve=c["auto_approve"], offer_text=c["offer_text"], auto_refill=c["auto_refill"], autopilot=c["autopilot"], discount=c["festival_discount_percent"], today={k: posted_today(load(), k) for k in poster.all_targets(c)},
                         connected={k: poster.configured(m, pl) for k, (pl, m) in poster.all_targets(c).items()})))
        if p == "/api/products":
            try: return self.send(200, products.fetch(cfg()["store_url"]))
            except Exception as e: return self.send(200, {"error": str(e)})
        if p == "/api/trends": return self.send(200, trends.suggestions())
        if p == "/api/insights":
            c = cfg(); q = load(); rows = []; tg = poster.all_targets(c)
            for i in q["items"]:
                for pl, r in i["posted"].items():
                    if r.get("ok") and not r.get("dry"):
                        base, m = tg.get(pl, (pl.split("@")[0], c))
                        rows.append(dict(item=i["id"], title=i["title"], theme=i["spec"]["theme"], plat=pl, stats=insights.fetch(m, base, r["id"])))
            return self.send(200, dict(rows=rows, tips=insights.advise(rows)))
        self.send(404, {})
    def do_POST(self):
        p = urlparse(self.path).path; body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if p == "/api/create": return self.send(200, dict(id=new_item(body)))
        if p == "/api/autofill": return self.send(200, dict(made=autofill(int(body.get("n", 5)))))
        if p == "/api/product_post":
            c = cfg(); pr = next((x for x in products.fetch(c["store_url"]) if x["handle"] == body["handle"]), None)
            return self.send(200, dict(id=product_item(pr, c, body.get("kind", "reel")))) if pr else self.send(404, {})
        if p == "/api/settings":
            c = json.load(open(CFG_FILE)) if os.path.exists(CFG_FILE) else {}
            for k in ("dry_run", "interval_minutes", "daily_cap_per_platform", "auto_approve", "start_hour", "end_hour", "offer_text", "auto_refill", "store_url", "autopilot", "festival_discount_percent"):
                if k in body: c[k] = body[k]
            json.dump(c, open(CFG_FILE, "w"), indent=2); return self.send(200, {"ok": 1})
        if p in ("/api/approve", "/api/reject", "/api/retry", "/api/delete"):
            with LOCK:
                q = load(); it = next((i for i in q["items"] if i["id"] == body["id"]), None)
                if not it: return self.send(404, {})
                if p.endswith("approve"): it["status"] = "scheduled"
                elif p.endswith("reject"): it["status"] = "rejected"
                elif p.endswith("retry"): it["status"] = "scheduled"; it["posted"] = {k: v for k, v in it["posted"].items() if v.get("ok")}
                else: q["items"].remove(it)
                save(q)
            return self.send(200, {"ok": 1})
        self.send(404, {})

if __name__ == "__main__":
    if not os.path.exists(CFG_FILE): shutil.copy(os.path.join(HERE, "config.example.json"), CFG_FILE)
    threading.Thread(target=loop, daemon=True).start()
    port = cfg()["port"]; print(f"Social Agent running: http://localhost:{port}  (dry_run={cfg()['dry_run']})")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
