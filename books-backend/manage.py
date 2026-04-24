#!/usr/bin/env python3
"""Management commands for the Books backend."""

import argparse
import sys
from getpass import getpass
from pathlib import Path

from pydantic import ValidationError

from app.auth import create_user
from app.database import SessionLocal
from app.models import User
from app.schemas import UserCreate


def handle_create_superuser(args: argparse.Namespace) -> int:
    """Create the single allowed user account."""

    username = (args.username or "").strip()
    password = args.password

    if not username:
        username = input("Username: ").strip()

    if not username:
        print("Error: Username cannot be empty.", file=sys.stderr)
        return 1

    if password is None:
        password = getpass("Password: ")
        password_confirmation = getpass("Password (again): ")
        if password != password_confirmation:
            print("Error: Passwords do not match.", file=sys.stderr)
            return 1

    try:
        # Reuse Pydantic validation rules from the API
        UserCreate(username=username, password=password)
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    session = SessionLocal()
    try:
        create_user(session, username, password)
    except ValueError as exc:
        session.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    else:
        print(f"Superuser '{username}' created successfully.")
        return 0
    finally:
        session.close()


def handle_seed_reading_list(args: argparse.Namespace) -> int:
    """Import a Reading List ZIP for an existing user."""

    from main import ImportReadingListError, import_reading_list_from_bytes

    zip_path = Path(args.zip)
    if not zip_path.is_file():
        print(f"Error: ZIP not found at {zip_path}", file=sys.stderr)
        return 1

    username = (args.username or "").strip()
    if not username:
        print("Error: --username is required.", file=sys.stderr)
        return 1

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            print(f"Error: user '{username}' not found.", file=sys.stderr)
            return 1

        content = zip_path.read_bytes()
        try:
            result = import_reading_list_from_bytes(session, user.id, content)
        except ImportReadingListError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    finally:
        session.close()

    print(f"Imported {result['imported']} book(s), skipped {result['skipped']}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Books backend management commands.")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser(
        "create-superuser",
        help="Create the single superuser account.",
    )
    create_parser.add_argument(
        "--username",
        "-u",
        help="Username for the superuser.",
    )
    create_parser.add_argument(
        "--password",
        "-p",
        help="Password for the superuser (use with caution, prefer interactive prompt).",
    )

    seed_parser = subparsers.add_parser(
        "seed-reading-list",
        help="Import a Reading List ZIP fixture for an existing user.",
    )
    seed_parser.add_argument(
        "--username", "-u", required=True, help="Target username."
    )
    seed_parser.add_argument(
        "--zip",
        required=True,
        help="Path to the Reading List ZIP to import.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "create-superuser":
        return handle_create_superuser(args)
    if args.command == "seed-reading-list":
        return handle_seed_reading_list(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
