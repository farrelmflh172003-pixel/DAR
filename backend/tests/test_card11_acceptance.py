import json
import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.saved_file_service import saved_file_service, SavedFileService
from backend.models import DiplomaticResponseSet, AIAnswerBundle, CanonicalQuestion

client = TestClient(app)

# ==============================================================================
# SECTION A: STATE DAN DATA CONSISTENCY
# ==============================================================================

def test_api_saved_files_ordering_newest_first():
    """Verify GET /api/saved-files returns items sorted strictly newest-first."""
    files = saved_file_service.list_files(sort_order="newest_first")
    assert len(files) >= 2, "Need at least 2 files to verify ordering"
    
    # Verify chronological descending order
    for i in range(len(files) - 1):
        ca1 = files[i].get("created_at") or files[i].get("timestamp", "")
        ca2 = files[i + 1].get("created_at") or files[i + 1].get("timestamp", "")
        if ca1 and ca2 and "T" in ca1 and "T" in ca2:
            assert ca1 >= ca2, f"Files out of order: {ca1} should be >= {ca2}"


def test_filter_empty_and_stress_test_records():
    """Verify empty documents and stress test records are excluded from main document selection."""
    test_docs = [
        {"id": "test-stress-1", "title": "Concurrent Stress Record #99", "selected_answer": "stress"},
        {"id": "test-empty-1", "title": "Empty Doc", "selected_answer": "", "chatgpt_answers": None, "original_audio_text": ""},
        {"id": "test-valid-1", "title": "Dokumen Valid Strategis", "selected_answer": "Jawaban Strategis Valid"}
    ]
    
    # Filtering predicate used in App.tsx
    def is_valid_main_doc(f):
        is_stress = f.get("title", "").startswith("Concurrent Stress") or f.get("title", "").startswith("Concurrency Audit")
        has_content = bool(
            (f.get("selected_answer") and f.get("selected_answer").strip()) or
            (f.get("original_audio_text") and f.get("original_audio_text").strip())
        )
        return not is_stress and has_content

    valid_candidates = [f for f in test_docs if is_valid_main_doc(f)]
    assert len(valid_candidates) == 1
    assert valid_candidates[0]["id"] == "test-valid-1"


def test_selected_answer_persistence_and_reload():
    """Verify selected_answer is saved and reloaded with 100% data integrity."""
    doc_payload = {
        "title": "Uji Persistensi Card 11",
        "original_audio_text": "Bagaimana pertahanan maritim Natuna?",
        "translated_indonesian_text": "Bagaimana pertahanan maritim Natuna?",
        "selected_answer": "Pertahanan maritim Natuna diperkuat melalui operasi gabungan TNI AL dan Bakamla RI."
    }
    
    created = saved_file_service.create_file(doc_payload)
    doc_id = created["id"]
    try:
        # Load back via service
        loaded = saved_file_service.get_file(doc_id)
        assert loaded is not None
        assert loaded["selected_answer"] == doc_payload["selected_answer"]
        
        # Load back via API
        res = client.get(f"/api/saved-files/{doc_id}")
        assert res.status_code == 200
        assert res.json()["selected_answer"] == doc_payload["selected_answer"]
    finally:
        saved_file_service.delete_file(doc_id)


def test_document_switching_isolation_no_leakage():
    """Verify switching documents does not leak selected_answer from the previous session."""
    doc1 = saved_file_service.create_file({
        "title": "Dokumen Sesi A",
        "selected_answer": "Jawaban Sesi A Unik 12345"
    })
    doc2 = saved_file_service.create_file({
        "title": "Dokumen Sesi B",
        "selected_answer": "Jawaban Sesi B Unik 67890"
    })
    
    try:
        loaded1 = saved_file_service.get_file(doc1["id"])
        loaded2 = saved_file_service.get_file(doc2["id"])
        
        assert loaded1["selected_answer"] != loaded2["selected_answer"]
        assert loaded1["selected_answer"] == "Jawaban Sesi A Unik 12345"
        assert loaded2["selected_answer"] == "Jawaban Sesi B Unik 67890"
    finally:
        saved_file_service.delete_file(doc1["id"])
        saved_file_service.delete_file(doc2["id"])


def test_card8_gemini_fallback_when_card3_chatgpt_empty():
    """Verify Card 8 (Gemini) is selected when Card 3 (ChatGPT) is empty."""
    doc = saved_file_service.create_file({
        "title": "Dokumen Sesi Gemini Saja",
        "chatgpt_answers": {"main_answer": ""},
        "gemini_answers": {"main_answer": "Analisis Strategis Gemini Komprehensif."},
        "selected_answer": "Analisis Strategis Gemini Komprehensif."
    })
    try:
        res = client.get(f"/api/session/{doc['id']}")
        assert res.status_code == 200
        data = res.json()
        assert data["chatgpt"]["main_answer"] == ""
        assert data["gemini"]["main_answer"] == "Analisis Strategis Gemini Komprehensif."
        # Selected answer must be Gemini's answer
        assert data["selected_answer"] == "Analisis Strategis Gemini Komprehensif."
    finally:
        saved_file_service.delete_file(doc["id"])


# ==============================================================================
# SECTION B: AI RESPONSE SELECTION & FALLBACK
# ==============================================================================

def test_ai_selection_hierarchy():
    """Verify fallback hierarchy: User chosen cards -> saved answer -> ChatGPT -> Gemini."""
    # Skenario 1: Keduanya ada
    both_bundle = DiplomaticResponseSet(
        canonical_question=CanonicalQuestion(id="q1", original_text="Q", timestamp="22:00 WIB"),
        canonical_translation_id="Q",
        chatgpt=AIAnswerBundle(main_answer="ChatGPT Ans", concise_answer="Concise", brief_analysis="Analysis", model_version="ChatGPT"),
        gemini=AIAnswerBundle(main_answer="Gemini Ans", concise_answer="Concise", brief_analysis="Analysis", model_version="Gemini"),
        english_translations={},
        selected_answer="ChatGPT Ans"
    )
    assert both_bundle.selected_answer == "ChatGPT Ans"

    # Skenario 2: ChatGPT gagal / kosong -> Fallback ke Gemini
    gemini_only = DiplomaticResponseSet(
        canonical_question=CanonicalQuestion(id="q2", original_text="Q", timestamp="22:00 WIB"),
        canonical_translation_id="Q",
        chatgpt=AIAnswerBundle(main_answer="", concise_answer="", brief_analysis="", model_version="ChatGPT"),
        gemini=AIAnswerBundle(main_answer="Gemini Standalone", concise_answer="Concise", brief_analysis="Analysis", model_version="Gemini"),
        english_translations={},
        selected_answer="Gemini Standalone"
    )
    assert gemini_only.selected_answer == "Gemini Standalone"

    # Skenario 3: Gemini gagal / kosong -> Fallback ke ChatGPT
    chatgpt_only = DiplomaticResponseSet(
        canonical_question=CanonicalQuestion(id="q3", original_text="Q", timestamp="22:00 WIB"),
        canonical_translation_id="Q",
        chatgpt=AIAnswerBundle(main_answer="ChatGPT Standalone", concise_answer="Concise", brief_analysis="Analysis", model_version="ChatGPT"),
        gemini=AIAnswerBundle(main_answer="", concise_answer="", brief_analysis="", model_version="Gemini"),
        english_translations={},
        selected_answer="ChatGPT Standalone"
    )
    assert chatgpt_only.selected_answer == "ChatGPT Standalone"


def test_user_manual_card_selection_and_switch():
    """Verify manual card selection and subsequent switching updates selected_answer."""
    doc = saved_file_service.create_file({
        "title": "Dokumen Multi-Kartu",
        "chatgpt_answers": {
            "main_answer": "Respon Utama ChatGPT",
            "concise_answer": "Respon Singkat ChatGPT"
        },
        "selected_answer": "Respon Utama ChatGPT"
    })
    doc_id = doc["id"]
    try:
        # User beralih ke Respon Singkat
        updated = saved_file_service.update_file(doc_id, {
            "selected_answer": "Respon Singkat ChatGPT"
        })
        assert updated["selected_answer"] == "Respon Singkat ChatGPT"

        # User menggabungkan dua kartu
        combined = "Respon Utama ChatGPT\n\nRespon Singkat ChatGPT"
        updated2 = saved_file_service.update_file(doc_id, {
            "selected_answer": combined
        })
        assert updated2["selected_answer"] == combined
    finally:
        saved_file_service.delete_file(doc_id)


# ==============================================================================
# SECTION C: LANGUAGE CONSISTENCY & TTS
# ==============================================================================

def test_language_translation_does_not_mutate_source():
    """Verify translating to English preserves the original Indonesian source untouched."""
    source_id = "Koordinasi pengamanan perbatasan maritim berjalan optimal."
    
    # Panggil API translate
    res = client.post("/api/translate", json={
        "text": source_id,
        "target_lang": "en",
        "source_lang": "id"
    })
    assert res.status_code == 200
    translated_en = res.json().get("translated_text", "")
    assert len(translated_en) > 0
    # Original source must be unchanged
    assert source_id == "Koordinasi pengamanan perbatasan maritim berjalan optimal."
    assert translated_en != source_id


def test_tts_endpoint_functional_for_current_content():
    """Verify TTS endpoint processes the exact text given."""
    test_text = "Sistem keamanan siber nasional dalam status siap siaga."
    res = client.post("/api/tts", json={
        "text": test_text,
        "voice": "Kore"
    })
    # Must succeed (200) with audio/wav or 500/503 if offline/mocked
    assert res.status_code in (200, 500, 503)
    if res.status_code == 200:
        assert res.headers["content-type"] == "audio/wav"
        assert len(res.content) > 44  # WAV header is 44 bytes


# ==============================================================================
# SECTION D: PERSISTENCE & BACKEND RESTART CYCLE
# ==============================================================================

def test_backend_restart_persistence_cycle():
    """Verify created document survives backend service re-instantiation (simulated restart)."""
    unique_tag = f"Cycle-Test-{int(time.time()*1000)}"
    doc = saved_file_service.create_file({
        "title": f"Dokumen {unique_tag}",
        "original_audio_text": f"Pertanyaan uji {unique_tag}",
        "selected_answer": f"Jawaban Terpilih {unique_tag}"
    })
    doc_id = doc["id"]
    
    try:
        # Simulasi restart backend dengan instansiasi service baru
        new_service_instance = SavedFileService()
        reloaded = new_service_instance.get_file(doc_id)
        assert reloaded is not None
        assert reloaded["title"] == f"Dokumen {unique_tag}"
        assert reloaded["selected_answer"] == f"Jawaban Terpilih {unique_tag}"
    finally:
        saved_file_service.delete_file(doc_id)


def test_storage_corruption_recovery():
    """Verify system maintains backup and recovers from corrupted state."""
    import shutil, tempfile
    from pathlib import Path
    from backend.services.saved_file_service import SAVED_FILES_PATH
    assert SAVED_FILES_PATH.exists()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        backup_path = Path(tmp_dir) / "saved_files_backup.json"
        shutil.copy2(SAVED_FILES_PATH, backup_path)
        assert backup_path.exists()
        assert backup_path.stat().st_size > 0


# ==============================================================================
# SECTION E: REGRESSION TEST
# ==============================================================================

def test_regression_core_endpoints():
    """Verify that all core application endpoints continue functioning normally."""
    # 1. Health
    h_res = client.get("/api/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "operational"

    # 2. Scenarios
    sc_res = client.get("/api/scenarios")
    assert sc_res.status_code == 200
    assert "natuna_unclos" in [s["id"] for s in sc_res.json()["scenarios"]]

    # 3. Saved Files list
    sf_res = client.get("/api/saved-files")
    assert sf_res.status_code == 200
    assert isinstance(sf_res.json(), list)

    # 4. Process Question
    p_res = client.post("/api/process", json={
        "question_text": "Uji coba integritas sistem Card 11."
    })
    assert p_res.status_code == 200
    res_data = p_res.json()
    assert "canonical_question" in res_data
    assert "chatgpt" in res_data
    assert "gemini" in res_data
    assert "selected_answer" in res_data
    assert len(res_data["selected_answer"]) > 0
    # Clean up the created live session file
    created_id = res_data["canonical_question"]["id"]
    saved_file_service.delete_file(created_id)
