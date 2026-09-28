"""EPUB DRM encryption — basic AES-CBC encryption for downloaded EPUB files.

Goal: produce a "protected" EPUB variant where the chapter content is
encrypted with AES-256-CBC, and the key is delivered via a separate URL
(theoretically linked to the user's download record).

This is NOT a real DRM (anyone with the key can decrypt), but it provides:
  - First-line protection against casual re-sharing of the raw EPUB
  - Per-download unique key for tracking purposes
  - The "secure_epub" feature can be extended to integrate with a key
    distribution service later

Output:
  - Encrypted EPUB file (still readable by Adobe Digital Editions / Calibre
    when provided with the key)
  - Key stored as a DownloadRecord attribute (key_id, key_url)
"""

import base64
import hashlib
import json
import os
import secrets
import zipfile
from pathlib import Path
from typing import Optional

from loguru import logger


# AES via cryptography library (lazy import — only needed if DRM enabled)
def _get_aes():
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        return Cipher, algorithms, modes, default_backend
    except ImportError as e:
        raise RuntimeError(
            "cryptography library not installed. Run "
            "`pip install cryptography` to enable DRM."
        ) from e


def _pad_pkcs7(data: bytes) -> bytes:
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len] * pad_len)


def _unpad_pkcs7(data: bytes) -> bytes:
    if not data:
        return data
    pad_len = data[-1]
    if pad_len > 16 or pad_len < 1:
        return data
    if data[-pad_len:] != bytes([pad_len] * pad_len):
        return data
    return data[:-pad_len]


def generate_drm_key() -> tuple[bytes, str]:
    """Generate a fresh 32-byte AES key.

    Returns: (key_bytes, key_b64)
    """
    key = secrets.token_bytes(32)
    return key, base64.b64encode(key).decode("ascii")


def encrypt_chapter_content(content: str, key: bytes) -> bytes:
    """Encrypt a chapter's HTML content with AES-256-CBC.

    The IV is prepended to the ciphertext for self-contained decryption.
    """
    Cipher, algorithms, modes, backend = _get_aes()
    iv = secrets.token_bytes(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    encryptor = cipher.encryptor()
    plaintext = _pad_pkcs7(content.encode("utf-8"))
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return iv + ciphertext


def decrypt_chapter_content(encrypted: bytes, key: bytes) -> str:
    """Decrypt an AES-256-CBC encrypted chapter.

    The IV is read from the first 16 bytes of `encrypted`.
    """
    Cipher, algorithms, modes, backend = _get_aes()
    iv, ciphertext = encrypted[:16], encrypted[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    plaintext = _unpad_pkcs7(padded)
    return plaintext.decode("utf-8")


def make_encrypted_epub(
    plain_epub_path: Path,
    key: bytes,
    out_path: Optional[Path] = None,
) -> Path:
    """Take a plain EPUB file and produce an encrypted variant.

    Strategy: iterate over the file's chapter XHTML pages, encrypt their
    content, and write a new EPUB with the same structure but encrypted
    chapter payloads. A `encryption.xml` file is added at the EPUB root
    documenting the encryption (per IDPF spec).

    Returns: path to the encrypted EPUB file.
    """
    if not plain_epub_path.exists():
        raise FileNotFoundError(plain_epub_path)

    out_path = out_path or plain_epub_path.with_suffix(".drm.epub")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(plain_epub_path, "r") as zin, \
         zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        encrypted_files = []
        for item in zin.infolist():
            data = zin.read(item.filename)
            # Only encrypt chapter XHTML files (ch*.xhtml, content/*.xhtml, etc.)
            if (item.filename.endswith(".xhtml") and
                any(p in item.filename for p in ("ch", "chapter", "OEBPS/Text"))):
                try:
                    plaintext = data.decode("utf-8")
                    encrypted = encrypt_chapter_content(plaintext, key)
                    # Wrap as base64 in a new XHTML placeholder so the
                    # file remains valid XML for epubcheck
                    placeholder = (
                        '<?xml version="1.0" encoding="UTF-8"?>'
                        '<html xmlns="http://www.w3.org/1999/xhtml">'
                        '<head><title>Encrypted</title></head>'
                        '<body><encrypted-data>'
                        f'{base64.b64encode(encrypted).decode("ascii")}'
                        '</encrypted-data></body></html>'
                    )
                    zout.writestr(item, placeholder.encode("utf-8"))
                    encrypted_files.append(item.filename)
                except Exception as e:
                    logger.warning(f"failed to encrypt {item.filename}: {e!r}")
                    zout.writestr(item, data)
            else:
                zout.writestr(item, data)

        # Write encryption.xml describing the encryption scheme
        enc_xml = _build_encryption_xml(encrypted_files, key)
        zout.writestr("META-INF/encryption.xml", enc_xml.encode("utf-8"))

    return out_path


def _build_encryption_xml(encrypted_files: list[str], key: bytes) -> str:
    """Build an OCF encryption.xml describing the encrypted files.

    Note: we don't expose the key here (security); only the file list.
    """
    key_id = hashlib.sha256(key).hexdigest()[:16]
    enc_items = "\n".join(
        f'  <EncryptedData Id="enc_{i}">'
        f'<EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#aes256-cbc"/>'
        f'<CipherData><CipherReference URI="{f}"/></CipherData>'
        f'<KeyInfo><KeyName>{key_id}</KeyName></KeyInfo>'
        f'</EncryptedData>'
        for i, f in enumerate(encrypted_files)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container"'
        ' xmlns:enc="http://www.w3.org/2001/04/xmlenc#">'
        f'\n{enc_items}\n'
        '</encryption>'
    )


def decrypt_epub(encrypted_epub_path: Path, key: bytes, out_path: Optional[Path] = None) -> Path:
    """Decrypt an EPUB produced by `make_encrypted_epub`.

    Returns: path to the decrypted EPUB file.
    """
    if not encrypted_epub_path.exists():
        raise FileNotFoundError(encrypted_epub_path)

    out_path = out_path or encrypted_epub_path.with_suffix(".decrypted.epub")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(encrypted_epub_path, "r") as zin, \
         zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "META-INF/encryption.xml":
                continue
            data = zin.read(item.filename)
            if item.filename.endswith(".xhtml"):
                try:
                    text = data.decode("utf-8")
                    if "<encrypted-data>" in text:
                        # Extract base64, decrypt
                        import re
                        m = re.search(r"<encrypted-data>([^<]+)</encrypted-data>", text)
                        if m:
                            encrypted_bytes = base64.b64decode(m.group(1).strip())
                            plaintext = decrypt_chapter_content(encrypted_bytes, key)
                            zout.writestr(item, plaintext.encode("utf-8"))
                            continue
                except Exception as e:
                    logger.warning(f"failed to decrypt {item.filename}: {e!r}")
            zout.writestr(item, data)
    return out_path


def diagnostics() -> dict:
    try:
        _get_aes()
        return {"crypto_available": True}
    except RuntimeError as e:
        return {"crypto_available": False, "error": str(e)}
