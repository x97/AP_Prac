"""Ephemeral ECDH + AES-256-GCM payload encryption for selected API responses.

The browser generates a P-256 key pair per request and sends its raw public
key in ``X-Content-Pubkey``. The server generates an ephemeral key pair,
derives a shared AES key with HKDF-SHA256, encrypts the JSON body, and returns
its own public key in the envelope. The server keeps no per-session key state.

This raises the cost of casual scraping and keeps response bodies out of
plaintext proxies/logs. It cannot stop a determined logged-in user from
decrypting content in the browser.
"""

from __future__ import annotations

import base64
import os
from typing import Any, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

ALG = "ECDH-P256+HKDF-SHA256+AES-256-GCM"
VERSION = 1
INFO = b"ap-content-v1"


def _decode_public_key(value: str) -> ec.EllipticCurvePublicKey:
    raw = base64.b64decode(value, validate=True)
    if len(raw) != 65 or raw[0] != 0x04:
        raise ValueError("public key must be an uncompressed P-256 point")
    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def aad_for(method: str, path: str) -> bytes:
    return f"ap-content-v1|{method.upper()}|{path}".encode("utf-8")


def encrypt_for_client(
    payload: bytes,
    client_public_key_b64: str,
    aad: bytes,
    *,
    version: int = VERSION,
) -> dict[str, Any]:
    client_public_key = _decode_public_key(client_public_key_b64)
    server_private_key = ec.generate_private_key(ec.SECP256R1())
    shared_secret = server_private_key.exchange(ec.ECDH(), client_public_key)
    salt = os.urandom(16)
    key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=INFO,
    ).derive(shared_secret)
    iv = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(iv, payload, aad)
    server_public_raw = server_private_key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return {
        "encrypted": True,
        "v": version,
        "alg": ALG,
        "server_public_key": _b64(server_public_raw),
        "salt": _b64(salt),
        "iv": _b64(iv),
        "ciphertext": _b64(ciphertext),
    }


def get_client_public_key(request) -> Optional[str]:
    value = request.headers.get("x-content-pubkey")
    return value.strip() if value else None
