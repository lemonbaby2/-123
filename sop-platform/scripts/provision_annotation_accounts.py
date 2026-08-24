"""Provision shared SOP accounts without storing a plaintext password in source control."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path


LABELERS = [(f"labeler{index:02d}", f"标注员{index:02d}") for index in range(1, 6)]


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${derived.hex()}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    if len(args.password) < 6:
        raise SystemExit("password must contain at least 6 characters")
    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"database does not exist: {database}")
    backup_dir = database.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"before_account_provision_{time.strftime('%Y%m%d_%H%M%S')}.sqlite3"
    with sqlite3.connect(database, timeout=60) as source, sqlite3.connect(backup_path) as target:
        source.backup(target)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(database, timeout=60) as connection:
        connection.execute("PRAGMA busy_timeout=60000")
        connection.execute("BEGIN IMMEDIATE")
        active_users = [row[0] for row in connection.execute("SELECT username FROM users WHERE active = 1")]
        for username in active_users:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (password_hash(args.password), username),
            )
        for username, display_name in LABELERS:
            connection.execute(
                """INSERT INTO users(username, password_hash, display_name, role, active, created_at)
                   VALUES (?, ?, ?, 'worker', 1, ?)
                   ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,
                       display_name=excluded.display_name, role='worker', active=1""",
                (username, password_hash(args.password), display_name, now),
            )
        connection.execute("DELETE FROM auth_sessions")
        connection.execute(
            "INSERT INTO event_log(event_type, payload_json, recorded_at) VALUES (?, ?, ?)",
            (
                "admin.accounts_provisioned",
                json.dumps({"accounts": [item[0] for item in LABELERS], "active_passwords_reset": len(active_users)}, ensure_ascii=False),
                now,
            ),
        )
        connection.commit()
        accounts = [
            {"username": row[0], "display_name": row[1], "role": row[2], "active": bool(row[3])}
            for row in connection.execute("SELECT username, display_name, role, active FROM users ORDER BY user_id")
        ]
    print(json.dumps({"ok": True, "database": str(database), "backup": str(backup_path), "accounts": accounts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
