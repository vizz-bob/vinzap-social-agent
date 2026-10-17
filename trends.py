"""Trends: live Google Trends India (RSS) + built-in festival packs (dates for 2026)."""
import urllib.request, xml.etree.ElementTree as ET, datetime, json, os

FESTIVALS = {  # 2026 dates (verify yearly)
 "navratri": dict(start="2026-10-11", end="2026-10-19", note="Ashtami 18 Oct, Navami 19 Oct"),
 "dussehra": dict(start="2026-10-20", end="2026-10-20", note="Vijayadashami"),
 "diwali":   dict(start="2026-11-08", end="2026-11-08", note="Lakshmi Puja expected 8 Nov 2026 - confirm on a calendar"),
}
HASHTAGS = {
 "navratri": "#navratri #navratri2026 #garba #dandiya #durgapuja #jaimatadi #festivevibes",
 "dussehra": "#dussehra #vijayadashami #dussehra2026 #ravandahan #jayshriram #festival",
 "diwali":   "#diwali #diwali2026 #happydiwali #diya #rangoli #festivalofLights #shubhdiwali",
}
# ready-made post ideas (hook, main text, sub, cta, caption)
PACK = {
 "navratri": [
  dict(hook="Happy Navratri!", main="नवरात्रि की हार्दिक शुभकामनाएं", sub="9 nights. 9 forms of Maa Durga.", cta="Share with your family 🙏"),
  dict(hook="9 Colours of Navratri", main="Which colour are you wearing today?", sub="Comment your colour 👇", cta="Follow for daily Navratri posts"),
  dict(hook="Garba Night Vibes", main="Dandiya + Garba + Friends", sub="Tag your Garba partner!", cta="Share this Reel"),
  dict(hook="Maha Ashtami", main="माँ दुर्गा आपके घर सुख-शांति लाएं", sub="Durga Ashtami wishes", cta="Send to someone special"),
  dict(hook="Maha Navami", main="जय माता दी 🙏", sub="Navami wishes to you & family", cta="Share & follow"),
 ],
 "dussehra": [
  dict(hook="Happy Dussehra!", main="बुराई पर अच्छाई की जीत", sub="Victory of good over evil", cta="Share the wishes 🏹"),
  dict(hook="Vijayadashami 2026", main="विजयादशमी की शुभकामनाएं", sub="May you win every battle", cta="Send to your family"),
  dict(hook="Burn the Ravan Within", main="Anger. Ego. Greed. Let them go.", sub="This Dussehra, burn one bad habit", cta="Comment your habit 👇"),
  dict(hook="Jai Shri Ram", main="सत्य की सदा जीत होती है", sub="Dussehra special", cta="Share & follow"),
 ],
 "diwali": [
  dict(hook="Happy Diwali!", main="दीपावली की हार्दिक शुभकामनाएं", sub="Light up your home & heart", cta="Share with loved ones 🪔"),
  dict(hook="Diwali Countdown", main="Cleaning. Lights. Sweets. Ready?", sub="What's on your list?", cta="Comment READY"),
  dict(hook="Diwali Decor Under Rs 500", main="Budget ideas that look premium", sub="Save for later", cta="Follow for more ideas"),
  dict(hook="5 Diwali Gift Ideas", main="Gifts under Rs 499", sub="Your family will love these", cta="Save this Reel"),
  dict(hook="Shubh Dhanteras", main="धनतेरस की शुभकामनाएं", sub="Wealth, health & happiness", cta="Share the wishes"),
 ],
}
OFFERS = {  # home-kitchen festival offers: edit prices/discounts to match your store
 "dussehra": [
  dict(hook="Dussehra Kitchen Sale!", main="Home kitchen essentials from Rs 99", sub="Festival offers on 100+ items", offer="DUSSEHRA OFFER  |  Extra 10% OFF", cta="Order at vinzapstore.in"),
  dict(hook="Dussehra Offer", main="Kitchen gadgets under Rs 299", sub="Limited time festival deal", offer="Shop now  |  Free gift ideas", cta="Comment LINK for the product"),
 ],
 "diwali": [
  dict(hook="Diwali Kitchen Sale!", main="Clean. Organise. Gift. From Rs 99", sub="Get your kitchen Diwali-ready", offer="DIWALI OFFER  |  Up to 30% OFF", cta="Order at vinzapstore.in"),
  dict(hook="Diwali Gift Ideas", main="Useful kitchen gifts under Rs 499", sub="Gift something people actually use", offer="DIWALI SPECIAL  |  Combo deals", cta="Comment LINK for the product"),
  dict(hook="Diwali Cleaning Hacks", main="Spray, scrub & sparkle for Rs 99", sub="Pre-Diwali cleaning must-haves", offer="DIWALI OFFER  |  Limited stock", cta="Comment LINK"),
 ],
}
IMAGE_SOURCES = {  # free, license-friendly places for festival photos/images (you download manually)
 "Pexels": "https://www.pexels.com/search/{q}/", "Pixabay": "https://pixabay.com/images/search/{q}/",
 "Unsplash": "https://unsplash.com/s/photos/{q}", "Canva (templates)": "https://www.canva.com/search/templates?q={q}",
}

def live_trends(geo="IN", n=15):
    try:
        req = urllib.request.Request(f"https://trends.google.com/trending/rss?geo={geo}", headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=15).read())
        ns = {"ht": "https://trends.google.com/trending/rss"}
        out = []
        for it in root.iter("item"):
            news = it.find("ht:news_item/ht:news_item_title", ns)
            out.append(dict(term=it.findtext("title"), traffic=it.findtext("ht:approx_traffic", namespaces=ns),
                            news=(news.text if news is not None else "")))
        return out[:n]
    except Exception as e:
        return [dict(term="(could not load live trends: %s)" % e, traffic="", news="")]

def festival_status(today=None):
    today = today or datetime.date.today(); res = []
    for k, v in FESTIVALS.items():
        s = datetime.date.fromisoformat(v["start"]); e = datetime.date.fromisoformat(v["end"])
        if today < s: st = f"in {(s-today).days} days"
        elif today <= e: st = "HAPPENING NOW"
        else: st = "finished"
        res.append(dict(festival=k, start=v["start"], end=v["end"], status=st, note=v["note"], hashtags=HASHTAGS[k],
                        photo_search={n: u.format(q=k+"+india") for n, u in IMAGE_SOURCES.items()}))
    return res

def suggestions(today=None):
    """festival ideas ordered by relevance (current/next first) + live search trends."""
    st = festival_status(today); order = [x["festival"] for x in sorted(
        st, key=lambda x: (x["status"] == "finished", 0 if x["status"] == "HAPPENING NOW" else 1))]
    kt = " #homekitchen #kitchengadgets #vinzapstore #festivesale"
    offers = [dict(festival=f, hashtags=HASHTAGS[f]+kt, theme="product", **p) for f in ("dussehra","diwali") for p in OFFERS[f]]
    ideas = offers + [dict(festival=f, hashtags=HASHTAGS[f], **p) for f in order for p in PACK[f]]
    return dict(festivals=st, ideas=ideas, live=live_trends())

if __name__ == "__main__":
    print(json.dumps(suggestions(), indent=1, ensure_ascii=False)[:1500])
