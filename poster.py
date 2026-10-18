"""Posting connectors. Tokens live ONLY in config.json on your computer.
Instagram + Facebook: Meta Graph API.  YouTube: Data API v3 (OAuth refresh token).
DRY_RUN (default) logs what would be posted and does not call any API."""
import os, json, time, urllib.request, urllib.parse, urllib.error, uuid

GV = "v26.0"

def _req(url, data=None, headers=None, method=None, timeout=300):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f: raw = f.read(); hdr = f.headers
    except urllib.error.HTTPError as e:
        raise RuntimeError("HTTP %s: %s" % (e.code, e.read().decode("utf8", "ignore")[:600]))
    try: return json.loads(raw or b"{}")
    except Exception: return {"raw": raw.decode("utf8", "ignore"), "headers": dict(hdr)}

def _form(url, **kw): return _req(url, urllib.parse.urlencode(kw).encode(), {"Content-Type": "application/x-www-form-urlencoded"}, "POST")
def _get(url, **kw): return _req(url + "?" + urllib.parse.urlencode(kw))

# ---------- Instagram (Reels / Stories) ----------
def instagram(cfg, video, caption, kind="reel"):
    ig, tok = cfg["instagram_user_id"], cfg["meta_access_token"]
    mt = "STORIES" if kind == "story" else "REELS"
    p = dict(media_type=mt, upload_type="resumable", access_token=tok)
    if mt == "REELS": p["caption"] = caption; p["share_to_feed"] = "true"
    c = _form(f"https://graph.facebook.com/{GV}/{ig}/media", **p)
    cid, uri = c["id"], c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GV}/{c['id']}"
    data = open(video, "rb").read()
    _req(uri, data, {"Authorization": "OAuth " + tok, "offset": "0", "file_size": str(len(data))}, "POST")
    for _ in range(60):  # wait for processing
        st = _get(f"https://graph.facebook.com/{GV}/{cid}", fields="status_code", access_token=tok).get("status_code")
        if st == "FINISHED": break
        if st == "ERROR": raise RuntimeError("Instagram processing error")
        time.sleep(5)
    pub = _form(f"https://graph.facebook.com/{GV}/{ig}/media_publish", creation_id=cid, access_token=tok)
    return pub["id"]

# ---------- Facebook Page video ----------
def facebook(cfg, video, caption, kind="reel"):
    page, tok = cfg["facebook_page_id"], cfg["facebook_page_token"]
    b = uuid.uuid4().hex; data = open(video, "rb").read(); body = b""
    for k, v in (("description", caption), ("access_token", tok)):
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += (f'--{b}\r\nContent-Disposition: form-data; name="source"; filename="v.mp4"\r\nContent-Type: video/mp4\r\n\r\n').encode() + data + f"\r\n--{b}--\r\n".encode()
    return _req(f"https://graph-video.facebook.com/{GV}/{page}/videos", body, {"Content-Type": "multipart/form-data; boundary=" + b}, "POST")["id"]

# ---------- YouTube Shorts ----------
def _yt_token(cfg):
    return _form("https://oauth2.googleapis.com/token", client_id=cfg["youtube_client_id"], client_secret=cfg["youtube_client_secret"],
                 refresh_token=cfg["youtube_refresh_token"], grant_type="refresh_token")["access_token"]

def youtube(cfg, video, caption, kind="reel", title="Shorts"):
    tok = _yt_token(cfg)
    meta = {"snippet": {"title": (title[:90] + " #Shorts")[:100], "description": caption + "\n#Shorts", "categoryId": "22"},
            "status": {"privacyStatus": cfg.get("youtube_privacy", "public"), "selfDeclaredMadeForKids": False}}
    data = open(video, "rb").read()
    r = urllib.request.Request("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        json.dumps(meta).encode(), {"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))}, method="POST")
    loc = urllib.request.urlopen(r, timeout=60).headers["Location"]
    return _req(loc, data, {"Content-Type": "video/mp4", "Authorization": "Bearer " + tok}, "PUT")["id"]

def _multipart(url, fields, fname, data, ctype):
    b = uuid.uuid4().hex; body = b""
    for k, v in fields.items(): body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += f'--{b}\r\nContent-Disposition: form-data; name="source"; filename="{fname}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + data + f"\r\n--{b}--\r\n".encode()
    return _req(url, body, {"Content-Type": "multipart/form-data; boundary=" + b}, "POST")

def facebook_photo(cfg, image, caption, kind="image", title=""):
    r = _multipart(f"https://graph.facebook.com/{GV}/{cfg['facebook_page_id']}/photos", dict(caption=caption, access_token=cfg["facebook_page_token"]),
                   "poster.jpg", open(image, "rb").read(), "image/jpeg")
    return r.get("post_id") or r["id"]

def instagram_photo(cfg, image, caption, kind="image", title=""):
    """Instagram needs a public image URL: upload it unpublished to your linked Facebook Page, use that URL."""
    pg = _multipart(f"https://graph.facebook.com/{GV}/{cfg['facebook_page_id']}/photos", dict(published="false", access_token=cfg["facebook_page_token"]),
                    "poster.jpg", open(image, "rb").read(), "image/jpeg")["id"]
    url = _get(f"https://graph.facebook.com/{GV}/{pg}", fields="images", access_token=cfg["facebook_page_token"])["images"][0]["source"]
    c = _form(f"https://graph.facebook.com/{GV}/{cfg['instagram_user_id']}/media", image_url=url, caption=caption, access_token=cfg["meta_access_token"])
    for _ in range(30):
        st = _get(f"https://graph.facebook.com/{GV}/{c['id']}", fields="status_code", access_token=cfg["meta_access_token"]).get("status_code")
        if st in ("FINISHED", None): break
        if st == "ERROR": raise RuntimeError("Instagram image processing error")
        time.sleep(3)
    return _form(f"https://graph.facebook.com/{GV}/{cfg['instagram_user_id']}/media_publish", creation_id=c["id"], access_token=cfg["meta_access_token"])["id"]

def facebook_story(cfg, video):
    """Facebook Page video Story (keeps the sound of the video)"""
    page, tok = cfg["facebook_page_id"], cfg["facebook_page_token"]
    s = _form(f"https://graph.facebook.com/{GV}/{page}/video_stories", upload_phase="start", access_token=tok)
    data = open(video, "rb").read()
    _req(s["upload_url"], data, {"Authorization": "OAuth " + tok, "offset": "0", "file_size": str(len(data))}, "POST")
    r = _form(f"https://graph.facebook.com/{GV}/{page}/video_stories", upload_phase="finish", video_id=s["video_id"], access_token=tok)
    return r.get("post_id") or s["video_id"]

def story(cfg, plat, video):
    if plat == "instagram": return instagram(cfg, video, "", "story")
    if plat == "facebook": return facebook_story(cfg, video)
    raise RuntimeError("no stories on " + plat)

PLATFORMS = {"instagram": instagram, "facebook": facebook, "youtube": youtube}
NEEDS = {"instagram": ("instagram_user_id", "meta_access_token"), "facebook": ("facebook_page_id", "facebook_page_token"),
         "youtube": ("youtube_client_id", "youtube_client_secret", "youtube_refresh_token")}

def configured(cfg, plat): return all(cfg.get(k) and not str(cfg[k]).startswith("PASTE") for k in NEEDS[plat])

def post(cfg, plat, video, caption, kind, title, dry):
    if dry: return "DRY-RUN (not posted): %s %s %s" % (plat, kind, os.path.basename(video))
    if not configured(cfg, plat): raise RuntimeError("missing keys for %s in config.json" % plat)
    if kind == "image":
        if plat == "youtube": raise RuntimeError("YouTube takes videos only")
        return (instagram_photo if plat == "instagram" else facebook_photo)(cfg, video, caption, kind, title)
    f = PLATFORMS[plat]
    return f(cfg, video, caption, kind, title) if plat == "youtube" else f(cfg, video, caption, kind)


def all_targets(cfg):
    """target key -> (platform, merged cfg). One target per account+platform; one for YouTube."""
    t = {}
    accts = cfg.get("accounts")
    if accts:
        for a in accts:
            m = dict(cfg); m.update(a)
            if a.get("instagram_user_id"): t["instagram@" + a["name"]] = ("instagram", m)
            if a.get("facebook_page_id"): t["facebook@" + a["name"]] = ("facebook", m)
    else:
        t["instagram"] = ("instagram", cfg); t["facebook"] = ("facebook", cfg)
    t["youtube"] = ("youtube", cfg)
    return t
