"""Appends today's Kerala 22Ct rate to data/rates.json.
EDIT SOURCE_URL and parse() for the site you choose (ideally one that republishes
the AKGSMA Kerala rate). Always check the site's terms before scraping."""
import json, re, datetime, pathlib, urllib.request

SOURCE_URL = "https://REPLACE-WITH-A-KERALA-GOLD-RATE-PAGE"
FILE = pathlib.Path(__file__).parent.parent / "data" / "rates.json"

def parse(html: str) -> float:
    # Example only: find the first number after "22" near "1 gm"/"1 Gram". Adjust to the site's HTML.
    m = re.search(r"22\s*(?:K|Ct|Carat)[^₹]{0,200}₹\s*([\d,]+(?:\.\d+)?)", html, re.I | re.S)
    if not m: raise ValueError("rate not found - fix parse()")
    return float(m.group(1).replace(",", ""))

req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
rate = parse(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore"))
today = datetime.date.today().isoformat()
data = json.loads(FILE.read_text())
data = [d for d in data if d["date"] != today] + [{"date": today, "rate22": rate}]
FILE.write_text(json.dumps(sorted(data, key=lambda d: d["date"]), indent=1))
print(today, rate)
