"""AES-256-GCM and AES-256-CBC encryption for Sensitive and More Sensitive data."""

from __future__ import annotations

import logging
import os
import secrets

from xeren.security.schemas import DataSensitivityTier, EncryptedBlob

logger = logging.getLogger("xeren.security.encryption")

# PBKDF2 iteration counts — higher = slower brute-force, per NIST 2023
_ITERATIONS: dict[DataSensitivityTier, int] = {
    DataSensitivityTier.SENSITIVE: 100_000,
    DataSensitivityTier.MORE_SENSITIVE: 600_000,
}


def _derive_key(passphrase: str, salt: bytes, iterations: int) -> bytes:
    """Derive a 256-bit key using PBKDF2-HMAC-SHA256."""
    import hashlib
    return hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=passphrase.encode("utf-8"),
        salt=salt,
        iterations=iterations,
        dklen=32,
    )


class XerenEncryption:
    """
    Encryption engine for Xeren's 3-tier data protection.

    Tiers:
      LIBERAL       → No encryption (fast path)
      SENSITIVE     → AES-256-CBC (fast, file-level)
      MORE_SENSITIVE → AES-256-GCM (authenticated encryption, integrity tag)
    """

    # ------------------------------------------------------------------
    # Encrypt
    # ------------------------------------------------------------------

    def encrypt(
        self,
        data: bytes,
        tier: DataSensitivityTier,
        passphrase: str,
    ) -> EncryptedBlob:
        """
        Encrypt data according to the sensitivity tier.

        Args:
            data: Raw plaintext bytes.
            tier: Sensitivity tier determining algorithm.
            passphrase: User passphrase (PIN-derived or session key).

        Returns:
            EncryptedBlob with all metadata needed for decryption.
        """
        if tier == DataSensitivityTier.LIBERAL:
            raise ValueError("Liberal tier data does not require encryption.")

        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
        except ImportError as err:
            raise RuntimeError(
                "cryptography package required for encryption. "
                "Install with: pip install cryptography"
            ) from err

        salt = secrets.token_bytes(32)
        iterations = _ITERATIONS[tier]
        key = _derive_key(passphrase, salt, iterations)

        if tier == DataSensitivityTier.MORE_SENSITIVE:
            # AES-256-GCM: authenticated encryption with integrity tag
            iv = secrets.token_bytes(12)  # 96-bit nonce for GCM
            encryptor = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=default_backend(),
            ).encryptor()
            ciphertext = encryptor.update(data) + encryptor.finalize()
            tag = encryptor.tag  # 16-byte authentication tag

            return EncryptedBlob(
                algorithm="AES-256-GCM",
                ciphertext=ciphertext,
                iv=iv,
                salt=salt,
                tag=tag,
                tier=tier,
                iterations=iterations,
            )

        else:
            # AES-256-CBC: fast, file-level encryption for Sensitive tier
            iv = secrets.token_bytes(16)  # 128-bit IV for CBC
            # PKCS7 padding
            pad_len = 16 - (len(data) % 16)
            padded = data + bytes([pad_len] * pad_len)

            encryptor = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend(),
            ).encryptor()
            ciphertext = encryptor.update(padded) + encryptor.finalize()

            return EncryptedBlob(
                algorithm="AES-256-CBC",
                ciphertext=ciphertext,
                iv=iv,
                salt=salt,
                tag=None,
                tier=tier,
                iterations=iterations,
            )

    # ------------------------------------------------------------------
    # Decrypt
    # ------------------------------------------------------------------

    def decrypt(
        self,
        blob: EncryptedBlob,
        passphrase: str,
    ) -> bytes:
        """
        Decrypt an EncryptedBlob back to plaintext bytes.

        Args:
            blob: The encrypted blob (from encrypt()).
            passphrase: The same passphrase used during encryption.

        Returns:
            Raw plaintext bytes.

        Raises:
            ValueError: If GCM authentication tag fails (data tampered).
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            from cryptography.exceptions import InvalidTag
        except ImportError as err:
            raise RuntimeError("cryptography package required.") from err

        key = _derive_key(passphrase, blob.salt, blob.iterations)

        if blob.algorithm == "AES-256-GCM":
            if not blob.tag:
                raise ValueError("GCM blob missing authentication tag.")
            try:
                decryptor = Cipher(
                    algorithms.AES(key),
                    modes.GCM(blob.iv, blob.tag),
                    backend=default_backend(),
                ).decryptor()
                return decryptor.update(blob.ciphertext) + decryptor.finalize()
            except InvalidTag as err:
                raise ValueError(
                    "GCM authentication failed — data may have been tampered with."
                ) from err

        elif blob.algorithm == "AES-256-CBC":
            decryptor = Cipher(
                algorithms.AES(key),
                modes.CBC(blob.iv),
                backend=default_backend(),
            ).decryptor()
            padded = decryptor.update(blob.ciphertext) + decryptor.finalize()
            # Remove PKCS7 padding
            pad_len = padded[-1]
            return padded[:-pad_len]

        else:
            raise ValueError(f"Unknown encryption algorithm: {blob.algorithm}")

    # ------------------------------------------------------------------
    # Convenience: encrypt/decrypt strings
    # ------------------------------------------------------------------

    def encrypt_text(self, text: str, tier: DataSensitivityTier, passphrase: str) -> EncryptedBlob:
        return self.encrypt(text.encode("utf-8"), tier, passphrase)

    def decrypt_text(self, blob: EncryptedBlob, passphrase: str) -> str:
        return self.decrypt(blob, passphrase).decode("utf-8")


__all__ = ["XerenEncryption"]
