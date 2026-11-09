import time
import secrets
import logging
import threading
from typing import Dict, Set, Optional, Any, List
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError
from config import settings

logger = logging.getLogger("menkopolkam.security")

PERMITTED_JWT_ALGORITHMS: Set[str] = {"HS256", "RS256"}

class AuthenticationError(Exception):
    """Base class for authentication and security errors."""
    pass

class SecurityError(AuthenticationError):
    """Raised when security invariant or configuration fails."""
    pass

class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""
    pass

class InvalidSignatureError(AuthenticationError):
    """Raised when JWT signature or algorithm is invalid."""
    pass

class InvalidClaimsError(AuthenticationError):
    """Raised when JWT claims (audience, issuer, etc.) are invalid."""
    pass

def create_access_token(
    sub: str,
    role: str = "operator",
    expires_delta_seconds: Optional[int] = None,
    aud: Optional[str] = None,
    iss: Optional[str] = None,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None
) -> str:
    """
    Mints a standard JWT access token for authentication testing or internal IdP integration.
    Default duration is 4 hours (14,400 seconds) as configured in settings.
    Never logs the token payload or secrets.
    """
    now = int(time.time())
    ttl = expires_delta_seconds if expires_delta_seconds is not None else getattr(settings, "ACCESS_TOKEN_EXPIRE_SECONDS", 14400)
    payload: Dict[str, Any] = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "iss": iss or settings.JWT_ISSUER,
        "aud": aud or settings.JWT_AUDIENCE
    }
    key = secret_key or settings.JWT_SECRET_KEY
    algo = algorithm or settings.JWT_ALGORITHM
    if algo not in PERMITTED_JWT_ALGORITHMS:
        raise InvalidSignatureError(f"Cannot mint token with unpermitted algorithm '{algo}'.")
    return jwt.encode(payload, key, algorithm=algo)

def verify_access_token(
    token: str,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
    audience: Optional[str] = None,
    issuer: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates signature, expiration, issuer, audience, and permitted algorithm.
    Explicitly guards against algorithm confusion, 'none' algorithm, and weak secrets.
    Throws specific AuthenticationError subclasses on failure.
    """
    if not token or not isinstance(token, str):
        raise AuthenticationError("Token must be a non-empty string.")

    key = secret_key or settings.JWT_SECRET_KEY
    algo = algorithm or settings.JWT_ALGORITHM
    aud = audience or settings.JWT_AUDIENCE
    iss = issuer or settings.JWT_ISSUER

    # 1. Permitted Algorithm Whitelist Defense
    if algo not in PERMITTED_JWT_ALGORITHMS:
        raise InvalidSignatureError(f"Algorithm '{algo}' is not permitted. Permitted: {sorted(PERMITTED_JWT_ALGORITHMS)}")

    # 2. Prevent Algorithm Confusion / 'none' Algorithm via Unverified Header Inspection
    try:
        header = jwt.get_unverified_header(token)
        token_alg = header.get("alg")
        if not token_alg or token_alg.lower() == "none":
            raise InvalidSignatureError("Unsigned tokens ('alg': 'none') are strictly forbidden.")
        if token_alg != algo:
            raise InvalidSignatureError(
                f"Algorithm confusion detected: token declared '{token_alg}' but system requires '{algo}'."
            )
    except Exception as e:
        if isinstance(e, InvalidSignatureError):
            raise
        raise AuthenticationError(f"Malformed JWT header: {e}")

    # 3. Validate Secret Strength in Protected Environments
    if settings.ENV in ("staging", "production") and (not key or len(key) < 32 or "insecure" in key.lower()):
        raise SecurityError("Unsafe, weak, or missing JWT_SECRET_KEY in non-development environment.")

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[algo],
            audience=aud if aud else None,
            issuer=iss if iss else None,
            options={"verify_exp": True, "verify_aud": bool(aud), "verify_iss": bool(iss)}
        )
        sub = payload.get("sub")
        if not sub:
            raise InvalidClaimsError("Token payload missing required 'sub' (subject) claim.")
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired.")
    except JWTClaimsError as e:
        raise InvalidClaimsError(f"Token claims validation failed: {e}")
    except JWTError as e:
        raise InvalidSignatureError(f"Invalid token signature or formatting: {e}")
    except Exception as e:
        raise AuthenticationError(f"Authentication validation failed: {e}")


class ConnectionTicketManager:
    """
    Manages single-use, short-lived (default 60s) WebSocket connection tickets.
    Protected with a threading.Lock to eliminate race conditions during concurrent redemption.
    Guarantees replay protection by strictly invalidating ticket upon redemption.
    """
    def __init__(self):
        self._tickets: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_ticket(
        self,
        user_id: str,
        role: str = "operator",
        scopes: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None
    ) -> str:
        with self._lock:
            self._cleanup_expired_tickets_unlocked()
            ttl = ttl_seconds if ttl_seconds is not None else settings.TICKET_TTL_SECONDS
            ticket = secrets.token_urlsafe(32)
            now = time.time()
            self._tickets[ticket] = {
                "user_id": user_id,
                "role": role,
                "scopes": scopes or [],
                "created_at": now,
                "expires_at": now + ttl,
                "redeemed": False
            }
            return ticket

    def redeem_ticket(self, ticket: str) -> Optional[Dict[str, Any]]:
        """
        Redeems ticket atomically under lock. If valid and unexpired, immediately deletes it
        so it cannot be replayed or claimed concurrently by racing requests.
        """
        if not ticket:
            return None

        with self._lock:
            if ticket not in self._tickets:
                return None

            ticket_data = self._tickets.pop(ticket)  # Atomic single-use removal
            now = time.time()
            if now > ticket_data["expires_at"]:
                return None  # Expired

            return {
                "user_id": ticket_data["user_id"],
                "role": ticket_data["role"],
                "scopes": ticket_data["scopes"]
            }

    def cleanup_expired_tickets(self) -> None:
        with self._lock:
            self._cleanup_expired_tickets_unlocked()

    def _cleanup_expired_tickets_unlocked(self) -> None:
        now = time.time()
        expired = [t for t, data in self._tickets.items() if now > data["expires_at"]]
        for t in expired:
            self._tickets.pop(t, None)



class HandshakeAbuseTracker:
    """
    Tracks failed handshake attempts per client IP within a sliding window.
    Protects against unauthenticated brute force and connection flooding.
    """
    def __init__(self):
        self._failures: Dict[str, List[float]] = {}

    def record_failure(self, client_ip: str, window_seconds: int = 60, max_failures: Optional[int] = None) -> bool:
        limit = max_failures if max_failures is not None else settings.MAX_FAILED_HANDSHAKES_PER_IP
        now = time.time()
        history = self._failures.setdefault(client_ip, [])
        # Prune old timestamps
        history = [ts for ts in history if now - ts < window_seconds]
        history.append(now)
        self._failures[client_ip] = history
        return len(history) >= limit

    def is_blocked(self, client_ip: str, window_seconds: int = 60, max_failures: Optional[int] = None) -> bool:
        limit = max_failures if max_failures is not None else settings.MAX_FAILED_HANDSHAKES_PER_IP
        now = time.time()
        history = self._failures.get(client_ip, [])
        valid_history = [ts for ts in history if now - ts < window_seconds]
        self._failures[client_ip] = valid_history
        return len(valid_history) >= limit

    def reset(self, client_ip: str) -> None:
        self._failures.pop(client_ip, None)


class PerUserConnectionTracker:
    """
    Tracks active WebSocket connections per authenticated user.
    Enforces configurable limit (MAX_CONCURRENT_SESSIONS_PER_USER).
    """
    def __init__(self):
        self._user_sessions: Dict[str, Set[str]] = {}

    def can_connect(self, user_id: str, max_concurrent: Optional[int] = None) -> bool:
        limit = max_concurrent if max_concurrent is not None else settings.MAX_CONCURRENT_SESSIONS_PER_USER
        active = self._user_sessions.get(user_id, set())
        return len(active) < limit

    def register_connection(self, user_id: str, session_id: str) -> None:
        sessions = self._user_sessions.setdefault(user_id, set())
        sessions.add(session_id)

    def unregister_connection(self, user_id: str, session_id: str) -> None:
        if user_id in self._user_sessions:
            self._user_sessions[user_id].discard(session_id)
            if not self._user_sessions[user_id]:
                self._user_sessions.pop(user_id, None)

    def get_active_count(self, user_id: str) -> int:
        return len(self._user_sessions.get(user_id, set()))


class WindowedRateLimiter:
    """
    In-memory sliding window rate limiter for expensive operations (provider switching, query analysis).
    NOTE: Operates in-memory per process. In a multi-worker deployment, a shared Redis store is required.
    """
    def __init__(self):
        self._events: Dict[str, List[float]] = {}

    def check_and_record(self, key: str, max_requests: int, window_seconds: float) -> bool:
        now = time.time()
        history = self._events.setdefault(key, [])
        valid = [t for t in history if now - t < window_seconds]
        if len(valid) >= max_requests:
            self._events[key] = valid
            return False
        valid.append(now)
        self._events[key] = valid
        return True


class ClientIPResolver:
    """
    Extracts real client IP while preventing X-Forwarded-For spoofing.
    Only trusts proxy headers when the direct peer IP is in settings.TRUSTED_PROXIES.
    """
    @staticmethod
    def resolve_client_ip(headers: Dict[str, str], direct_host: str) -> str:
        clean_direct = (direct_host or "").strip()
        trusted = set(settings.TRUSTED_PROXIES)

        if clean_direct in trusted:
            # Check X-Forwarded-For
            xff = headers.get("x-forwarded-for")
            if xff:
                # The first IP in the list is the original client
                parts = [p.strip() for p in xff.split(",") if p.strip()]
                if parts:
                    return parts[0]
            # Check X-Real-IP
            x_real = headers.get("x-real-ip")
            if x_real:
                return x_real.strip()

        return clean_direct or "127.0.0.1"


# Global instances for the backend process
ticket_manager = ConnectionTicketManager()
handshake_tracker = HandshakeAbuseTracker()
user_tracker = PerUserConnectionTracker()
rate_limiter = WindowedRateLimiter()
ip_resolver = ClientIPResolver()
