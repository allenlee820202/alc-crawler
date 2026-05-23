"""AES-CBC decryption for Yungching /api/v2/list responses.

Yungching's BFF wraps the JSON payload in AES-256-CBC encryption.
Key derivation:
  1. SHA-256 hash the passphrase "YungChing.Buy" to get raw bytes
  2. PBKDF2 (SHA-1, salt=[2,7,0,5,1,3,8,0], 1000 iterations) -> 48 bytes
  3. First 32 bytes = AES key, bytes 32-48 = IV
  4. AES-CBC decrypt + PKCS7 unpad -> UTF-8 JSON
"""
from __future__ import annotations

import hashlib
import json
from base64 import b64decode
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.padding import PKCS7

_PASSPHRASE = "YungChing.Buy"
_SALT = bytes([2, 7, 0, 5, 1, 3, 8, 0])
_ITERATIONS = 1000
_KEY_MATERIAL_LENGTH = 48  # 32 key + 16 IV


def _derive_key_iv() -> tuple[bytes, bytes]:
    """Derive AES-256 key and IV from the fixed passphrase."""
    password = hashlib.sha256(_PASSPHRASE.encode()).digest()
    kdf = PBKDF2HMAC(
        algorithm=SHA1(),
        length=_KEY_MATERIAL_LENGTH,
        salt=_SALT,
        iterations=_ITERATIONS,
    )
    material = kdf.derive(password)
    return material[:32], material[32:48]


# Pre-compute on import — passphrase is static.
_KEY, _IV = _derive_key_iv()


def decrypt_response_data(encrypted_b64: str) -> dict[str, Any]:
    """Decrypt the AES-CBC-encrypted 'data' field from the API response.

    Returns the parsed JSON dict.
    Raises ValueError on decryption or JSON parse failure.
    """
    try:
        ciphertext = b64decode(encrypted_b64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 in response data: {exc}") from exc

    cipher = Cipher(algorithms.AES(_KEY), modes.CBC(_IV))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()

    try:
        return json.loads(plaintext.decode("utf-8"))  # type: ignore[no-any-return]
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Decrypted payload is not valid JSON: {exc}") from exc
