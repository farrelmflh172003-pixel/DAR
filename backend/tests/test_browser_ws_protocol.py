import pytest
import asyncio
import json
import websockets
import httpx
from config import settings
from utils.security import create_access_token

WS_URL = "ws://127.0.0.1:8000/ws/realtime-session"
VALID_ORIGIN = "http://localhost:5173"
INVALID_ORIGIN = "http://evil-attacker.com"

def get_server_ticket(user_id="browser_user_test"):
    """Fetch a single-use connection ticket from the running FastAPI server."""
    token = create_access_token(sub=user_id, role="operator")
    res = httpx.post(
        "http://127.0.0.1:8000/api/auth/ticket",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5.0
    )
    if res.status_code == 200:
        return res.json()["ticket"]
    raise RuntimeError(f"Failed to fetch ticket: {res.status_code} - {res.text}")

async def receive_session_created(ws, timeout=8.0):
    """Helper to consume initial status messages and return the session_created event."""
    t_end = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < t_end:
        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
        if isinstance(msg, str):
            data = json.loads(msg)
            if data.get("type") == "session_created":
                return data
    raise TimeoutError("session_created message not received within timeout")

@pytest.mark.asyncio
async def test_origin_header_validation_and_rejection():
    """Verify Origin header security: allow valid frontend origin, reject unauthorized origins."""
    try:
        t1 = get_server_ticket("user_origin_valid")
        # 1. Valid origin succeeds
        async with websockets.connect(
            f"{WS_URL}?ticket={t1}",
            additional_headers={"Origin": VALID_ORIGIN}
        ) as ws:
            init_data = await receive_session_created(ws)
            assert init_data["type"] == "session_created"
            assert "session_id" in init_data

        t2 = get_server_ticket("user_origin_invalid")
        # 2. Unauthorized origin is rejected with HTTP 403 Forbidden / Handshake Exception
        with pytest.raises((websockets.exceptions.InvalidHandshake, websockets.exceptions.ConnectionClosed)):
            async with websockets.connect(
                f"{WS_URL}?ticket={t2}",
                additional_headers={"Origin": INVALID_ORIGIN}
            ) as ws:
                await ws.recv()

    except (ConnectionRefusedError, httpx.ConnectError):
        pytest.skip("Backend server on port 8000 is not running.")

@pytest.mark.asyncio
async def test_two_concurrent_browser_clients_protocol_isolation():
    """Verify two independent browser clients have isolated sessions with zero crosstalk."""
    try:
        t1 = get_server_ticket("user_client_1")
        t2 = get_server_ticket("user_client_2")
        async with websockets.connect(f"{WS_URL}?ticket={t1}", additional_headers={"Origin": VALID_ORIGIN}) as ws1, \
                   websockets.connect(f"{WS_URL}?ticket={t2}", additional_headers={"Origin": VALID_ORIGIN}) as ws2:

            init1 = await receive_session_created(ws1)
            init2 = await receive_session_created(ws2)

            sess_id_1 = init1["session_id"]
            sess_id_2 = init2["session_id"]
            assert sess_id_1 != sess_id_2

            # Client 1 switches provider to openai_realtime
            await ws1.send(json.dumps({"type": "switch_provider", "provider": "openai_realtime"}))

            # Client 1 receives provider_switched
            switched_event = None
            for _ in range(5):
                msg = await asyncio.wait_for(ws1.recv(), timeout=8.0)
                if isinstance(msg, str):
                    d = json.loads(msg)
                    if d.get("type") == "provider_switched":
                        switched_event = d
                        break

            assert switched_event is not None
            assert switched_event.get("provider") == "openai_realtime"

            # Client 2 must NOT receive Client 1's provider_switched event
            try:
                msg2 = await asyncio.wait_for(ws2.recv(), timeout=0.6)
                if isinstance(msg2, str):
                    d2 = json.loads(msg2)
                    # Must NOT be the switched event from client 1
                    assert d2.get("type") != "provider_switched"
                    assert d2.get("provider") != "openai_realtime"
            except asyncio.TimeoutError:
                pass # Perfectly fine if queue was empty

    except (ConnectionRefusedError, httpx.ConnectError):
        pytest.skip("Backend server on port 8000 is not running.")

@pytest.mark.asyncio
async def test_oversized_audio_payload_rejection():
    """Verify security constraint: binary audio payload exceeding MAX_AUDIO_CHUNK_BYTES (512KB) is rejected."""
    try:
        t = get_server_ticket("user_oversized_audio")
        async with websockets.connect(f"{WS_URL}?ticket={t}", additional_headers={"Origin": VALID_ORIGIN}) as ws:
            await receive_session_created(ws)

            # Send 513 KB binary payload
            oversized_audio = b"\x00" * (513 * 1024)
            await ws.send(oversized_audio)

            # Server must return explicit error
            error_event = None
            for _ in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=4.0)
                if isinstance(msg, str):
                    d = json.loads(msg)
                    if d.get("type") == "error":
                        error_event = d
                        break

            assert error_event is not None
            assert "exceeds" in error_event.get("message", "").lower()

    except (ConnectionRefusedError, httpx.ConnectError):
        pytest.skip("Backend server on port 8000 is not running.")

@pytest.mark.asyncio
async def test_clean_client_disconnect_and_reconnect():
    """Verify that closing a client WebSocket cleans up the server session and allows clean reconnection."""
    try:
        t1 = get_server_ticket("user_reconnect")
        # First connection
        async with websockets.connect(f"{WS_URL}?ticket={t1}", additional_headers={"Origin": VALID_ORIGIN}) as ws:
            init = await receive_session_created(ws)
            first_session_id = init["session_id"]

        # Small pause to let server finalize teardown
        await asyncio.sleep(0.2)

        t2 = get_server_ticket("user_reconnect")
        # Reconnection
        async with websockets.connect(f"{WS_URL}?ticket={t2}", additional_headers={"Origin": VALID_ORIGIN}) as ws:
            init = await receive_session_created(ws)
            new_session_id = init["session_id"]
            assert new_session_id != first_session_id

    except (ConnectionRefusedError, httpx.ConnectError):
        pytest.skip("Backend server on port 8000 is not running.")

