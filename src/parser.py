from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

DAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MAX_SLOTS = 13
MINUTES_PER_DAY = 1440


@dataclass
class DaySchedule:
    # List of (endtime_minutes, temperature) sorted by endtime, last entry endtime=1440
    slots: list[tuple[int, float]] = field(default_factory=list)


@dataclass
class RoomSchedule:
    room: str
    days: dict[str, DaySchedule] = field(default_factory=dict)  # key: Mo..So


def _parse_time(value) -> int:
    """Parse HH:MM string, Excel time float, or datetime.time/datetime to minutes since midnight."""
    import datetime
    if isinstance(value, str):
        h, m = value.strip().split(":")
        return int(h) * 60 + int(m)
    if isinstance(value, float):
        total = round(value * MINUTES_PER_DAY)
        return total % MINUTES_PER_DAY or MINUTES_PER_DAY
    if isinstance(value, datetime.datetime):
        return value.hour * 60 + value.minute
    if isinstance(value, datetime.time):
        return value.hour * 60 + value.minute
    raise ValueError(f"Cannot parse time: {value!r}")


def parse_xlsx(path: Path) -> list[RoomSchedule]:
    wb = openpyxl.load_workbook(path, data_only=True)
    rooms = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        schedule = _parse_sheet(sheet_name, ws)
        rooms.append(schedule)
    return rooms


def _parse_sheet(room: str, ws) -> RoomSchedule:
    rows = list(ws.iter_rows(values_only=True))
    # Find header row (contains 'von' or 'bis')
    header_idx = None
    for i, row in enumerate(rows):
        if row and str(row[0]).strip().lower() == "von":
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"Sheet '{room}': header row with 'von' not found")

    header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
    day_cols = {}
    for day in DAYS:
        for j, h in enumerate(header):
            if h == day:
                day_cols[day] = j
                break

    missing = [d for d in DAYS if d not in day_cols]
    if missing:
        raise ValueError(f"Sheet '{room}': missing day columns: {missing}")

    bis_col = header.index("bis")
    day_schedules: dict[str, list[tuple[int, float]]] = {d: [] for d in DAYS}

    for row in rows[header_idx + 1:]:
        if not row or row[bis_col] is None:
            continue
        try:
            endtime = _parse_time(row[bis_col])
        except (ValueError, TypeError):
            continue
        # 24:00 → 1440
        if endtime == 0:
            endtime = MINUTES_PER_DAY
        for day in DAYS:
            raw = row[day_cols[day]]
            if raw is None:
                continue
            temp = float(raw)
            day_schedules[day].append((endtime, temp))

    rs = RoomSchedule(room=room)
    for day in DAYS:
        slots = sorted(day_schedules[day], key=lambda x: x[0])
        if not slots:
            raise ValueError(f"Sheet '{room}', day '{day}': no data rows found")
        if slots[-1][0] != MINUTES_PER_DAY:
            raise ValueError(
                f"Sheet '{room}', day '{day}': last endtime must be 24:00 (1440), got {slots[-1][0]}"
            )
        if len(slots) > MAX_SLOTS:
            raise ValueError(
                f"Sheet '{room}', day '{day}': {len(slots)} slots exceed max {MAX_SLOTS}"
            )
        rs.days[day] = DaySchedule(slots=slots)
    return rs
