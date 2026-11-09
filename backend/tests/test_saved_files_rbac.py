import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.utils.security import create_access_token
from backend.services.saved_file_service import saved_file_service

client = TestClient(app)

@pytest.fixture
def sample_file():
    doc = saved_file_service.create_file({
        "title": "Dokumen Uji RBAC Menkopolkam",
        "original_audio_text": "Apakah peran Pengamat dapat menghapus arsip?",
        "translated_indonesian_text": "Apakah peran Pengamat dapat menghapus arsip?",
        "selected_answer": "Arsip negara dilindungi oleh sistem keamanan berlapis RBAC."
    })
    yield doc
    saved_file_service.delete_file(doc["id"])

def test_viewer_cannot_delete_saved_file_inspect_bypass(sample_file):
    """
    Penetration Test: Attacker attempts to bypass UI restrictions using browser Inspect / DevTools
    by issuing a raw DELETE fetch request with a Viewer session token.
    Must strictly return 403 Forbidden.
    """
    file_id = sample_file["id"]
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    
    res = client.delete(
        f"/api/saved-files/{file_id}",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert res.status_code == 403
    assert "Akses Ditolak" in res.json().get("detail", "")
    assert "Viewer" in res.json().get("detail", "") or "Pengamat" in res.json().get("detail", "")

def test_viewer_cannot_update_saved_file_inspect_bypass(sample_file):
    """
    Penetration Test: Attacker attempts to tamper with document contents via browser Inspect / DevTools
    using a raw PUT request with a Viewer session token.
    Must strictly return 403 Forbidden.
    """
    file_id = sample_file["id"]
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    
    res = client.put(
        f"/api/saved-files/{file_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"selected_answer": "Hacked content injected via inspect"}
    )
    assert res.status_code == 403
    assert "Akses Ditolak" in res.json().get("detail", "")

def test_viewer_cannot_create_saved_file_inspect_bypass():
    """
    Penetration Test: Attacker attempts to inject new documents via raw POST request with Viewer token.
    Must strictly return 403 Forbidden.
    """
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    
    res = client.post(
        "/api/saved-files",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"title": "Injected File", "selected_answer": "Hacked"}
    )
    assert res.status_code == 403
    assert "Akses Ditolak" in res.json().get("detail", "")

def test_forged_or_tampered_token_rejected_inspect_bypass(sample_file):
    """
    Penetration Test: Attacker attempts to forge a JWT with 'role: superadmin' in DevTools localStorage.
    Because the signature was not minted with JWT_SECRET_KEY, server must return 401 Unauthorized.
    """
    file_id = sample_file["id"]
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJoYWNrZXIiLCJyb2xlIjoic3VwZXJhZG1pbiJ9.invalidsignature123"
    
    res = client.delete(
        f"/api/saved-files/{file_id}",
        headers={"Authorization": f"Bearer {fake_token}"}
    )
    assert res.status_code == 401
    assert "Token" in res.json().get("detail", "") or "tidak valid" in res.json().get("detail", "")

def test_authorized_admin_can_modify_and_delete_saved_file():
    """
    Verify authenticated Admin or Superadmin role can legitimately manage documents.
    """
    admin_token = create_access_token(sub="admin_polkam", role="admin")
    
    # 1. Create
    create_res = client.post(
        "/api/saved-files",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "Dokumen Sah Admin", "selected_answer": "Resmi"}
    )
    assert create_res.status_code == 200
    created_id = create_res.json()["id"]
    
    # 2. Update
    update_res = client.put(
        f"/api/saved-files/{created_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"selected_answer": "Pembaruan Resmi Admin"}
    )
    assert update_res.status_code == 200
    
    # 3. Delete
    delete_res = client.delete(
        f"/api/saved-files/{created_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert delete_res.status_code == 200
    assert delete_res.json().get("status") == "success"

def test_viewer_can_read_saved_files_legitimately(sample_file):
    """
    Verify that Viewers retain legitimate Read-Only access (Viewing and PDF export preview).
    """
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    
    res = client.get(
        "/api/saved-files",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    
    res_single = client.get(
        f"/api/saved-files/{sample_file['id']}",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert res_single.status_code == 200
    assert res_single.json()["id"] == sample_file["id"]

def test_viewer_cannot_bulk_delete_or_clear_all_inspect_bypass():
    """
    Penetration Test: Attacker with Viewer role attempts to bulk delete or wipe archive.
    Must strictly return 403 Forbidden.
    """
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    
    # 1. Bulk delete attempt
    bulk_res = client.post(
        "/api/saved-files/bulk-delete",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"ids": ["doc-1", "doc-2"]}
    )
    assert bulk_res.status_code == 403
    assert "Akses Ditolak" in bulk_res.json().get("detail", "")
    
    # 2. Clear all attempt
    clear_res = client.delete(
        "/api/saved-files",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert clear_res.status_code == 403
    assert "Akses Ditolak" in clear_res.json().get("detail", "")

def test_delete_all_files_remains_empty_no_resurrect():
    """
    Verify Bug Fix: When all documents are cleared/deleted,
    GET /api/saved-files must remain empty [] and NOT resurrect default initial seeds.
    """
    admin_token = create_access_token(sub="admin_polkam", role="admin")
    
    # Clear all
    clear_res = client.delete(
        "/api/saved-files",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert clear_res.status_code == 200
    
    # Read back
    list_res = client.get("/api/saved-files")
    assert list_res.status_code == 200
    assert list_res.json() == [], f"Expected empty list but got {list_res.json()}"
    
    # Restore initial seeds to maintain clean test isolation and persistent state
    saved_file_service.restore_seeds()

