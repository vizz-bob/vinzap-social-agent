"""Pulls real numbers for posted items + simple recommendations."""
import poster as P

def fetch(cfg, plat, post_id):
    try:
        if plat == "instagram":
            d = P._get(f"https://graph.facebook.com/{P.GV}/{post_id}/insights", metric="views,reach,likes,comments,saved,shares", access_token=cfg["meta_access_token"])
            return {m["name"]: m["values"][0]["value"] for m in d.get("data", [])}
        if plat == "youtube":
            d = P._get("https://www.googleapis.com/youtube/v3/videos", part="statistics", id=post_id, access_token=P._yt_token(cfg))
            s = d["items"][0]["statistics"]; return {"views": s.get("viewCount"), "likes": s.get("likeCount"), "comments": s.get("commentCount")}
        if plat == "facebook":
            d = P._get(f"https://graph.facebook.com/{P.GV}/{post_id}", fields="views,likes.summary(true),comments.summary(true)", access_token=cfg["facebook_page_token"])
            return {"views": d.get("views"), "likes": d.get("likes", {}).get("summary", {}).get("total_count"), "comments": d.get("comments", {}).get("summary", {}).get("total_count")}
    except Exception as e:
        return {"error": str(e)[:200]}
    return {}

def advise(rows):
    """rows: [{theme, plat, stats}] -> tips"""
    tips, by = [], {}
    for r in rows:
        v = r["stats"].get("views")
        try: v = int(v)
        except Exception: continue
        by.setdefault(r["theme"], []).append(v)
    if not by: return ["No numbers yet. Post items with real keys (dry-run has no stats)."]
    avg = {k: sum(v)/len(v) for k, v in by.items()}; best = max(avg, key=avg.get)
    tips.append("Best theme so far: %s (avg %.0f views). Make more like it." % (best, avg[best]))
    if max(avg.values()) < 50: tips.append("All low: add a real photo/clip in the first 2s, ask for a comment, post at 7-9pm, 1 Reel/day.")
    return tips
