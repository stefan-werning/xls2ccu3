from .parser import DaySchedule, DAYS, MAX_SLOTS, MINUTES_PER_DAY


def normalize(schedule: DaySchedule) -> list[tuple[int, float]]:
    """Pad slots to MAX_SLOTS by repeating last temperature with endtime=1440."""
    slots = list(schedule.slots)
    last_temp = slots[-1][1] if slots else 4.5
    while len(slots) < MAX_SLOTS:
        slots.append((MINUTES_PER_DAY, last_temp))
    return slots


def diff_day(
    target: DaySchedule, current: list[tuple[int, float]]
) -> list[tuple[int, float]] | None:
    """Return normalized target slots if they differ from current, else None."""
    norm_target = normalize(target)
    # current already has MAX_SLOTS entries from CCU3 read
    if len(current) != MAX_SLOTS:
        return norm_target
    for (et, temp), (cet, ctemp) in zip(norm_target, current):
        if et != cet or abs(temp - ctemp) >= 0.25:
            return norm_target
    return None


def compute_diffs(
    target_days: dict[str, DaySchedule],
    current_days: dict[str, list[tuple[int, float]]],
) -> dict[str, list[tuple[int, float]]]:
    """Return dict of day → normalized slots for days that need updating."""
    result = {}
    for day in DAYS:
        if day not in target_days:
            continue
        current = current_days.get(day, [])
        changed = diff_day(target_days[day], current)
        if changed is not None:
            result[day] = changed
    return result
