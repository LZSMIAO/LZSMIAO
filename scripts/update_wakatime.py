"""Update the compact profile section using WakaTime's last seven days."""

import base64
import json
import math
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

README = Path(__file__).resolve().parents[1] / "README.md"
START, END = "<!-- WAKATIME:START -->", "<!-- WAKATIME:END -->"


def number(value):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Invalid duration or percentage")
    return value


def duration(seconds):
    minutes = int(number(seconds) // 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m" if minutes else "<1m"


def label(value):
    # Keep provider labels inside a single plain-text line.
    return re.sub(r"[^\w .+#/-]", "", str(value))[:24].strip() or "Other"


def render(data):
    total = number(data["total_seconds"])
    if total == 0:
        return "近七天暫無編程活動。"
    languages = sorted(data["languages"], key=lambda row: number(row["total_seconds"]), reverse=True)
    editors = sorted(data["editors"], key=lambda row: number(row["total_seconds"]), reverse=True)
    lines = [f"近七天 · **{duration(total)}**", "", "```text"]
    for row in languages[:4]:
        percent = min(100, number(row["percent"]))
        filled = round(percent / 10)
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"{label(row['name']):<16} {duration(row['total_seconds']):>8}  {bar} {percent:5.1f}%")
    lines += ["```"]
    if editors:
        lines += ["", "編輯器：" + " · ".join(f"{label(row['name'])} {duration(row['total_seconds'])}" for row in editors[:2])]
    start, end = str(data["start"])[:10], str(data["end"])[:10]
    if not all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) for date in (start, end)):
        raise ValueError("Invalid reporting dates")
    lines += ["", f"<sub>{start} — {end} · WakaTime</sub>"]
    return "\n".join(lines)


def replace_section(original, content):
    if original.count(START) != 1 or original.count(END) != 1:
        raise ValueError("README must contain exactly one statistics block")
    before, remainder = original.split(START)
    if END not in remainder:
        raise ValueError("Statistics markers are out of order")
    _, after = remainder.split(END)
    return before + START + "\n" + content + "\n" + END + after


def main():
    key = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not key:
        print("WAKATIME_API_KEY is not configured; README unchanged.")
        return
    request = Request(
        "https://api.wakatime.com/api/v1/users/current/stats/last_7_days",
        headers={
            "Authorization": "Basic " + base64.b64encode(key.encode()).decode(),
            "Accept": "application/json",
            "User-Agent": "LZSMIAO-profile",
        },
    )
    with urlopen(request, timeout=30) as response:
        if response.status == 202:
            print("WakaTime is calculating statistics; README unchanged.")
            return
        data = json.load(response)["data"]
    if not data.get("is_up_to_date"):
        print("WakaTime statistics are stale; README unchanged.")
        return
    original = README.read_text(encoding="utf-8")
    updated = replace_section(original, render(data))
    if updated != original:
        README.write_text(updated, encoding="utf-8")
        print("Updated the seven-day coding summary.")
    else:
        print("Statistics unchanged.")


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        print(f"WakaTime returned HTTP {error.code}; README unchanged.", file=sys.stderr)
        sys.exit(1)
    except (URLError, TimeoutError, ValueError, KeyError, TypeError, OSError):
        print("Could not retrieve valid WakaTime statistics; README unchanged.", file=sys.stderr)
        sys.exit(1)
