#!/usr/bin/env python3
import argparse
import os
import sys

from dotenv import load_dotenv

from src.ccu3 import CCU3Client
from src.diff import compute_diffs, effective_slots
from src.loader import load_source
from src.parser import parse_xlsx, MAX_SLOTS


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Sync heating schedules from XLSX to CCU3 HmIP-BWTH devices."
    )
    parser.add_argument("source", help="Path to .xlsx file or public Google Drive share link")
    parser.add_argument("--dry-run", action="store_true", help="Show diff only, write nothing")
    parser.add_argument("--room", metavar="ROOM", help="Process only this room (sheet name)")
    args = parser.parse_args()

    host = os.getenv("CCU3_HOST")
    if not host:
        print("ERROR: CCU3_HOST not set. Copy .env.template to .env and fill in values.", file=sys.stderr)
        sys.exit(1)

    port = int(os.getenv("CCU3_PORT", "8181"))
    user = os.getenv("CCU3_USER", "")
    password = os.getenv("CCU3_PASSWORD", "")

    # Load and parse XLSX
    try:
        xlsx_path = load_source(args.source)
    except Exception as e:
        print(f"ERROR loading source: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        room_schedules = parse_xlsx(xlsx_path)
    except Exception as e:
        print(f"ERROR parsing XLSX: {e}", file=sys.stderr)
        sys.exit(1)

    if args.room:
        room_schedules = [r for r in room_schedules if r.room == args.room]
        if not room_schedules:
            print(f"ERROR: Room '{args.room}' not found in XLSX sheets.", file=sys.stderr)
            sys.exit(1)

    # Connect to CCU3 and discover devices
    ccu = CCU3Client(host, port, user, password)
    try:
        device_map = ccu.find_bwth_devices()
    except Exception as e:
        print(f"ERROR connecting to CCU3 at {host}:{port}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"CCU3 device map (room → channel address):")
    for room, addr in device_map.items():
        print(f"  {room} → {addr}")
    print()

    any_error = False
    for rs in room_schedules:
        if rs.room not in device_map:
            print(f"WARNING: Room '{rs.room}' has no HmIP-BWTH device on CCU3 — skipping.")
            any_error = True
            continue

        channel_addr = device_map[rs.room]
        print(f"Room: {rs.room}  ({channel_addr})")

        try:
            current = ccu.read_schedule(channel_addr)
        except Exception as e:
            print(f"  ERROR reading schedule: {e}")
            any_error = True
            continue

        diffs = compute_diffs(rs.days, current)

        if not diffs:
            print("  all days unchanged")
            continue

        for day, slots in diffs.items():
            if args.dry_run:
                target_eff = effective_slots(slots)
                current_eff = effective_slots(current.get(day, []))
                print(f"  {day}: would update ({len(target_eff)} active slots)")
                for i, (et, temp) in enumerate(target_eff):
                    c_et, c_temp = current_eff[i] if i < len(current_eff) else (None, None)
                    marker = " *" if (et != c_et or c_temp is None or abs(temp - c_temp) >= 0.25) else ""
                    print(f"    slot {i+1:2d}: {et:4d}min  {temp:.1f}°C{marker}")
                unused = MAX_SLOTS - len(target_eff)
                if unused > 0:
                    print(f"    (+ {unused} unused slots)")
            else:
                try:
                    ccu.write_day(channel_addr, day, slots)
                    print(f"  {day}: updated ({len(slots)} slots)")
                except Exception as e:
                    print(f"  {day}: ERROR writing: {e}")
                    any_error = True

    sys.exit(1 if any_error else 0)


if __name__ == "__main__":
    main()
