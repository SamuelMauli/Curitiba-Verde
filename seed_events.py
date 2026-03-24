"""Seed the events database with comprehensive historical data."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from events.database import EventsDB
from pipeline.config import DATA_DIR


def seed():
    db_path = DATA_DIR / "events.db"
    db = EventsDB(str(db_path))

    # Clear existing events
    db._conn.execute("DELETE FROM eventos")
    db._conn.commit()

    # Load comprehensive events
    events_file = Path("events/seed_data/eventos_completos.json")
    if events_file.exists():
        count = db.seed_from_json(str(events_file))
        print(f"Loaded {count} events from eventos_completos.json")
    else:
        # Fallback to initial marcos
        fallback = Path("events/seed_data/marcos_iniciais.json")
        if fallback.exists():
            count = db.seed_from_json(str(fallback))
            print(f"Loaded {count} events from marcos_iniciais.json (fallback)")
        else:
            print("No event files found!")
            return

    total = db.count_events()
    print(f"Total events in database: {total}")

    # Show distribution
    events = db.list_events(limit=10000)
    by_year = {}
    by_cat = {}
    for e in events:
        y = e["data"][:4] if e.get("data") else "?"
        by_year[y] = by_year.get(y, 0) + 1
        c = e.get("categoria", "?")
        by_cat[c] = by_cat.get(c, 0) + 1

    print("\nBy year:")
    for y in sorted(by_year.keys()):
        print(f"  {y}: {by_year[y]}")

    print("\nBy category:")
    for c, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")

    db.close()


if __name__ == "__main__":
    seed()
