
"""
Updates data/rates.json with Kerala 22K gold rate (Rs/gm, excl. GST)
from Goodreturns.

Backfills available historical dates.
Fails loudly if the source data is missing, stale, malformed or suspicious.
"""

import json
import re
import html
import sys
import datetime
import pathlib
import urllib.request
import os
from zoneinfo import ZoneInfo

URL = "https://www.goodreturns.in/gold-rates/kerala.html"
FILE = pathlib.Path(__file__).resolve().parent.parent / "data" / "rates.json"

TODAY = datetime.datetime.now(
    ZoneInfo("Asia/Kolkata")
).date()

# Fetch source page
req = urllib.request.Request(
    URL,
    headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
        "Cache-Control": "no-cache"
    }
)

try:
    with urllib.request.urlopen(req, timeout=40) as response:
        if response.status != 200:
            sys.exit(f"Source returned HTTP {response.status}")

        raw = response.read().decode("utf-8", "ignore")

except Exception as e:
    sys.exit(f"Could not fetch Goodreturns page: {e}")


# Extract individual HTML table rows.
# This prevents accidentally matching prices from different rows.
rows = re.findall(
    r"<tr\b[^>]*>(.*?)</tr>",
    raw,
    flags=re.IGNORECASE | re.DOTALL
)

found = {}

for row in rows:
    text = html.unescape(
        re.sub(r"<[^>]+>", " ", row)
    )
    text = re.sub(r"\s+", " ", text).strip()

    dates = re.findall(
        r"\b([A-Z][a-z]{2} \d{1,2}, \d{4})\b",
        text
    )

    prices = re.findall(
        r"₹\s*([\d,]+)",
        text
    )

    if not dates or len(prices) < 2:
        continue

    try:
        parsed_date = datetime.datetime.strptime(
            dates[0], "%b %d, %Y"
        ).date()

        iso = parsed_date.isoformat()

        r24 = int(prices[0].replace(",", ""))
        r22 = int(prices[1].replace(",", ""))

    except (ValueError, IndexError):
        continue

    # Reject future records
    if parsed_date > TODAY:
        continue

    # Reject implausible prices
    if not (5000 < r22 < 100000):
        continue

    if not (5000 < r24 < 110000):
        continue

    # 22K should be approximately 91.6% of 24K
    ratio = r22 / r24

    if not (0.88 < ratio < 0.95):
        continue

    # Conflicting duplicate records are suspicious
    if iso in found and found[iso] != r22:
        sys.exit(f"Conflicting source rates for {iso}")

    found[iso] = r22


if len(found) < 2:
    sys.exit(
        "Could not verify at least two daily rates. "
        "Goodreturns page layout may have changed."
    )


# Check freshness
latest_date = max(
    datetime.date.fromisoformat(d) for d in found
)

age = (TODAY - latest_date).days

if age < 0 or age > 3:
    sys.exit(
        f"Source data is stale. Latest date: {latest_date}; "
        f"today: {TODAY}"
    )


# Load and validate existing history
if FILE.exists():
    try:
        existing = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"Existing rates.json is invalid: {e}")
else:
    existing = []

if not isinstance(existing, list):
    sys.exit("Existing rates.json must contain a list")

data = {}

for item in existing:
    if not isinstance(item, dict):
        sys.exit("Invalid existing rate record")

    d = item.get("date")
    r = item.get("rate22")

    try:
        parsed = datetime.date.fromisoformat(d)
        if parsed.isoformat() != d:
            raise ValueError()
    except (ValueError, TypeError):
        sys.exit(f"Invalid existing date: {d}")

    if isinstance(r, bool) or not isinstance(r, (int, float)) or not (5000 < r < 100000):
        sys.exit(f"Invalid existing rate for {d}")

    data[d] = r


# Update history with verified source records
data.update(found)

result = [
    {"date": d, "rate22": data[d]}
    for d in sorted(data)
]

# Atomic write: replace file only after successful serialization
tmp = FILE.with_suffix(".json.tmp")

try:
    tmp.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8"
    )
    os.replace(tmp, FILE)

except Exception as e:
    if tmp.exists():
        tmp.unlink()
    sys.exit(f"Could not save rate history: {e}")


print("Rate update successful")
print("New source records:", len(found))
print("Latest source date:", latest_date)
print("Latest 22K rate:", found[max(found)])
print("Total history records:", len(result))
