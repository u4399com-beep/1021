"""Captcha recognition integration — 2captcha + local OCR fallback.

Goal: when a crawler task encounters a WAF captcha (e.g., cunshu.la's
GoEdge WAF), automatically solve it.

Strategy:
  1. If CAPTCHA_2CAPTCHA_KEY is configured, send the captcha image to 2captcha
     and poll for the solution (5-30s typical).
  2. Fallback: try pytesseract (Tesseract OCR) if installed locally — useful
     for simple character captchas.
  3. If neither is available, raise an exception and let the task fall through
     to the next tier.
"""
from __future__ import annotations

import base64
import time
from typing import Optional

from django.conf import settings
from loguru import logger


def is_2captcha_configured() -> bool:
    return bool(settings.CRAWLER.get("CAPTCHA_2CAPTCHA_KEY", ""))


def is_ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        return True
    except ImportError:
        return False


# ------------------------------------------------------------------
# 2captcha backend
# ------------------------------------------------------------------
def solve_with_2captcha(image_bytes: bytes, *, timeout: int = 120) -> Optional[str]:
    """Submit a captcha image to 2captcha and poll for the solution.

    Returns the solved text, or None on timeout/error.
    """
    import httpx

    api_key = settings.CRAWLER.get("CAPTCHA_2CAPTCHA_KEY", "")
    if not api_key:
        return None

    endpoint = settings.CRAWLER.get("CAPTCHA_2CAPTCHA_ENDPOINT", "https://2captcha.com/in.php")
    res_endpoint = "https://2captcha.com/res.php"

    # Submit
    b64 = base64.b64encode(image_bytes).decode("ascii")
    try:
        r = httpx.post(endpoint, data={
            "key": api_key,
            "method": "base64",
            "body": b64,
            "json": 1,
        }, timeout=30)
        if r.status_code != 200:
            logger.warning(f"2captcha submit failed: {r.status_code}")
            return None
        data = r.json()
        if data.get("status") != 1:
            logger.warning(f"2captcha submit error: {data}")
            return None
        captcha_id = data.get("request")
    except Exception as e:
        logger.warning(f"2captcha submit exception: {e!r}")
        return None

    # Poll for result
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(5)
        try:
            r = httpx.get(res_endpoint, params={
                "key": api_key, "action": "get", "id": captcha_id, "json": 1,
            }, timeout=15)
            data = r.json()
            if data.get("status") == 1:
                return data.get("request")
            if data.get("request") != "CAPCHA_NOT_READY":
                logger.warning(f"2captcha poll error: {data}")
                return None
        except Exception as e:
            logger.warning(f"2captcha poll exception: {e!r}")
    return None


# ------------------------------------------------------------------
# Local OCR fallback
# ------------------------------------------------------------------
def solve_with_ocr(image_bytes: bytes) -> Optional[str]:
    """Run Tesseract OCR on the captcha image.

    Works for simple 4-6 character alphanumeric captchas. Less reliable
    for distorted/colored captchas.
    """
    try:
        import pytesseract
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        # Convert to grayscale + upscale for better OCR
        img = img.convert("L")
        text = pytesseract.image_to_string(img, config="--psm 7 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        return text.strip()
    except Exception as e:
        logger.warning(f"OCR failed: {e!r}")
        return None


# ------------------------------------------------------------------
# Master solver
# ------------------------------------------------------------------
def solve_captcha(image_bytes: bytes, *, prefer: str = "2captcha") -> Optional[str]:
    """Try the preferred backend first, then fallback.

    Args:
        image_bytes: PNG/JPG bytes of the captcha image
        prefer: "2captcha" or "ocr"

    Returns: solved text, or None on failure
    """
    if prefer == "2captcha":
        if is_2captcha_configured():
            result = solve_with_2captcha(image_bytes)
            if result:
                return result
        # Fallback to OCR
        if is_ocr_available():
            return solve_with_ocr(image_bytes)
    else:
        if is_ocr_available():
            result = solve_with_ocr(image_bytes)
            if result:
                return result
        if is_2captcha_configured():
            return solve_with_2captcha(image_bytes)
    return None


def diagnostics() -> dict:
    return {
        "2captcha_configured": is_2captcha_configured(),
        "ocr_available": is_ocr_available(),
    }
