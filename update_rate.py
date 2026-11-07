"""Updates data/rates.json with Kerala 22K rate (Rs/gm, excl. GST) from Goodreturns.
The page lists the last 10 days, so each run also back-fills any missed days.
Fails loudly (non-zero exit) if the page layout changes, so the bot never saves junk."""
import json, re, html, sys, datetime, pathlib, urllib.request

URL = "https://www.goodreturns.in/gold-rates/kerala.html"
FILE = pathlib.Path(__file__).resolve().parent.parent / "data" / "rates.json"

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                                           "Accept-Language": "en-IN,en;q=0.9"})
raw = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))

# Rows look like: "Nov 07, 2026 ₹14,357 (+11) ₹13,160 (+10)"  -> 24K first, 22K second
rows = re.findall(r"([A-Z][a-z]{2} \d{1,2}, \d{4}) ₹ ?([\d,]+)[^₹]{0,30}?₹ ?([\d,]+)", text)
found = {}
for d, k24, k22 in rows:
    iso = datetime.datetime.strptime(d, "%b %d, %Y").date().isoformat()
    r22, r24 = int(k22.replace(",", "")), int(k24.replace(",", ""))
    if 5000 < r22 < 100000 and 0.88 < r22 / r24 < 0.95:   # 22K should be ~91.6% of 24K
        found[iso] = r22
if len(found) < 2:
    sys.exit("Could not parse rates - page layout changed. Update scripts/update_rate.py")

data = {d["date"]: d["rate22"] for d in json.loads(FILE.read_text())}
data.update(found)
FILE.write_text(json.dumps([{"date": k, "rate22": v} for k, v in sorted(data.items())], indent=1))
print("Saved", len(found), "days; latest:", max(found), found[max(found)])
