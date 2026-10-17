#!/usr/bin/env python3
"""One scheduled run: if a post is due, pick the next store product, design ONE Reel or poster, post it to every due account.
Reels and posters alternate. Reels go to Instagram, Facebook (both Pages) and YouTube; posters go to Instagram and Facebook."""
import os, sys, json, time, uuid, random, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import agent, poster, products

agent.Q_FILE = os.path.join(HERE, "state", "queue.json")
os.makedirs(os.path.dirname(agent.Q_FILE), exist_ok=True)
SLACK = 420   # GitHub may start runs a few minutes late; allow 7 minutes of slack on the interval

def main():
    c = agent.cfg(); now = time.time(); hr = datetime.datetime.now().hour
    if not (c["start_hour"] <= hr < c["end_hour"]): print(f"hour {hr} is outside {c['start_hour']}-{c['end_hour']}, nothing to do"); return
    q = agent.load(); last = q.setdefault("last", {}); tg = poster.all_targets(c)
    due = []
    for k, (pl, m) in tg.items():
        if not c["dry_run"] and not poster.configured(m, pl): continue
        if now - last.get(k, 0) < c["interval_minutes"] * 60 - SLACK: continue
        if agent.posted_today(q, k) >= c["daily_cap_per_platform"]: continue
        due.append(k)
    if not due: print("nothing due"); return
    kind = "reel" if q.get("n", 0) % 2 == 0 else "image"
    if kind == "image" and all(tg[k][0] == "youtube" for k in due): kind = "reel"   # YouTube takes videos only
    plats = ["instagram", "facebook", "youtube"] if kind == "reel" else ["instagram", "facebook"]
    if not any(tg[k][0] in plats for k in due): kind, plats = "reel", ["instagram", "facebook", "youtube"]

    prods = products.home_kitchen(products.fetch(c["store_url"]), c.get("product_types"))
    used = {i.get("handle") for i in q["items"] if i.get("handle")}
    fresh = [p for p in prods if p["handle"] not in used] or prods
    random.shuffle(fresh); p = None; item = None
    for cand in fresh[:5]:
        try:
            info = agent.build_info(cand, c); iid0 = uuid.uuid4().hex[:8]
            photos = products.download(cand["images"], agent.UP, iid0)
            if not photos: raise RuntimeError("no photos")
            p = cand; break
        except Exception as e: print("skip product", cand["handle"], e)
    if not p: print("no usable product"); sys.exit(1)
    iid = uuid.uuid4().hex[:8]
    item = dict(id=iid, status="generating", kind=kind, style="sale", info=info, spec=dict(theme="product", hook=info["headline"]), photos=photos,
                caption=agent.caption_for(p, info), title=info["headline"], platforms=plats, posted={}, created=now, after=0,
                handle=p["handle"], product_url=p["url"])
    q["items"].append(item); q["n"] = q.get("n", 0) + 1; agent.save(q)
    agent.generate(iid)                       # renders now and waits until the file is finished
    q = agent.load(); it = next(i for i in q["items"] if i["id"] == iid)
    if it["status"] != "scheduled": print("render failed:", it.get("error")); agent.save(q); sys.exit(1)
    for k in due: q["last"][k] = q["last"].get(k, 0) - SLACK     # so tick() accepts targets that are within the slack window
    agent.save(q)
    agent.tick()                              # posts the new item to every due account
    q = agent.load()
    q["items"] = q["items"][-80:]             # keep the history small
    for i in q["items"]: i.pop("photos", None)
    agent.save(q)
    for line in q["log"][-8:]: print(line)

if __name__ == "__main__":
    main()
