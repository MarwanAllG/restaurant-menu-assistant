"""Create two local password accounts without putting credentials in source control."""

import argparse
import getpass
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import dotenv_values, set_key

from core.auth import hash_password
from core.config import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate", action="store_true", help="Generate private local test credentials"
    )
    args = parser.parse_args()
    path = ROOT / ".env"
    path.touch(exist_ok=True)
    existing = dotenv_values(path)
    if existing.get("TEST_ACCOUNTS_JSON"):
        raise SystemExit("Accounts already configured; existing credentials were preserved.")
    accounts = {}
    generated = []
    for default in ["Marwan", "Toka"]:
        username = (
            default if args.generate else (input(f"Username [{default}]: ").strip() or default)
        )
        if username in accounts:
            raise SystemExit("Usernames must differ")
        password = (
            secrets.token_urlsafe(18)
            if args.generate
            else getpass.getpass(f"Password for {username} (at least 12 characters): ")
        )
        if len(password) < 12:
            raise SystemExit("Use at least 12 characters")
        if not args.generate and password != getpass.getpass("Confirm password: "):
            raise SystemExit("Passwords do not match")
        accounts[username] = hash_password(password)
        generated.append(f"{username}: {password}")
    set_key(path, "TEST_ACCOUNTS_JSON", json.dumps(accounts))
    if not existing.get("CHAINLIT_AUTH_SECRET"):
        set_key(path, "CHAINLIT_AUTH_SECRET", secrets.token_urlsafe(48))
    os.chmod(path, 0o600)
    if args.generate:
        credentials = ROOT / "data" / "local-test-accounts.txt"
        credentials.parent.mkdir(exist_ok=True)
        with credentials.open("x") as handle:
            handle.write(
                "Local test accounts. Never commit this file.\n" + "\n".join(generated) + "\n"
            )
        os.chmod(credentials, 0o600)
        print("Private credentials saved to data/local-test-accounts.txt")
    print("Saved two hashed accounts and authentication secret to ignored .env. API key unchanged.")


if __name__ == "__main__":
    main()
