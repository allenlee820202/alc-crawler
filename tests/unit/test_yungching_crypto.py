"""Unit tests for Yungching AES-CBC decryption."""
from __future__ import annotations

import json
from base64 import b64encode

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from alc_crawler.adapters.sites.site_yungching.crypto import (
    _IV,
    _KEY,
    decrypt_response_data,
)


def _encrypt(data: dict[str, object]) -> str:
    """Encrypt a dict using the same AES params for round-trip testing."""
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    padder = PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(_KEY), modes.CBC(_IV))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return b64encode(ciphertext).decode()


class TestDecryptResponseData:
    def test_round_trip(self) -> None:
        original = {"hello": "world", "count": 42}
        encrypted = _encrypt(original)
        result = decrypt_response_data(encrypted)
        assert result == original

    def test_chinese_content(self) -> None:
        original = {"name": "大安區精美住宅", "tags": ["近捷運"]}
        encrypted = _encrypt(original)
        result = decrypt_response_data(encrypted)
        assert result["name"] == "大安區精美住宅"

    def test_invalid_base64_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid base64"):
            decrypt_response_data("not-valid-base64!!!")

    def test_invalid_ciphertext_raises(self) -> None:
        # Valid base64 but not valid AES ciphertext
        with pytest.raises((ValueError, Exception)):
            decrypt_response_data(b64encode(b"short").decode())
