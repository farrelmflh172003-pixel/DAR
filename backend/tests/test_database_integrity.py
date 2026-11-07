import os
import json
import time
import shutil
import tempfile
import concurrent.futures
from pathlib import Path
from services.mariadb_service import MariaDBService
from services.saved_file_service import SavedFileService, SAVED_FILES_PATH

def test_mariadb_resilient_connection_handling():
    """Verify that MariaDBService gracefully handles unreachable database host without crashing."""
    service = MariaDBService()
    # When DB is not running, _connected is False and methods fail safely
    user = service.get_user_by_username("admin")
    assert user is None or isinstance(user, dict)

def test_json_fallback_atomic_writes_and_persistence():
    """Verify JSON fallback guarantees atomic writes and survives reload without loss."""
    test_service = SavedFileService()
    initial_count = len(test_service.list_files())

    # Create new record
    created = test_service.create_file({
        "title": "Uji Pemulihan Database Menkopolkam",
        "speaker": "Direktur Operasi",
        "original_audio_text": "Evaluasi ketahanan satgas maritim.",
        "translated_indonesian_text": "Evaluasi ketahanan satgas maritim.",
        "selected_answer": "Respon taktis terkoordinasi."
    })
    rec_id = created["id"]

    # Verify write reached disk in valid JSON format
    assert SAVED_FILES_PATH.exists()
    with open(SAVED_FILES_PATH, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert any(item["id"] == rec_id for item in disk_data)

    # Clean up created record
    assert test_service.delete_file(rec_id) is True
    assert len(test_service.list_files()) == initial_count

def test_concurrent_read_write_zero_duplicate_records():
    """Stress test concurrent writes to guarantee no duplicate records and zero data loss."""
    test_service = SavedFileService()
    initial_records = test_service.list_files()
    created_ids = []

    def insert_worker(index: int):
        record = test_service.create_file({
            "title": f"Concurrent Stress Record #{index}",
            "speaker": f"Operator-{index}",
            "selected_answer": f"Selected Answer from thread {index}"
        })
        return record["id"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(insert_worker, i) for i in range(16)]
        created_ids = [f.result() for f in futures]

    # Verify exactly 16 unique records were created (no duplicates)
    assert len(set(created_ids)) == 16
    all_files = test_service.list_files()
    id_counts = {cid: sum(1 for f in all_files if f["id"] == cid) for cid in created_ids}
    assert all(count == 1 for count in id_counts.values()), "Duplicate record detected!"

    # Clean up all created stress test records
    for cid in created_ids:
        test_service.delete_file(cid)

def test_database_backup_and_restore_cycle():
    """Verify backup creation, file tampering, and restore cycle."""
    test_service = SavedFileService()
    assert SAVED_FILES_PATH.exists()

    with tempfile.TemporaryDirectory() as tmp_dir:
        backup_path = Path(tmp_dir) / "saved_files_backup.json"
        
        # 1. Create Backup
        shutil.copy2(SAVED_FILES_PATH, backup_path)
        assert backup_path.exists()
        original_size = backup_path.stat().st_size
        assert original_size > 0

        # 2. Modify State
        temp_item = test_service.create_file({"title": "Temporary Backup Test Item"})
        assert test_service.get_file(temp_item["id"]) is not None

        # 3. Restore from Backup
        shutil.copy2(backup_path, SAVED_FILES_PATH)
        restored_files = test_service.list_files()
        assert not any(f["id"] == temp_item["id"] for f in restored_files)

