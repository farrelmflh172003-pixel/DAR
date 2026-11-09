import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.utils.security import create_access_token
from backend.services.prompter_service import prompter_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_prompter_state():
    """Ensure prompter starts and ends cleanly without polluting subsequent tests."""
    prompter_service.clear_queue()
    yield
    prompter_service.clear_queue()

@pytest.fixture
def sample_prompter_doc():
    doc = prompter_service.add_or_update_item({
        "id": "test-doc-01",
        "filename": "naskah_pidato_menkopolkam.txt",
        "text": "Selamat pagi hadirin sekalian, mari kita tingkatkan stabilitas maritim nasional.",
        "wordCount": 10,
        "charCount": 78,
        "pageCount": 1,
        "durationStr": "00:05",
        "fileType": "txt"
    })
    return doc

def test_viewer_cannot_add_prompter_document_rbac_defense():
    """
    Penetration Test: Attacker with Viewer role attempts to inject document into prompter queue.
    Server must strictly reject with HTTP 403 Forbidden.
    """
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    res = client.post(
        "/api/prompter/queue",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "id": "injected-doc",
            "filename": "infiltrated.txt",
            "text": "Injected malicious script"
        }
    )
    assert res.status_code == 403
    assert "Akses Ditolak" in res.json().get("detail", "")
    assert "Viewer" in res.json().get("detail", "") or "Pengamat" in res.json().get("detail", "")

def test_viewer_cannot_delete_prompter_document_rbac_defense(sample_prompter_doc):
    """
    Penetration Test: Attacker with Viewer role attempts to delete a document from prompter queue.
    Server must strictly reject with HTTP 403 Forbidden.
    """
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    res = client.delete(
        f"/api/prompter/queue/{sample_prompter_doc['id']}",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert res.status_code == 403
    assert "Akses Ditolak" in res.json().get("detail", "")

def test_viewer_cannot_reorder_or_clear_prompter_rbac_defense(sample_prompter_doc):
    """
    Penetration Test: Attacker with Viewer role attempts to reorder or clear prompter queue.
    Server must strictly reject both with HTTP 403 Forbidden.
    """
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    
    # 1. Reorder attempt
    reorder_res = client.put(
        "/api/prompter/queue/reorder",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"ids": [sample_prompter_doc["id"]]}
    )
    assert reorder_res.status_code == 403
    assert "Akses Ditolak" in reorder_res.json().get("detail", "")

    # 2. Clear all attempt
    clear_res = client.delete(
        "/api/prompter/queue",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert clear_res.status_code == 403
    assert "Akses Ditolak" in clear_res.json().get("detail", "")

def test_viewer_can_read_prompter_queue_legitimately(sample_prompter_doc):
    """
    Verify legitimate read-only access: Viewers can observe and teleprompt queued documents.
    """
    viewer_token = create_access_token(sub="pengamat_tamu", role="viewer")
    res = client.get(
        "/api/prompter/queue",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert res.status_code == 200
    queue = res.json()
    assert isinstance(queue, list)
    assert len(queue) == 1
    assert queue[0]["id"] == sample_prompter_doc["id"]

def test_admin_and_operator_can_manage_prompter_queue():
    """
    Verify Operator/Admin roles have legitimate full CRUD access to prompter queue.
    """
    admin_token = create_access_token(sub="admin_polkam", role="admin")

    # 1. Add document
    create_res = client.post(
        "/api/prompter/queue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "id": "official-brief-01",
            "filename": "Arahan_Menko.txt",
            "text": "Arahan resmi Kemenko Polkam untuk delegasi internasional.",
            "wordCount": 7,
            "charCount": 54,
            "pageCount": 1,
            "durationStr": "00:03",
            "fileType": "txt"
        }
    )
    assert create_res.status_code == 200
    assert create_res.json()["id"] == "official-brief-01"

    # 2. Update text
    edit_res = client.put(
        "/api/prompter/queue/official-brief-01",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"text": "Teks naskah yang telah diedit secara resmi."}
    )
    assert edit_res.status_code == 200
    assert "diedit secara resmi" in edit_res.json()["text"]

    # 3. Read back
    read_res = client.get("/api/prompter/queue")
    assert read_res.status_code == 200
    assert len(read_res.json()) == 1

    # 4. Delete document
    del_res = client.delete(
        "/api/prompter/queue/official-brief-01",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_res.status_code == 200

    # Verify empty
    assert len(client.get("/api/prompter/queue").json()) == 0

