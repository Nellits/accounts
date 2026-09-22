"""Copy users from a TV Tracker database into Accounts, preserving ids.

Usage:
  # From backend/ with both DATABASE_URL (accounts) and TVTRACKER_DATABASE_URL set:
  python scripts/migrate_from_tvtracker.py

  # Or pass URLs:
  python scripts/migrate_from_tvtracker.py \\
    --source postgresql://.../tvtracker \\
    --dest postgresql://.../accounts

Admin ids: set ADMIN_USER_IDS=1,2 (same as tvtracker) to mark is_admin.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _parse_admin_ids(raw: str) -> set[int]:
    out: set[int] = set()
    for part in raw.split(","):
        p = part.strip()
        if p.isdigit():
            out.add(int(p))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate users from tvtracker to accounts")
    parser.add_argument("--source", default=os.getenv("TVTRACKER_DATABASE_URL", ""))
    parser.add_argument("--dest", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument(
        "--admin-ids",
        default=os.getenv("ADMIN_USER_IDS", ""),
        help="Comma-separated user ids to mark is_admin",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rows that would be inserted without writing",
    )
    args = parser.parse_args()
    if not args.source or not args.dest:
        print("Both --source (or TVTRACKER_DATABASE_URL) and --dest (or DATABASE_URL) are required.")
        return 1

    admin_ids = _parse_admin_ids(args.admin_ids)
    src = create_engine(args.source)
    dst = create_engine(args.dest)

    with src.connect() as sconn:
        rows = sconn.execute(
            text(
                """
                SELECT id, name, email, password_hash,
                       password_reset_token_hash, password_reset_expires_at,
                       avatar_url, theme
                FROM users
                WHERE email IS NOT NULL
                ORDER BY id
                """
            )
        ).mappings().all()

    print(f"Found {len(rows)} users with email in source")
    if args.dry_run:
        for r in rows:
            print(f"  id={r['id']} email={r['email']} admin={r['id'] in admin_ids}")
        return 0

    inserted = 0
    updated = 0
    with dst.begin() as dconn:
        for r in rows:
            is_admin = r["id"] in admin_ids
            existing = dconn.execute(
                text("SELECT id FROM users WHERE id = :id"),
                {"id": r["id"]},
            ).first()
            params = {
                "id": r["id"],
                "name": r["name"],
                "email": r["email"],
                "password_hash": r["password_hash"],
                "password_reset_token_hash": r["password_reset_token_hash"],
                "password_reset_expires_at": r["password_reset_expires_at"],
                "avatar_url": r["avatar_url"],
                "theme": r["theme"],
                "is_admin": is_admin,
            }
            if existing:
                dconn.execute(
                    text(
                        """
                        UPDATE users SET
                          name = :name,
                          email = :email,
                          password_hash = :password_hash,
                          password_reset_token_hash = :password_reset_token_hash,
                          password_reset_expires_at = :password_reset_expires_at,
                          avatar_url = :avatar_url,
                          theme = :theme,
                          is_admin = :is_admin
                        WHERE id = :id
                        """
                    ),
                    params,
                )
                updated += 1
            else:
                dconn.execute(
                    text(
                        """
                        INSERT INTO users (
                          id, name, email, password_hash,
                          password_reset_token_hash, password_reset_expires_at,
                          avatar_url, theme, is_admin
                        ) VALUES (
                          :id, :name, :email, :password_hash,
                          :password_reset_token_hash, :password_reset_expires_at,
                          :avatar_url, :theme, :is_admin
                        )
                        """
                    ),
                    params,
                )
                inserted += 1

        # Keep sequence ahead of max id (Postgres)
        if "postgresql" in str(dst.url):
            dconn.execute(
                text(
                    """
                    SELECT setval(
                      pg_get_serial_sequence('users', 'id'),
                      COALESCE((SELECT MAX(id) FROM users), 1)
                    )
                    """
                )
            )

    print(f"Done. inserted={inserted} updated={updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
