import base64
import hashlib
import hmac
import json
import os
import secrets

ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(ITERATIONS),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or not 100000 <= int(rounds) <= 2000000:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt), int(rounds)
        )
        return hmac.compare_digest(actual, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str) -> bool:
    try:
        accounts = json.loads(os.getenv("TEST_ACCOUNTS_JSON") or "{}")
        encoded = accounts.get(username)
        # Do comparable work for an unknown account too.
        dummy = "pbkdf2_sha256$600000$c29tZXJhbmRvbXNhbHQ=$" + base64.b64encode(bytes(32)).decode()
        valid = verify_password(password, encoded or dummy)
        return bool(encoded and valid)
    except (ValueError, TypeError, AttributeError):
        return False
