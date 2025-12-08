#!/usr/bin/env python3
"""Management commands for the Books backend."""

import argparse
import sys
from getpass import getpass

from pydantic import ValidationError

from app.auth import create_user
from app.database import SessionLocal
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "create-superuser":
        return handle_create_superuser(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
