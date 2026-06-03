"""Password hashing using PBKDF2-HMAC-SHA256 (stdlib only)."""

import binascii
import hashlib
import os

_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return binascii.hexlify(salt).decode() + ":" + binascii.hexlify(dk).decode()


def verify_password(stored: str, provided: str) -> bool:
    salt_hex, dk_hex = stored.split(":", 1)
    salt = binascii.unhexlify(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", provided.encode(), salt, _ITERATIONS)
    return binascii.hexlify(dk).decode() == dk_hex
