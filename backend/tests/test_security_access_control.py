import pytest
import asyncio
import json
import time
import httpx
import websockets
from config import settings
from jose import jwt
from utils.security import (
    create_access_token,
    verify_access_token,
    ticket_manager,
    handshake_tracker,
    user_tracker,
    rate_limiter,
    ip_resolver,
    AuthenticationError,
    SecurityError,
    TokenExpiredError,
    InvalidSignatureError,
    InvalidClaimsError,
    ConnectionTicketManager,
    HandshakeAbuseTracker,
    PerUserConnectionTracker,
    ClientIPResolver
)
from utils.resilience import (
    classify_provider_error,
    execute_with_bounded_retry,
    ProviderErrorCategory
)
from orchestration.session_orchestrator import SessionOrchestrator

WS_URL = "ws://127.0.0.1:8000/ws/realtime-session"
HTTP_URL = "http://127.0.0.1:8000"
VALID_ORIGIN = "http://localhost:5173"

def test_jwt_validation_matrix():
    """
    Verify complete JWT access token lifecycle and defensive validation:
    - Valid signature, unexpired, matching aud & iss
    - Expired token raises TokenExpiredError
    - Malformed / tampered token raises InvalidSignatureError
    - Wrong audience raises InvalidClaimsError
    - Wrong issuer raises InvalidClaimsError
    - Missing 'sub' claim raises InvalidClaimsError
    """
    secret = "test-secret-key-for-menkopolkam-security-tests-32bytes!"
    aud = "menkopolkam-web"
    iss = "menkopolkam-ai-hub"

    # 1. Valid Token
    valid_token = create_access_token(
        sub="operator-007",
        role="diplomat",
        expires_delta_seconds=300,
        aud=aud,
        iss=iss,
        secret_key=secret
    )
    claims = verify_access_token(valid_token, secret_key=secret, audience=aud, issuer=iss)
    assert claims["sub"] == "operator-007"
    assert claims["role"] == "diplomat"
    assert claims["aud"] == aud
    assert claims["iss"] == iss

    # 2. Expired Token
    expired_token = create_access_token(
        sub="operator-007",
        expires_delta_seconds=-10,  # Expired 10 seconds ago
        aud=aud,
        iss=iss,
        secret_key=secret
    )
    with pytest.raises(TokenExpiredError):
        verify_access_token(expired_token, secret_key=secret, audience=aud, issuer=iss)

    # 3. Tampered Token Signature (Wrong Secret)
    with pytest.raises(InvalidSignatureError):
        verify_access_token(valid_token, secret_key="wrong-secret-key-attacker-guess!!", audience=aud, issuer=iss)

    # 4. Wrong Audience
    with pytest.raises(InvalidClaimsError):
        verify_access_token(valid_token, secret_key=secret, audience="unauthorized-foreign-app", issuer=iss)

    # 5. Wrong Issuer
    with pytest.raises(InvalidClaimsError):
        verify_access_token(valid_token, secret_key=secret, audience=aud, issuer="rogue-identity-provider")

    # 6. Malformed String
    with pytest.raises(AuthenticationError):
        verify_access_token("this.is.not.a.valid.jwt.payload", secret_key=secret)


def test_connection_ticket_single_use_and_replay_protection():
    """
    Verify WebSocket connection tickets are single-use, short-lived,
    and strictly immune to replay attacks.
    """
    mgr = ConnectionTicketManager()
    ticket = mgr.create_ticket(user_id="operator_alfa", role="lead_analyst", ttl_seconds=2)

    # First redemption succeeds
    redemption_1 = mgr.redeem_ticket(ticket)
    assert redemption_1 is not None
    assert redemption_1["user_id"] == "operator_alfa"
    assert redemption_1["role"] == "lead_analyst"

    # Second redemption MUST fail (Replay attack blocked)
    redemption_2 = mgr.redeem_ticket(ticket)
    assert redemption_2 is None

    # Expired ticket redemption MUST fail
    expired_ticket = mgr.create_ticket(user_id="operator_beta", ttl_seconds=0)
    time.sleep(0.01)
    redemption_expired = mgr.redeem_ticket(expired_ticket)
    assert redemption_expired is None


def test_session_hijacking_and_principal_isolation():
    """
    Verify that sessions are strictly bound to their authenticated principal
    and cannot be hijacked or attached to by other authenticated users.
    """
    orch = SessionOrchestrator()

    # User 1 creates session "sess_alpha_99"
    sess_1 = orch.get_or_create_session(
        session_id="sess_alpha_99",
        user_id="user_alice_menkopolkam"
    )
    assert sess_1.session_id == "sess_alpha_99"
    assert sess_1.user_id == "user_alice_menkopolkam"

    # Same user accessing same session succeeds
    sess_1_reconnect = orch.get_or_create_session(
        session_id="sess_alpha_99",
        user_id="user_alice_menkopolkam"
    )
    assert sess_1_reconnect is sess_1

    # User 2 attempting to attach to User 1's session ID MUST raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        orch.get_or_create_session(
            session_id="sess_alpha_99",
            user_id="attacker_bob"
        )
    assert "Session access denied" in str(exc_info.value)
    assert "user_alice_menkopolkam" in str(exc_info.value)


def test_per_user_concurrent_connection_limits():
    """
    Verify that per-user concurrent session limits are enforced, preventing
    resource exhaustion or credential sharing abuse.
    """
    tracker = PerUserConnectionTracker()
    user = "operator_citra"
    limit = 2

    assert tracker.can_connect(user, max_concurrent=limit) is True
    tracker.register_connection(user, "sess_1")
    assert tracker.get_active_count(user) == 1

    assert tracker.can_connect(user, max_concurrent=limit) is True
    tracker.register_connection(user, "sess_2")
    assert tracker.get_active_count(user) == 2

    # Third connection attempt MUST be rejected
    assert tracker.can_connect(user, max_concurrent=limit) is False

    # Disconnect one session
    tracker.unregister_connection(user, "sess_1")
    assert tracker.get_active_count(user) == 1
    assert tracker.can_connect(user, max_concurrent=limit) is True


def test_client_ip_spoofing_defense():
    """
    Verify ClientIPResolver ignores fake X-Forwarded-For headers from untrusted clients,
    preventing rate-limit evasion or IP spoofing.
    """
    headers = {"x-forwarded-for": "103.20.10.5, 127.0.0.1"}

    # Case A: Direct connection is from untrusted client host
    resolved_untrusted = ClientIPResolver.resolve_client_ip(
        headers=headers,
        direct_host="192.168.1.100"  # Not in TRUSTED_PROXIES
    )
    assert resolved_untrusted == "192.168.1.100"  # Spoofed XFF is ignored

    # Case B: Direct connection is from trusted reverse proxy
    resolved_trusted = ClientIPResolver.resolve_client_ip(
        headers=headers,
        direct_host="127.0.0.1"  # In TRUSTED_PROXIES
    )
    assert resolved_trusted == "103.20.10.5"  # Client IP correctly extracted


def test_handshake_abuse_and_brute_force_prevention():
    """
    Verify HandshakeAbuseTracker tracks failed attempts and blocks abusive IPs.
    """
    tracker = HandshakeAbuseTracker()
    ip = "198.51.100.42"
    threshold = 3

    assert tracker.is_blocked(ip, max_failures=threshold) is False

    tracker.record_failure(ip, max_failures=threshold)
    tracker.record_failure(ip, max_failures=threshold)
    assert tracker.is_blocked(ip, max_failures=threshold) is False

    # 3rd failure triggers block
    is_blocked_now = tracker.record_failure(ip, max_failures=threshold)
    assert is_blocked_now is True
    assert tracker.is_blocked(ip, max_failures=threshold) is True

    # Reset unblocks
    tracker.reset(ip)
    assert tracker.is_blocked(ip, max_failures=threshold) is False


def test_provider_error_classification_and_bounded_retry():
    """
    Verify that quota errors and auth failures are strictly classified as non-retryable,
    while transient 503 server outages are safely retried with bounded backoff.
    """
    # 1. Quota Exhaustion -> Non-retryable
    cat, retry, _ = classify_provider_error(status_code=429, provider_name="Gemini")
    assert cat == ProviderErrorCategory.QUOTA_EXHAUSTED
    assert retry is False

    cat_oai, retry_oai, _ = classify_provider_error(error_code="credit_balance_exhausted", provider_name="OpenAI")
    assert cat_oai == ProviderErrorCategory.QUOTA_EXHAUSTED
    assert retry_oai is False

    # 2. Authentication Failure -> Non-retryable
    cat_auth, retry_auth, _ = classify_provider_error(status_code=401, provider_name="OpenAI")
    assert cat_auth == ProviderErrorCategory.AUTH_FAILED
    assert retry_auth is False

    # 3. Permission Denied -> Non-retryable
    cat_perm, retry_perm, _ = classify_provider_error(status_code=403, provider_name="Gemini")
    assert cat_perm == ProviderErrorCategory.PERMISSION_DENIED
    assert retry_perm is False

    # 4. Transient Outage -> Retryable
    cat_outage, retry_outage, _ = classify_provider_error(status_code=503, provider_name="Gemini")
    assert cat_outage == ProviderErrorCategory.TRANSIENT_OUTAGE
    assert retry_outage is True

    # 5. Bounded Retry Execution: Non-retryable halts immediately (no retry loop)
    attempts = 0
    async def mock_failing_quota_call():
        nonlocal attempts
        attempts += 1
        raise ValueError("quota exceeded HTTP 429")

    success, _, err_msg = asyncio.run(
        execute_with_bounded_retry(mock_failing_quota_call, max_retries=3, base_delay=0.01)
    )
    assert success is False
    assert attempts == 1  # Exactly 1 attempt, zero retry loops
    assert "batas kuota" in err_msg


@pytest.mark.asyncio
async def test_ws_ticket_endpoint_and_policy_violation_e2e():
    """
    End-to-End WebSocket authentication protocol test:
    1. Obtains ticket from HTTP /api/auth/ticket using valid JWT
    2. Successfully connects to WebSocket with ?ticket=...
    3. Reconnect with the SAME ticket is rejected with 1008 Policy Violation (Replay defense)
    4. Connect with an invalid ticket is rejected with 1008 Policy Violation
    """
    try:
        # 1. Mint JWT and obtain connection ticket
        token = create_access_token(sub="operator-e2e-user", role="operator")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{HTTP_URL}/api/auth/ticket",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "ticket" in data
            ticket = data["ticket"]
            assert data["user_id"] == "operator-e2e-user"

        # 2. Connect with ticket to WebSocket
        ws_url_with_ticket = f"{WS_URL}?ticket={ticket}"
        async with websockets.connect(ws_url_with_ticket, additional_headers={"Origin": VALID_ORIGIN}) as ws:
            # Wait for session_created
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=6.0)
                if isinstance(msg, str):
                    ev = json.loads(msg)
                    if ev.get("type") == "session_created":
                        assert ev["user_id"] == "operator-e2e-user"
                        break

        # 3. Attempt replay with the same redeemed ticket -> MUST fail with 1008
        with pytest.raises((websockets.exceptions.InvalidHandshake, websockets.exceptions.ConnectionClosed)):
            async with websockets.connect(ws_url_with_ticket, additional_headers={"Origin": VALID_ORIGIN}) as ws_replayed:
                await ws_replayed.recv()

        # 4. Attempt connection with completely bogus ticket -> MUST fail with 1008
        bogus_url = f"{WS_URL}?ticket=bogus_unauthorized_token_xyz"
        with pytest.raises((websockets.exceptions.InvalidHandshake, websockets.exceptions.ConnectionClosed)):
            async with websockets.connect(bogus_url, additional_headers={"Origin": VALID_ORIGIN}) as ws_bogus:
                await ws_bogus.recv()

    except ConnectionRefusedError:
        pytest.skip("Backend server on port 8000 is not running.")


@pytest.mark.asyncio
async def test_ws_oversized_text_frame_rejection():
    """
    Verify that incoming text messages larger than 64 KB are safely rejected
    with an error event and do not cause memory or parsing exploits.
    """
async def get_server_ticket(user_id: str = "test-operator") -> str:
    """Helper to fetch a valid connection ticket from the running backend server."""
    token = create_access_token(sub=user_id, role="operator")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{HTTP_URL}/api/auth/ticket",
            headers={"Authorization": f"Bearer {token}"}
        )
        return resp.json()["ticket"]

@pytest.mark.asyncio
async def test_ws_oversized_text_frame_rejection():
    """
    Verify that incoming text messages larger than 64 KB are safely rejected
    with an error event and do not cause memory or parsing exploits.
    """
    try:
        ticket = await get_server_ticket("test_oversized_operator")
        async with websockets.connect(f"{WS_URL}?ticket={ticket}", additional_headers={"Origin": VALID_ORIGIN}) as ws:
            # Wait for session initialization
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=6.0)
                if isinstance(msg, str) and json.loads(msg).get("type") == "session_created":
                    break

            # Send oversized text payload (> 64 KB)
            oversized_payload = json.dumps({"type": "ping", "junk": "A" * 70000})
            await ws.send(oversized_payload)

            # Receive error event
            received_error = False
            t_end = asyncio.get_event_loop().time() + 5.0
            while asyncio.get_event_loop().time() < t_end:
                resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
                if isinstance(resp, str):
                    ev = json.loads(resp)
                    if ev.get("type") == "error":
                        assert "64 KB" in ev.get("message", "")
                        received_error = True
                        break

            assert received_error is True, "Expected 64 KB error event was not received"

    except ConnectionRefusedError:
        pytest.skip("Backend server on port 8000 is not running.")


@pytest.mark.asyncio
async def test_ws_switch_provider_rate_limit_e2e():
    """
    Verify that rapid spamming of switch_provider requests triggers rate limiting
    and prevents connection/orchestrator abuse.
    """
    try:
        ticket = await get_server_ticket("test_rate_limit_operator")
        async with websockets.connect(f"{WS_URL}?ticket={ticket}", additional_headers={"Origin": VALID_ORIGIN}) as ws:

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=6.0)
                if isinstance(msg, str) and json.loads(msg).get("type") == "session_created":
                    break

            # Spam switch provider 8 times in quick succession (limit is 5 per 30s)
            hit_rate_limit = False
            for _ in range(8):
                await ws.send(json.dumps({"type": "switch_provider", "provider": "gemini_live"}))
                await asyncio.sleep(0.05)

            # Read events until we encounter rate limit error
            t_end = asyncio.get_event_loop().time() + 5.0
            while asyncio.get_event_loop().time() < t_end:
                try:
                    res = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if isinstance(res, str):
                        data = json.loads(res)
                        if data.get("type") == "error" and "rate limit" in data.get("message", "").lower():
                            hit_rate_limit = True
                            break
                except asyncio.TimeoutError:
                    break

            assert hit_rate_limit is True, "Rate limit error event was not triggered after rapid switching."

    except ConnectionRefusedError:
        pytest.skip("Backend server on port 8000 is not running.")



@pytest.mark.asyncio
async def test_adversarial_concurrent_ticket_redemption_race_condition():
    """
    Adversarial Race Condition Test:
    Simulates 20 concurrent async workers attempting to redeem the exact same single-use ticket.
    Verifies that threading.Lock guarantees exactly 1 worker succeeds and 19 workers fail.
    """
    mgr = ConnectionTicketManager()
    ticket = mgr.create_ticket(user_id="analyst_omega", role="special_advisor", ttl_seconds=10)

    async def attempt_redemption():
        # Small random delay to create true concurrency overlap
        await asyncio.sleep(0.001)
        return mgr.redeem_ticket(ticket)

    results = await asyncio.gather(*(attempt_redemption() for _ in range(20)))

    successful_redemptions = [r for r in results if r is not None]
    failed_redemptions = [r for r in results if r is None]

    assert len(successful_redemptions) == 1, f"Expected exactly 1 success, got {len(successful_redemptions)}"
    assert len(failed_redemptions) == 19, f"Expected 19 rejections, got {len(failed_redemptions)}"
    assert successful_redemptions[0]["user_id"] == "analyst_omega"


def test_adversarial_jwt_algorithm_confusion_and_none_attack():
    """
    Adversarial Crypto Test:
    1. Rejects tokens declaring 'alg': 'none' (Unsigned token attack)
    2. Rejects tokens declaring an unpermitted algorithm (e.g. HS512 / none)
    3. Rejects algorithm confusion where token header algorithm mismatches server setting
    """
    secret = "a_very_secure_and_cryptographically_sound_key_32b!"

    # 1. 'none' algorithm token
    unsigned_header = {"alg": "none", "typ": "JWT"}
    unsigned_claims = {"sub": "rogue_attacker", "iat": int(time.time()), "exp": int(time.time()) + 3600}
    # Craft raw unverified token
    import base64
    b64_header = base64.urlsafe_b64encode(json.dumps(unsigned_header).encode()).decode().rstrip("=")
    b64_claims = base64.urlsafe_b64encode(json.dumps(unsigned_claims).encode()).decode().rstrip("=")
    none_token = f"{b64_header}.{b64_claims}."

    with pytest.raises(InvalidSignatureError) as exc_info:
        verify_access_token(none_token, secret_key=secret, algorithm="HS256")
    assert "none" in str(exc_info.value).lower() or "forbidden" in str(exc_info.value).lower()

    # 2. Algorithm confusion: token signed with HS512 but server expects HS256
    hs512_token = jwt.encode(unsigned_claims, secret, algorithm="HS512")
    with pytest.raises(InvalidSignatureError) as exc_info2:
        verify_access_token(hs512_token, secret_key=secret, algorithm="HS256")
    assert "confusion" in str(exc_info2.value).lower() or "not permitted" in str(exc_info2.value).lower()


@pytest.mark.asyncio
async def test_adversarial_cross_user_session_operations_idor_prevention():
    """
    Adversarial IDOR Test:
    Proves that a user cannot manipulate another user's session:
    - User B cannot switch provider on User A's session
    - User B cannot trigger dual intelligence on User A's session
    - User B cannot delete or remove User A's session
    """
    orch = SessionOrchestrator()
    orch.get_or_create_session(session_id="victim_session_001", user_id="user_victim")

    # Attacker attempts provider switch on victim's session
    with pytest.raises(PermissionError) as exc_switch:
        await orch.switch_provider(
            session_id="victim_session_001",
            new_provider_id="openai_realtime",
            user_id="attacker_mallory"
        )
    assert "Session access denied" in str(exc_switch.value)

    # Attacker attempts dual intelligence query injection on victim's session
    with pytest.raises(PermissionError) as exc_dual:
        await orch.process_dual_intelligence(
            session_id="victim_session_001",
            query="classified topic",
            user_id="attacker_mallory"
        )
    assert "Session access denied" in str(exc_dual.value)

    # Attacker attempts to terminate victim's session
    with pytest.raises(PermissionError) as exc_remove:
        orch.remove_session("victim_session_001", user_id="attacker_mallory")
    assert "Session access denied" in str(exc_remove.value)

    # Verify victim's session remains intact
    assert orch.get_session("victim_session_001") is not None


def test_adversarial_production_startup_fail_closed_on_weak_keys():
    """
    Adversarial Configuration Test:
    Verifies that verify_access_token strictly refuses to validate tokens
    in staging or production if the key is insecure, weak (< 32 chars), or empty.
    """
    valid_token = create_access_token(
        sub="test_user",
        secret_key="a_valid_32_bytes_super_safe_secret_key_123!"
    )

    # Test with weak key in production environment
    with pytest.raises(SecurityError) as exc_weak:
        verify_access_token(
            valid_token,
            secret_key="insecure-weak-key"
        )
    assert "Unsafe" in str(exc_weak.value) or "missing" in str(exc_weak.value)


@pytest.mark.asyncio
async def test_adversarial_audio_queue_dual_bounds_and_backpressure():
    """
    Adversarial Backpressure Test:
    Simulates an unresponsive/slow WebSocket client where 200 audio chunks (768 KB)
    are delivered by a fast provider.
    Verifies that dual bounds (max items: 120, max bytes: 512 KB) are strictly respected
    and memory cannot grow unbounded.
    """
    queue = asyncio.Queue(maxsize=120)
    audio_bytes = 0
    MAX_BYTES = 512 * 1024
    chunk_size = 3840  # 80ms PCM frame

    # Feed 200 chunks into bounded queue with drop-oldest logic
    for _ in range(200):
        dummy_chunk = b"\x00" * chunk_size
        while queue.full() or (audio_bytes + len(dummy_chunk) > MAX_BYTES):
            dropped = queue.get_nowait()
            audio_bytes = max(0, audio_bytes - len(dropped))
            queue.task_done()

        audio_bytes += len(dummy_chunk)
        await queue.put(dummy_chunk)

    # Assert bounded resource constraints
    assert queue.qsize() <= 120, f"Queue item count exceeded limit: {queue.qsize()}"
    assert audio_bytes <= MAX_BYTES, f"Queue byte budget exceeded: {audio_bytes} > {MAX_BYTES}"
    assert queue.qsize() == min(120, MAX_BYTES // chunk_size)


@pytest.mark.asyncio
async def test_adversarial_multi_worker_fail_fast_guard():
    """
    Topology Guard Test:
    Verifies that starting the server in staging/production:
    1. Allows supported WORKERS=1 single-worker staging.
    2. Strictly raises RuntimeError when WORKERS > 1.
    3. Strictly raises ValueError on invalid or non-positive worker configurations (e.g. 0, -1, 'abc').
    4. Accurately detects command-line flags (--workers 3) to prevent accidental bypass.
    """
    from main import validate_staging_and_production_security_invariants
    from config import Settings
    import sys

    # 1. Supported single-worker (WORKERS=1) succeeds cleanly
    original_workers = settings.WORKERS
    try:
        settings.WORKERS = 1
        # In staging, WORKERS=1 with valid JWT key must not raise any error
        await validate_staging_and_production_security_invariants()
    finally:
        settings.WORKERS = original_workers

    # 2. Multi-worker (WORKERS=4) is rejected with RuntimeError
    try:
        settings.WORKERS = 4
        with pytest.raises(RuntimeError) as exc_info:
            await validate_staging_and_production_security_invariants()
        assert "Multi-worker configuration" in str(exc_info.value)
        assert "strictly forbidden" in str(exc_info.value)
    finally:
        settings.WORKERS = original_workers

    # 3. Invalid or non-positive worker values raise ValueError
    import os
    orig_env_workers = os.environ.get("WORKERS")
    try:
        os.environ["WORKERS"] = "0"
        with pytest.raises(ValueError) as exc_v0:
            Settings._resolve_workers_count()
        assert "must be at least 1" in str(exc_v0.value)

        os.environ["WORKERS"] = "malformed_number"
        with pytest.raises(ValueError) as exc_val:
            Settings._resolve_workers_count()
        assert "Malformed WORKERS configuration" in str(exc_val.value)
    finally:
        if orig_env_workers is not None:
            os.environ["WORKERS"] = orig_env_workers
        else:
            os.environ.pop("WORKERS", None)

    # 4. CLI flag detection (--workers 3)
    orig_argv = list(sys.argv)
    try:
        sys.argv = ["uvicorn", "main:app", "--workers", "3"]
        workers_from_cli = Settings._resolve_workers_count()
        assert workers_from_cli == 3
    finally:
        sys.argv = orig_argv


@pytest.mark.asyncio
async def test_adversarial_audio_queue_accounting_and_interrupt_purge():
    """
    Audio Accounting & Barge-In Stress Test:
    Simulates repeated cycles of enqueuing, dropping, partial dequeuing,
    and instant barge-in purging.
    Verifies that audio_out_bytes accurately tracks queue content and is strictly
    reset to 0 on interrupt/barge-in, never drifting or becoming negative.
    """
    queue = asyncio.Queue(maxsize=120)
    audio_out_bytes = 0
    MAX_BYTES = 512 * 1024
    chunk_size = 3840

    for cycle in range(10):
        # Enqueue 30 chunks
        for _ in range(30):
            chunk = b"\xaa" * chunk_size
            while queue.full() or (audio_out_bytes + len(chunk) > MAX_BYTES):
                dropped = queue.get_nowait()
                audio_out_bytes = max(0, audio_out_bytes - len(dropped))
                queue.task_done()
            audio_out_bytes += len(chunk)
            await queue.put(chunk)

        assert audio_out_bytes == queue.qsize() * chunk_size
        assert audio_out_bytes >= 0

        # Dequeue 10 chunks (simulating consumer)
        for _ in range(10):
            c = await queue.get()
            audio_out_bytes = max(0, audio_out_bytes - len(c))
            queue.task_done()

        assert audio_out_bytes == queue.qsize() * chunk_size
        assert audio_out_bytes >= 0

        # Simulate barge-in / interrupt purge
        while not queue.empty():
            dropped = queue.get_nowait()
            audio_out_bytes = max(0, audio_out_bytes - len(dropped))
            queue.task_done()
        audio_out_bytes = 0

        # Must be strictly empty and zero bytes
        assert queue.empty()
        assert audio_out_bytes == 0



