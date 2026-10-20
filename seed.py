"""Load seed.json (real applications) into the database.

Usage:  python seed.py
Skips rows whose company+role already exist, so it is safe to re-run.
"""

import json
from datetime import date
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.models import Application, ApplicationStatus

Base.metadata.create_all(bind=engine)


def main() -> None:
    rows = json.loads(Path(__file__).with_name("seed.json").read_text())
    db = SessionLocal()
    inserted = 0
    for row in rows:
        exists = (
            db.query(Application)
            .filter(Application.company == row["company"], Application.role == row["role"])
            .first()
        )
        if exists:
            continue
        row = dict(row)
        row["date_applied"] = date.fromisoformat(row["date_applied"])
        row["status"] = ApplicationStatus(row["status"])
        db.add(Application(**row))
        inserted += 1
    db.commit()
    db.close()
    print(f"Inserted {inserted} applications ({len(rows)} in seed file).")


if __name__ == "__main__":
    main()
