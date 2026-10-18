#!/usr/bin/env python3
"""Validate FYI calendar data without third-party dependencies."""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


def validate(data):
    def check(condition, message):
        if not condition:
            raise ValueError(message)

    def date(value):
        check(isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)), "日期格式无效")
        return dt.date.fromisoformat(value)

    check(data["schemaVersion"] == 1 and data["region"] == "CN" and data["timezone"] == "Asia/Shanghai", "协议版本/地区/时区错误")
    year = data["year"]
    check(type(year) is int and 1901 <= year <= 2099, "年份超出范围")
    check(data["officialStatus"] in ("confirmed", "pending", "unavailable"), "官方状态无效")
    if data["checkedAt"] is not None:
        checked = dt.datetime.fromisoformat(data["checkedAt"].replace("Z", "+00:00"))
        check(checked.tzinfo is not None, "核对时间需要时区")
    sources = set()
    for s in data["sources"]:
        check(s["id"] and s["id"] not in sources and s["title"].strip(), "来源缺失或重复")
        sources.add(s["id"])
        u = s["url"]
        check(isinstance(u, str) and not re.search(r"[\s\x00-\x1f\x7f]", u), "来源 URL 有空白或控制字符")
        parsed = urlsplit(u)
        check(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password, "来源须为完整 HTTPS 地址")
        check(parsed.port is None or 1 <= parsed.port <= 65535, "来源端口错误")
        check(not re.search(r"%(?![0-9a-fA-F]{2})", u), "来源百分号转义错误")
        date(s["publishedAt"])
    def entry(e):
        check(e["sourceId"] in sources and isinstance(e["name"], str) and 0 < len(e["name"].strip()) <= 80, "缺少来源或名称无效")
    off = set()
    for h in data["holidays"]:
        entry(h)
        start, end = date(h["start"]), date(h["end"])
        check(start.year == year == end.year and start <= end, "假期年份或区间错误")
        days = {start + dt.timedelta(days=i) for i in range((end - start).days + 1)}
        check(not off.intersection(days), "假期重叠")
        off.update(days)
    work = set()
    for w in data["workdays"]:
        entry(w)
        d = date(w["date"])
        check(d.year == year and d not in off and d not in work, "补班年份错误、重复或与放假冲突")
        work.add(d)
    events = set()
    for e in data["events"]:
        entry(e)
        check(date(e["date"]).year == year and e["kind"] in ("festival", "observance"), "节日日期/类型错误")
        key = (e["date"], e["name"])
        check(key not in events, "节日重复")
        events.add(key)
    if data["officialStatus"] == "confirmed":
        check(off and sources and data["checkedAt"], "已确认年份缺少资料")
    else:
        check(not off and not work, "未确认年份不能标记休/班")


if __name__ == "__main__":
    paths = [Path(p) for p in sys.argv[1:]] or sorted(Path("data/calendar/cn").glob("*.json"))
    if not paths:
        sys.exit("没有日历文件")
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            validate(data)
            if path.stem != str(data["year"]):
                raise ValueError("文件名与年份不一致")
        except (ValueError, KeyError, TypeError, OSError) as exc:
            sys.exit(f"{path}: {exc}")
        print(f"OK {path}")
