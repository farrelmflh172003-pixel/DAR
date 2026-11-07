import asyncio
import random
import logging
from enum import Enum
from typing import Optional, Tuple, Callable, Any, Dict

logger = logging.getLogger("menkopolkam.resilience")

class ProviderErrorCategory(str, Enum):
    QUOTA_EXHAUSTED = "quota_exhausted"
    AUTH_FAILED = "auth_failed"
    PERMISSION_DENIED = "permission_denied"
    TRANSIENT_OUTAGE = "transient_outage"
    BAD_REQUEST = "bad_request"
    UNKNOWN = "unknown"

def classify_provider_error(
    status_code: Optional[int] = None,
    error_code: Optional[str] = None,
    raw_message: str = "",
    provider_name: str = "Provider"
) -> Tuple[ProviderErrorCategory, bool, str]:
    """
    Classifies external provider errors and determines whether they are safely retryable.
    Returns: (category, is_retryable, actionable_user_message)
    """
    msg_lower = (raw_message or "").lower()
    code_lower = (error_code or "").lower()

    # 1. Quota Exhaustion (Non-retryable)
    if (
        status_code == 429 or
        code_lower in ("credit_balance_exhausted", "insufficient_quota", "resource_exhausted") or
        "quota" in msg_lower or
        "credit_balance_exhausted" in msg_lower or
        "rate limit" in msg_lower
    ):
        category = ProviderErrorCategory.QUOTA_EXHAUSTED
        is_retryable = False
        actionable_msg = (
            f"Layanan {provider_name} mencapai batas kuota (Quota Exhausted / HTTP 429). "
            f"Kredit API habis atau rate limit tercapai. Harap periksa tagihan dan kuota akun."
        )
        return category, is_retryable, actionable_msg

    # 2. Authentication Failure (Non-retryable)
    if (
        status_code == 401 or
        code_lower in ("invalid_api_key", "unauthenticated", "invalid_token") or
        "api key" in msg_lower or
        "unauthorized" in msg_lower or
        "authentication" in msg_lower
    ):
        category = ProviderErrorCategory.AUTH_FAILED
        is_retryable = False
        actionable_msg = f"Autentikasi {provider_name} gagal: API Key tidak valid atau tidak memiliki otorisasi."
        return category, is_retryable, actionable_msg

    # 3. Permission Denied / Policy Violation (Non-retryable)
    if (
        status_code == 403 or
        code_lower in ("permission_denied", "access_denied") or
        "permission" in msg_lower or
        "policy" in msg_lower or
        "forbidden" in msg_lower
    ):
        category = ProviderErrorCategory.PERMISSION_DENIED
        is_retryable = False
        actionable_msg = f"Akses {provider_name} ditolak (Permission Denied): Model memerlukan whitelisting atau izin khusus."
        return category, is_retryable, actionable_msg

    # 4. Transient Outage / Network Timeout (Safe to retry with bounded backoff)
    if (
        status_code in (500, 502, 503, 504) or
        "timeout" in msg_lower or
        "timed out" in msg_lower or
        "connection refused" in msg_lower or
        "network" in msg_lower or
        "unavailable" in msg_lower
    ):
        category = ProviderErrorCategory.TRANSIENT_OUTAGE
        is_retryable = True
        actionable_msg = f"Gangguan sementara pada jaringan/server {provider_name} (HTTP {status_code or 'Timeout'})."
        return category, is_retryable, actionable_msg

    # 5. Bad Request / Client Error (Non-retryable)
    if status_code in (400, 404, 422):
        category = ProviderErrorCategory.BAD_REQUEST
        is_retryable = False
        actionable_msg = f"Parameter permintaan ke {provider_name} tidak valid (HTTP {status_code})."
        return category, is_retryable, actionable_msg

    # Default Unknown
    return ProviderErrorCategory.UNKNOWN, False, f"Terjadi kesalahan pada {provider_name}: {raw_message[:100]}"


async def execute_with_bounded_retry(
    operation: Callable[[], Any],
    provider_name: str = "Provider",
    max_retries: int = 2,
    base_delay: float = 0.5,
    max_delay: float = 2.0
) -> Tuple[bool, Any, Optional[str]]:
    """
    Executes an async operation with bounded exponential backoff and jitter.
    Strictly forbids retrying non-retryable errors (401, 403, 429).
    Returns: (success, result, error_message)
    """
    last_err_msg = ""
    for attempt in range(max_retries + 1):
        try:
            res = await operation()
            return True, res, None
        except Exception as e:
            raw_err = str(e)
            category, is_retryable, actionable = classify_provider_error(
                raw_message=raw_err,
                provider_name=provider_name
            )
            last_err_msg = actionable

            if not is_retryable or attempt >= max_retries:
                logger.warning(
                    f"[{provider_name}] Non-retryable or max retries exceeded on attempt {attempt + 1}: {actionable}"
                )
                return False, None, actionable

            # Exponential backoff with random jitter
            delay = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0.05, 0.2)
            logger.info(f"[{provider_name}] Transient error ({category}). Retrying in {delay:.2f}s (Attempt {attempt + 1}/{max_retries})...")
            await asyncio.sleep(delay)

    return False, None, last_err_msg
