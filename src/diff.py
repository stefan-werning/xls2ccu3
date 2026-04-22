from .parser import DaySchedule, DAYS, MAX_SLOTS, MINUTES_PER_DAY


def normalize(schedule: DaySchedule) -> list[tuple[int, float]]:
    """Pad slots to MAX_SLOTS by repeating last temperature with endtime=1440."""
    slots = list(schedule.slots)
    last_temp = slots[-1][1] if slots else 4.5
    while len(slots) < MAX_SLOTS:
        slots.append((MINUTES_PER_DAY, last_temp))
    return slots


def effective_slots(slots: list[tuple[int, float]]) -> list[tuple[int, float]]:
    """Return the active slots: up to and including the first endtime==1440.
    Everything after that is considered unused by the BWTH."""
    out: list[tuple[int, float]] = []
    for et, temp in slots:
        out.append((et, temp))
        if et >= MINUTES_PER_DAY:
            break
    return out


def diff_day(
    target: DaySchedule, current: list[tuple[int, float]]
) -> list[tuple[int, float]] | None:
    """Return normalized target slots if the effective programming differs."""
    target_eff = effective_slots(target.slots)
    current_eff = effective_slots(current)
    if len(target_eff) != len(current_eff):
        return normalize(target)
    for (et, temp), (cet, ctemp) in zip(target_eff, current_eff):
        if et != cet or abs(temp - ctemp) >= 0.25:
            return normalize(target)
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
