import csv
import datetime
import json
import os
import random
import re
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse


# Paths and endpoints
GARMIN_DIR = Path(r"C:\Users\blyth\Desktop\Engineering\Sky\downloads\garmin").expanduser()
OWUI_ENDPOINT = os.environ.get("SKY_MORNING_POST", "http://127.0.0.1:3000/api/sky/morning")


# ---------------
# Helper utils
# ---------------

def _clip_text(txt: str, n: int = 420) -> str:
    t = re.sub(r"\s+", " ", (txt or "")).strip()
    if len(t) > n:
        return t[:n].rstrip() + "..."
    return t


def _list_csvs(dirpath: Path) -> List[Path]:
    if not dirpath.exists():
        return []
    files = [p for p in dirpath.glob("*.csv") if re.search(r"sleep-.*\.csv", p.name, re.I)]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _sniff_reader(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        head = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(head, delimiters=",;\t")
        except Exception:
            dialect = csv.excel
        rdr = csv.DictReader(f, dialect=dialect)
        cols = rdr.fieldnames or []
        rows = list(rdr)
        return cols, rows


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


SYN = {
    "stage": {"stage", "sleepstage", "state"},
    "duration": {"duration", "seconds", "mins", "minutes"},
    "totalsleep": {"totalsleep", "totalsleeptime", "sleepduration", "sleepminutes", "totalsleepminutes", "duration"},
    "timeinbed": {"timeinbed", "bedtime", "timeinbedminutes", "inbedminutes"},
    "deep": {"deep", "deepsleep", "deepsleepminutes"},
    "rem": {"rem", "remsleep", "remsleepminutes"},
    "light": {"light", "lightsleep", "lightsleepminutes"},
    "awake": {"awake", "awakeminutes"},
    "score": {"score", "sleepscore"},
    "hrv": {"hrv", "averagehrv", "hrvaverage", "avg_hrv"},
}


def _to_minutes(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none", "null"):
        return None
    try:
        # numeric means minutes
        return float(s.replace(",", ""))
    except Exception:
        pass
    # h:mm or h:mm:ss
    if re.match(r"^\d+:\d{2}(:\d{2})?$", s):
        parts = [int(p) for p in s.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 60 + parts[1] + parts[2] / 60.0
    # '7h 1m', '7h', '1m'
    m = re.match(r"(?i)^\s*(?:(\d+)\s*h(?:ours?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?)?)?)?\s*$", s)
    if m and (m.group(1) or m.group(2)):
        h = int(m.group(1) or 0)
        m2 = int(m.group(2) or 0)
        return h * 60 + m2
    # '3600 s'
    if re.match(r"^\d+(\.\d+)?\s*s(ec|econds)?$", s, re.I):
        sec = float(re.sub(r"[^0-9.]+", "", s))
        return sec / 60.0
    return None


def _get_by_syn(row: Dict[str, str], keys: set) -> Optional[float]:
    for k, v in row.items():
        if _norm(k) in {_norm(x) for x in keys}:
            return _to_minutes(v)
    return None


def _parse_latest_metrics() -> Optional[Dict[str, Optional[float]]]:
    files = _list_csvs(GARMIN_DIR)
    if not files:
        return None
    path = files[0]
    cols, rows = _sniff_reader(path)
    out: Dict[str, Optional[float]] = {
        "file": path.name,
        "total_min": None,
        "deep_min": None,
        "rem_min": None,
        "light_min": None,
        "awake_min": None,
        "inbed_min": None,
        "eff": None,
        "score": None,
        "hrv": None,
        "deep_pct": None,
        "rem_pct": None,
        "light_pct": None,
    }

    # Case 1: single-row summary with named columns
    if rows:
        r0 = rows[0]
        tot = _get_by_syn(r0, SYN["totalsleep"])  # minutes
        deep = _get_by_syn(r0, SYN["deep"])
        rem = _get_by_syn(r0, SYN["rem"])
        light = _get_by_syn(r0, SYN["light"])
        awake = _get_by_syn(r0, SYN["awake"]) or 0.0
        inbed = (tot or 0.0) + awake if (tot or 0.0) + awake > 0 else None
        eff = (100.0 * tot / inbed) if (inbed and tot) else None
        score = None
        for k in ("score", "sleepscore"):
            if any(_norm(c) == k for c in cols):
                try:
                    score = float(re.sub(r"[^0-9.]+", "", str(r0.get(next(c for c in cols if _norm(c) == k), ""))))
                except Exception:
                    score = None
                break
        hrv = _get_by_syn(r0, SYN["hrv"])  # assume ms already

        if tot or deep or rem or light:
            out.update(
                {
                    "total_min": tot,
                    "deep_min": deep,
                    "rem_min": rem,
                    "light_min": light,
                    "awake_min": _get_by_syn(r0, SYN["awake"]),
                    "inbed_min": inbed,
                    "eff": eff,
                    "score": score,
                    "hrv": hrv,
                }
            )
            total = (tot or 0.0)
            if total > 0:
                out["deep_pct"] = (100.0 * (deep or 0.0) / total) if deep is not None else None
                out["rem_pct"] = (100.0 * (rem or 0.0) / total) if rem is not None else None
                out["light_pct"] = (100.0 * (light or 0.0) / total) if light is not None else None
            return out

    # Case 2: stage timeline with Stage + Duration columns
    stage_key = next((k for k in cols if _norm(k) in {_norm(x) for x in SYN["stage"]}), None)
    dur_key = next((k for k in cols if _norm(k) in {_norm(x) for x in SYN["duration"]}), None)
    if stage_key and dur_key:
        sums: Dict[str, float] = {"deep": 0.0, "rem": 0.0, "light": 0.0, "awake": 0.0}
        for r in rows:
            stage = _norm(r.get(stage_key, ""))
            dur = _to_minutes(r.get(dur_key)) or 0.0
            if "deep" in stage:
                sums["deep"] += dur
            elif "rem" in stage:
                sums["rem"] += dur
            elif "light" in stage:
                sums["light"] += dur
            elif "awake" in stage or "wake" in stage:
                sums["awake"] += dur
        total = sums["deep"] + sums["rem"] + sums["light"]
        inbed = total + sums["awake"] if (total + sums["awake"]) > 0 else None
        eff = (100.0 * total / inbed) if inbed else None
        out.update(
            {
                "total_min": total,
                "deep_min": sums["deep"],
                "rem_min": sums["rem"],
                "light_min": sums["light"],
                "awake_min": sums["awake"],
                "inbed_min": inbed,
                "eff": eff,
            }
        )
        if total > 0:
            out["deep_pct"] = 100.0 * sums["deep"] / total
            out["rem_pct"] = 100.0 * sums["rem"] / total
            out["light_pct"] = 100.0 * sums["light"] / total
        return out

    # Case 3: key/value two-column CSV
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            head = f.read(2048)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(head, delimiters=",;\t")
            except Exception:
                dialect = csv.excel
            rdr = csv.reader(f, dialect=dialect)
            pairs: List[Tuple[str, str]] = []
            for row in rdr:
                if not row:
                    continue
                key = (row[0] or "").strip()
                val = (row[1] or "").strip() if len(row) > 1 else ""
                if key and val and not key.lower().startswith("sleep score 1 day") and not key.lower().endswith("factors") and not key.lower().startswith("sleep timeline"):
                    pairs.append((key, val))
        if pairs:
            kv = {k: v for k, v in pairs}
            tot = _to_minutes(kv.get("Sleep Duration"))
            deep = _to_minutes(kv.get("Deep Sleep Duration"))
            rem = _to_minutes(kv.get("REM Duration"))
            light = _to_minutes(kv.get("Light Sleep Duration"))
            awake = _to_minutes(kv.get("Awake Time")) or 0.0
            inbed = (tot or 0.0) + awake if (tot or 0.0) + awake > 0 else None
            eff = (100.0 * tot / inbed) if (inbed and tot) else None
            score = None
            if "Sleep Score" in kv:
                try:
                    score = float(re.sub(r"[^0-9.]+", "", kv["Sleep Score"]))
                except Exception:
                    score = None
            hrv = None
            for k in ("Avg Overnight HRV", "Average HRV", "HRV"):
                if k in kv:
                    try:
                        hrv = float(re.sub(r"[^0-9.]+", "", kv[k]))
                    except Exception:
                        hrv = None
                    break
            out.update(
                {
                    "total_min": tot,
                    "deep_min": deep,
                    "rem_min": rem,
                    "light_min": light,
                    "awake_min": _to_minutes(kv.get("Awake Time")),
                    "inbed_min": inbed,
                    "eff": eff,
                    "score": score,
                    "hrv": hrv,
                }
            )
            total = (tot or 0.0)
            if total > 0:
                out["deep_pct"] = (100.0 * (deep or 0.0) / total) if deep is not None else None
                out["rem_pct"] = (100.0 * (rem or 0.0) / total) if rem is not None else None
                out["light_pct"] = (100.0 * (light or 0.0) / total) if light is not None else None
            return out
    except Exception:
        pass
    return out


def _sleep_prose(m: Optional[Dict[str, Optional[float]]]) -> str:
    if not m:
        return "No sleep data found."
    tot = m.get("total_min") or 0
    h = int(tot // 60)
    mins = int(round(tot - h * 60))
    eff = m.get("eff")
    deep_pct = m.get("deep_pct")
    rem_pct = m.get("rem_pct")
    light_pct = m.get("light_pct")
    score = m.get("score")
    hrv = m.get("hrv")

    def bucket_eff(x: Optional[float]) -> str:
        if x is None:
            return ""
        if x >= 92:
            return "excellent sleep efficiency"
        if x >= 85:
            return "good efficiency"
        if x >= 80:
            return "okay efficiency"
        return "lower efficiency"

    p1_bits: List[str] = []
    p1_bits.append(f"You slept about {h}h {mins}m" + (f" with {bucket_eff(eff)} ({eff:.0f}%)." if eff else "."))
    if deep_pct is not None and rem_pct is not None and light_pct is not None:
        p1_bits.append(f"Sleep composition looked balanced: Deep {deep_pct:.0f}%, REM {rem_pct:.0f}%, Light {light_pct:.0f}%.")
    if score is not None:
        p1_bits.append(f"Garmin's sleep score was {score:.0f}, a simple read on overall quality.")
    if hrv is not None:
        p1_bits.append(f"Average overnight HRV was about {hrv:.0f} ms, a soft indicator of recovery.")
    p1 = " ".join(p1_bits)

    # Tailored feedback and actions
    recs: List[str] = []
    if deep_pct is not None and deep_pct < 20:
        recs.append("Deep sleep ran a bit light — try a cooler room, darker lighting, and a gentle 20–30 minute wind-down.")
    if rem_pct is not None and rem_pct < 20:
        recs.append("REM looked light — reduce late-night screens and heavy food; light stretching and quiet reading can help.")
    if eff is not None and eff < 85:
        recs.append("Efficiency dipped — aim for a consistent bedtime and limit in-bed wake time; if you're awake, get up for 5–10 minutes and reset.")
    if not recs:
        recs.append("Overall pattern looks steady — keep the same pre-sleep routine and timing to compound results.")
    recs.append("Tonight: finish caffeine by early afternoon, dim lights 60–90 minutes before bed, and park tomorrow's to‑dos on paper.")
    p2 = " ".join(recs)

    return p1 + "\n\n" + p2


# ---------------------------
# News fetchers (RSS/Atom)
# ---------------------------

FEEDS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.reuters.com/reuters/worldNews",
    "https://feeds.npr.org/1001/rss.xml",
]


def _parse_feed(url: str) -> List[Dict]:
    items: List[Dict] = []
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        # RSS: channel/item
        for it in root.findall('.//item'):
            title = (it.findtext('title') or '').strip()
            link = (it.findtext('link') or '').strip()
            desc = (it.findtext('description') or '').strip()
            pd = it.findtext('pubDate') or ''
            dt = None
            try:
                dt = parsedate_to_datetime(pd)
            except Exception:
                dt = None
            if title:
                items.append({"title": title, "link": link, "summary": desc, "published": dt})
        # Atom: entry
        for it in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            title = (it.findtext('{http://www.w3.org/2005/Atom}title') or '').strip()
            link_el = it.find('{http://www.w3.org/2005/Atom}link')
            link = link_el.get('href') if link_el is not None else ''
            desc = (it.findtext('{http://www.w3.org/2005/Atom}summary') or '').strip()
            pd = it.findtext('{http://www.w3.org/2005/Atom}updated') or ''
            dt = None
            try:
                dt = parsedate_to_datetime(pd)
            except Exception:
                try:
                    dt = datetime.datetime.fromisoformat(pd.replace('Z', '+00:00'))
                except Exception:
                    dt = None
            if title:
                items.append({"title": title, "link": link, "summary": desc, "published": dt})
    except Exception:
        return []
    return items


def fetch_news() -> Tuple[List[str], List[str]]:
    now = datetime.datetime.now()
    start_12h = now - datetime.timedelta(hours=12)
    # yesterday window (local)
    today_mid = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0, 0))
    y_start = today_mid - datetime.timedelta(days=1)
    y_end = today_mid

    pool: List[Dict] = []
    for u in FEEDS:
        pool.extend(_parse_feed(u))

    def pick(start: datetime.datetime, end: datetime.datetime, limit: int) -> List[str]:
        out: List[str] = []
        seen = set()
        def key(item):
            dt = item.get('published') or datetime.datetime.min
            return dt
        for it in sorted(pool, key=key, reverse=True):
            dt = it.get('published')
            if not isinstance(dt, datetime.datetime):
                continue
            if dt.tzinfo is not None:
                try:
                    dt = dt.astimezone().replace(tzinfo=None)
                except Exception:
                    dt = dt.replace(tzinfo=None)
            if start <= dt <= end:
                t = it.get('title') or ''
                if not t:
                    continue
                keyt = t.lower()
                if keyt in seen:
                    continue
                seen.add(keyt)
                host = urlparse(it.get('link') or '').netloc or 'news'
                summ = _clip_text(it.get('summary') or '')
                line = f"{t} - {host}"
                if summ:
                    line = f"{line}. {summ}"
                out.append(line)
                if len(out) >= limit:
                    break
        return out

    last12 = pick(start_12h, now, 6)
    yester = pick(y_start, y_end, 6)
    if not last12:
        last12 = ["Overnight recap not available", "Check feeds later", "Network limited"]
    if not yester:
        yester = ["Yesterday recap not available", "Check feeds later", "Network limited"]
    # ensure no duplicates between the two lists
    low12 = {t.lower() for t in last12}
    yester = [t for t in yester if t.lower() not in low12]
    return last12, yester


def suggested_plans() -> List[str]:
    weekday_core = [
        "Wake, water, and 5–10 minutes of daylight",
        "Morning movement (mobility + 5 minutes breathing)",
        "Deep work block (120–150 min) on the highest‑leverage task",
        "Short reset: 10‑minute walk or stretch",
        "Admin sweep: inbox zero in one 20‑minute pass",
        "Second deep work block (60–90 min) to push one needle",
        "Lunch away from desk; 10 minutes outside afterwards",
        "Light coordination/outreach (30–45 min): one nudge that matters",
        "Wrap‑up (20–30 min): log wins, plan tomorrow, park open loops",
        "Evening: dim screens, low‑stress wind‑down, read 10 pages",
    ]
    weekend_core = [
        "Wake, water, and light mobility",
        "Hobby/learning block (90–120 min)",
        "Errands or deep tidy (30–45 min)",
        "Movement outside (walk, easy ride, or hike)",
        "Social/outreach: one call or coffee",
        "Meal prep or shopping (60 min)",
        "Plan the week in 20 minutes: priorities and 3 key blocks",
    ]
    dow = datetime.datetime.today().weekday()
    return weekend_core if dow in (5, 6) else weekday_core


def food_plan() -> List[str]:
    options = [
        [
            "Breakfast: Greek yogurt + berries + granola",
            "Snack: banana + handful of nuts",
            "Lunch: chicken and rice + leafy greens",
            "Snack: cottage cheese + fruit",
            "Dinner: salmon + vegetables + potatoes",
            "Hydration: 2–3L water across the day",
        ],
        [
            "Breakfast: oatmeal + eggs",
            "Snack: apple + peanut butter",
            "Lunch: turkey wrap + salad",
            "Snack: protein shake",
            "Dinner: stir‑fry and rice noodles",
            "Hydration: tea/water; limit caffeine after noon",
        ],
        [
            "Breakfast: smoothie (protein + fruit + spinach)",
            "Snack: Greek yogurt",
            "Lunch: steak and potatoes + greens",
            "Snack: carrots + hummus",
            "Dinner: shrimp + quinoa + greens",
            "Hydration: water with each meal",
        ],
    ]
    return random.choice(options)


def _load_last_advice() -> Optional[str]:
    try:
        y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        p = Path(f"open-webui-full/backend/data/sky_daily/{y}.json")
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8")).get("good_word_of_advice")
    except Exception:
        return None
    return None


def _select_advice() -> str:
    pool = [
        "Progress favors consistency over intensity.",
        "Protect the first hour; it sets the pace.",
        "Measure what matters, ignore the rest.",
        "Move first, then think — motion fuels clarity.",
        "Reduce inputs to improve outputs.",
        "Tiny improvements compound into momentum.",
        "When in doubt, simplify and ship.",
        "Keep your energy for what compounds and cut the rest.",
        "Today is built from what you measure and what you ignore.",
    ]
    last = _load_last_advice()
    candidates = [a for a in pool if a != last] or pool
    return random.choice(candidates)


def morning_digest() -> Dict:
    metrics = _parse_latest_metrics()
    news12, news_yday = fetch_news()
    payload = {
        "date": datetime.date.today().isoformat(),
        "sleep_review": _sleep_prose(metrics),
        "overnight_news": news12,
        "previous_day_news": news_yday,
        "plans_placeholder": suggested_plans(),
        "food_recommendations": food_plan(),
        "good_word_of_advice": _select_advice(),
    }
    return payload


def _save_local(payload: Dict) -> str:
    base = Path("open-webui-full/backend/data/sky_daily")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{payload.get('date')}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return str(path)


def post_digest(payload: Dict) -> None:
    stored = _save_local(payload)
    try:
        res = requests.post(OWUI_ENDPOINT, json=payload, timeout=10)
        print(f"[{res.status_code}] Morning digest posted -> {res.json()}")
    except Exception as e:
        print(f"FAILED to post morning digest: {e}. Local file saved at: {stored}")


if __name__ == "__main__":
    post_digest(morning_digest())

