#!/usr/bin/env python3
"""Reset local dev state, import fixture books, generate sample books, and run the backend."""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SHELVES = ("want_to_read", "started", "paused", "finished", "abandoned")


def nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reset books.db, uploads/ and media/, seed dev books, and start the backend.",
    )
    parser.add_argument("--username", default=os.getenv("DEV_USERNAME", "dev"))
    parser.add_argument("--password", default=os.getenv("DEV_PASSWORD", "devpassword"))
    parser.add_argument(
        "--fixture",
        type=Path,
        default=os.getenv("DEV_FIXTURE", "fixtures/reading_list_sample.zip"),
        help="Reading List export ZIP, relative to books-backend (default: %(default)s)",
    )
    parser.add_argument(
        "--sample-books",
        type=nonnegative_int,
        default=0,
        help="Extra generated books to add alongside the fixture (default: 0)",
    )
    parser.add_argument(
        "--shelf",
        choices=SHELVES,
        default="want_to_read",
        help="Reading shelf for generated books (default: %(default)s)",
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Seed data without starting the backend",
    )
    return parser


def validate_fixture(path: Path) -> None:
    if not path.is_file():
        raise ValueError(
            f"Fixture not found at {path}. If this is a fresh clone, run: git lfs pull"
        )

    with path.open("rb") as fixture:
        if b"git-lfs" in fixture.read(512):
            raise ValueError("Fixture is an LFS pointer. Run: git lfs pull")

    try:
        with zipfile.ZipFile(path) as archive:
            archive.read("data.csv").decode("utf-8")
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError) as exc:
        raise ValueError(
            "Fixture must be a Reading List ZIP containing UTF-8 data.csv"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    fixture = BACKEND_DIR / args.fixture

    try:
        validate_fixture(fixture)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    env = dict(os.environ, DATABASE_URL="sqlite:///./books.db", UPLOADS_DIR="uploads")

    def run(*command: str) -> None:
        subprocess.run(["uv", "run", *command], cwd=BACKEND_DIR, env=env, check=True)

    print("==> Resetting dev state", flush=True)
    for name in ("books.db", "books.db-wal", "books.db-shm"):
        (BACKEND_DIR / name).unlink(missing_ok=True)
    for name in ("uploads", "media"):
        path = BACKEND_DIR / name
        if path.is_symlink():
            path.unlink()
        elif path.exists():
            shutil.rmtree(path)
        path.mkdir()

    try:
        print("==> Running migrations", flush=True)
        run("alembic", "upgrade", "head")
        print(f"==> Creating user '{args.username}'", flush=True)
        run(
            "python",
            "manage.py",
            "create-superuser",
            "--username",
            args.username,
            "--password",
            args.password,
        )

        print(f"==> Seeding Reading List from {fixture}", flush=True)
        run(
            "python",
            "manage.py",
            "seed-reading-list",
            "--username",
            args.username,
            "--zip",
            str(fixture),
        )

        if args.sample_books:
            print(
                f"==> Adding {args.sample_books} sample books to {args.shelf}",
                flush=True,
            )
            run(
                "python",
                "manage.py",
                "seed-sample-books",
                "--username",
                args.username,
                "--count",
                str(args.sample_books),
                "--shelf",
                args.shelf,
            )
    except subprocess.CalledProcessError as exc:
        return exc.returncode

    if not args.no_start:
        print("==> Starting backend (Ctrl-C to stop)", flush=True)
        os.chdir(BACKEND_DIR)
        os.execvpe("uv", ["uv", "run", "fastapi", "dev", "main.py"], env)

    return 0


if __name__ == "__main__":
    sys.exit(main())
