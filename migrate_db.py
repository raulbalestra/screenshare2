"""
Small CLI to run DB migrations manually.
Usage:
    python migrate_db.py

It will call DatabaseManager.migrate_add_email_column() which is idempotent and safe to run multiple times.
"""
import os
import sys

# ensure project dir is on path
project_root = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.models import DatabaseManager


def main():
    try:
        print("Running DB migration: add email column if missing...")
        DatabaseManager.migrate_add_email_column()
        print("Migration finished.")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
