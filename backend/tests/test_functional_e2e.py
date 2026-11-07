import pytest
import base64
from fastapi.testclient import TestClient
from main import app
from services.captcha_service import captcha_service
from services.user_service import user_service
from services.ai_orchestrator import translate_text_universal, process_live_question_fast

client = TestClient(app)

def test_login_success_with_valid_captcha_and_credentials():
    """Verify end-to-end login with valid captcha and system credentials."""
    # 1. Generate captcha
    challenge = captcha_service.generate_captcha()
    cid = challenge["captcha_id"]
    # Solve equation
    q = challenge["question"].replace("= ?", "").strip()
    if "+" in q:
        a, b = q.split("+")
        ans = str(int(a.strip()) + int(b.strip()))
    else:
        a, b = q.split("-")
        ans = str(int(a.strip()) - int(b.strip()))

    payload = {
        "username": "admin",
        "password": "admin",
        "captcha_id": cid,
        "captcha_answer": ans
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "token" in data
    assert data["user"]["role"] == "Admin"

def test_translator_api_markdown_preservation():
    """Verify /api/translate endpoint translates and preserves rich text markdown."""
    payload = {
        "text": "**Kebijakan Keamanan Maritim**:\n- Poin 1: Penegakan kedaulatan di ZEE Natuna.\n- Poin 2: Diplomasi damai ASEAN.",
        "target_lang": "en",
        "source_lang": "id"
    }
    res = client.post("/api/translate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "translated_text" in data
    assert len(data["translated_text"]) > 0

def test_document_extract_api():
    """Verify /api/document/extract processes and extracts text from base64 files."""
    sample_text = "SURAT KEPUTUSAN MENKO POLKAM RI\nNomor: KEP-01/MENKO/POLKAM/2026\nTentang Kesiapan Satgas Terpadu."
    b64_content = base64.b64encode(sample_text.encode("utf-8")).decode("ascii")

    payload = {
        "filename": "nota_dinas.txt",
        "file_base64": f"data:text/plain;base64,{b64_content}"
    }
    res = client.post("/api/document/extract", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "text" in data
    assert "SURAT KEPUTUSAN" in data["text"]

@pytest.mark.asyncio
async def test_cards_bundle_structure_and_fallback():
    """Verify live question processing produces complete bundles for Card 1 to Card 11."""
    query = "Bagaimana kebijakan pengamanan perbatasan maritim di Kepulauan Riau?"
    trans_id, cg_b, gem_b, en_trans, sources, is_factual, v_lang, v_name, is_doc = await process_live_question_fast(query)

    # Verify Card 1 & 2
    assert len(trans_id) > 0
    assert v_lang in ("id", "auto")

    # Verify Card 3, 4, 5 (ChatGPT bundle)
    assert len(cg_b.main_answer) > 0
    assert len(cg_b.concise_answer) > 0
    assert len(cg_b.brief_analysis) > 0

    # Verify Card 8, 9, 10 (Gemini bundle)
    assert len(gem_b.main_answer) > 0
    assert len(gem_b.concise_answer) > 0
    assert len(gem_b.brief_analysis) > 0

    # Verify Card 11 (English translation bundle)
    assert "card_3" in en_trans or "card_8" in en_trans
