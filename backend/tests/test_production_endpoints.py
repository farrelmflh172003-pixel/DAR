import pytest
import concurrent.futures
from fastapi.testclient import TestClient
from main import app
from config import settings
from utils.security import create_access_token
from services.saved_file_service import saved_file_service

client = TestClient(app)

def test_security_headers_middleware():
    """Verify enterprise security headers are injected on all HTTP responses."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

def test_api_health_endpoint():
    """Verify health endpoint returns operational status and server details."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "operational"
    assert "application" in data
    assert "mode" in data

def test_captcha_generation():
    """Verify captcha endpoint returns valid SVG challenge and captcha_id."""
    res = client.get("/api/auth/captcha")
    assert res.status_code == 200
    data = res.json()
    assert "captcha_id" in data
    assert "svg" in data
    assert "<svg" in data["svg"]

def test_login_invalid_captcha():
    """Verify login fails with 400 when captcha is invalid."""
    payload = {
        "username": "admin",
        "password": "adminpassword",
        "captcha_id": "invalid-id-xyz",
        "captcha_answer": "WRONG"
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 400
    assert "captcha" in res.json().get("detail", "").lower()

def test_spa_serving_and_static_assets():
    """Verify root / serves HTML and non-existent frontend routes fallback to SPA index."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "text/html" in res_root.headers.get("content-type", "")

    # Deep nested SPA route should return 200 index.html
    res_nested = client.get("/dashboard/session-overview")
    assert res_nested.status_code == 200
    assert "text/html" in res_nested.headers.get("content-type", "")

    # API route that does not exist must return 404 JSON, not HTML
    res_api_404 = client.get("/api/non-existent-endpoint-xyz")
    assert res_api_404.status_code == 404

def test_saved_files_crud_lifecycle():
    """Verify full CRUD lifecycle on saved questions / answers."""
    # 1. Create
    new_doc = {
        "title": "Uji Integrasi Kemenko Polkam 2026",
        "speaker": "Auditor QA",
        "original_audio_text": "Bagaimana kesiapan pertahanan siber nasional?",
        "translated_indonesian_text": "Bagaimana kesiapan pertahanan siber nasional?",
        "ai_answers": {
            "main_answer": "Penguatan arsitektur siber BSSN dan TNI terus ditingkatkan.",
            "concise_answer": "Kesiapan siber nasional prima.",
            "brief_analysis": "Analisis ketahanan infrastruktur kritis.",
            "monitoring_issues": "Mitigasi anomali lalu lintas data.",
            "resolution_recommendations": "Sinergi CSIRT terpadu.",
            "kemenko_role": "Kemenko Polkam mengoordinasikan satgas siber.",
            "field_monitoring_agenda": "Audit kesiapan pusat data.",
            "latest_news": "Simulasi siber gabungan nasional.",
            "model_version": "Audit Suite Test"
        },
        "selected_answer": "Kesiapan siber nasional prima."
    }
    create_res = client.post("/api/saved-files", json=new_doc)
    assert create_res.status_code == 200
    created_id = create_res.json().get("id")
    assert created_id is not None

    # 2. Read list
    list_res = client.get("/api/saved-files")
    assert list_res.status_code == 200
    files = list_res.json()
    assert any(f.get("id") == created_id for f in files)

    # 3. Update (Card 11 auto-sync behavior)
    updated_text = "Updated Selected Answer from Card 11 Automation"
    update_res = client.put(f"/api/saved-files/{created_id}", json={"selected_answer": updated_text})
    assert update_res.status_code == 200
    assert update_res.json().get("selected_answer") == updated_text

    # 4. Delete
    del_res = client.delete(f"/api/saved-files/{created_id}")
    assert del_res.status_code == 200
    assert del_res.json().get("status") == "success"

def test_delete_user_rbac_authorization():
    """Verify unauthenticated user cannot delete accounts, but authorized admin can."""
    # 1. Unauthenticated request should be rejected (401 or 403)
    unauth_res = client.delete("/api/users/viewer")
    assert unauth_res.status_code in (401, 403)

    # 2. Token with unauthorized role (e.g. 'viewer') should be rejected (403)
    viewer_token = create_access_token(sub="test_viewer", role="viewer")
    viewer_res = client.delete(
        "/api/users/viewer",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert viewer_res.status_code == 403

    # 3. Superadmin or protected account cannot be deleted even by Admin
    admin_token = create_access_token(sub="test_admin", role="admin")
    protect_res = client.delete(
        "/api/users/superadmin",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert protect_res.status_code == 400
    assert "terproteksi" in protect_res.json().get("detail", "").lower()

def test_saved_file_concurrency_thread_safety():
    """Verify SavedFileService concurrency: 10 parallel threads updating records without data corruption."""
    # Create test record
    rec = saved_file_service.create_file({
        "title": "Concurrency Audit Record",
        "selected_answer": "Initial"
    })
    rec_id = rec["id"]

    def worker_update(idx: int):
        return saved_file_service.update_file(rec_id, {"selected_answer": f"Worker-{idx}"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_update, i) for i in range(10)]
        results = [f.result() for f in futures]

    assert all(r is not None for r in results)
    final_file = saved_file_service.get_file(rec_id)
    assert final_file is not None
    assert final_file["selected_answer"].startswith("Worker-")

    # Clean up
    saved_file_service.delete_file(rec_id)
