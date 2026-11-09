import os
import json
import time
import uuid
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger("menkopolkam.prompter")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
TOP_DATABASE_DIR = ROOT_DIR / "database"
BACKEND_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_DIR = TOP_DATABASE_DIR if TOP_DATABASE_DIR.exists() else BACKEND_DATA_DIR
PROMPTER_FILES_PATH = DATA_DIR / "prompter_files.json"

class PrompterDocItemModel(BaseModel):
    id: str
    filename: str
    text: str = ""
    pageImages: List[str] = Field(default_factory=list)
    wordCount: int = 0
    charCount: int = 0
    pageCount: int = 1
    durationStr: str = "00:00"
    fileType: str = "txt"
    created_at: Optional[str] = ""
    updated_at: Optional[str] = ""

class PrompterService:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        with self._lock:
            if not PROMPTER_FILES_PATH.exists():
                try:
                    with open(PROMPTER_FILES_PATH, "w", encoding="utf-8") as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                    logger.info("Initialized empty prompter repository at %s", PROMPTER_FILES_PATH)
                except Exception as e:
                    logger.error("Failed to initialize prompter storage: %s", e)

    def _read_all_unlocked(self) -> List[Dict[str, Any]]:
        try:
            if not PROMPTER_FILES_PATH.exists():
                return []
            with open(PROMPTER_FILES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            logger.error("Error reading prompter files: %s", e)
            return []

    def _write_all_unlocked(self, data: List[Dict[str, Any]]) -> bool:
        try:
            temp_path = PROMPTER_FILES_PATH.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, PROMPTER_FILES_PATH)
            if BACKEND_DATA_DIR.exists() and DATA_DIR != BACKEND_DATA_DIR:
                try:
                    mirror_path = BACKEND_DATA_DIR / "prompter_files.json"
                    with open(mirror_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error("Error writing prompter files: %s", e)
            return False

    def list_queue(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._read_all_unlocked()

    def get_item(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            items = self._read_all_unlocked()
            for it in items:
                if it.get("id") == doc_id:
                    return it
            return None

    def add_or_update_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            items = self._read_all_unlocked()
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
            doc_id = item.get("id") or f"doc-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"

            record = {
                "id": doc_id,
                "filename": item.get("filename") or "Naskah Prompter",
                "text": item.get("text", ""),
                "pageImages": item.get("pageImages") or item.get("page_images") or [],
                "wordCount": item.get("wordCount") or item.get("word_count") or (len(item.get("text", "").split()) if item.get("text") else 0),
                "charCount": item.get("charCount") or item.get("char_count") or len(item.get("text", "")),
                "pageCount": item.get("pageCount") or item.get("page_count") or 1,
                "durationStr": item.get("durationStr") or item.get("duration_str") or "00:00",
                "fileType": item.get("fileType") or item.get("file_type") or "txt",
                "created_at": item.get("created_at") or now_iso,
                "updated_at": now_iso
            }

            idx = next((i for i, it in enumerate(items) if it.get("id") == doc_id), None)
            if idx is not None:
                items[idx] = record
            else:
                # Max 10 items limit in prompter queue
                if len(items) >= 10:
                    # Remove oldest from front if capacity reached
                    items.pop(0)
                items.append(record)

            self._write_all_unlocked(items)
            logger.info("Prompter document saved: %s (%s)", doc_id, record["filename"])
            return record

    def update_item_text(self, doc_id: str, text: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            items = self._read_all_unlocked()
            for idx, it in enumerate(items):
                if it.get("id") == doc_id:
                    it["text"] = text
                    words = text.split()
                    it["wordCount"] = len(words)
                    it["charCount"] = len(text)
                    reading_secs = round((len(words) / 130) * 60)
                    mins = reading_secs // 60
                    secs = reading_secs % 60
                    it["durationStr"] = f"{mins:02d}:{secs:02d}"
                    it["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
                    items[idx] = it
                    self._write_all_unlocked(items)
                    return it
            return None

    def reorder_queue(self, ordered_ids: List[str]) -> List[Dict[str, Any]]:
        with self._lock:
            items = self._read_all_unlocked()
            items_map = {it.get("id"): it for it in items}
            reordered: List[Dict[str, Any]] = []
            for oid in ordered_ids:
                if oid in items_map:
                    reordered.append(items_map.pop(oid))
            # Append any remaining items not mentioned in ordered_ids
            for remaining in items_map.values():
                reordered.append(remaining)
            self._write_all_unlocked(reordered)
            return reordered

    def delete_item(self, doc_id: str) -> bool:
        with self._lock:
            items = self._read_all_unlocked()
            initial_len = len(items)
            items = [it for it in items if it.get("id") != doc_id]
            if len(items) < initial_len:
                self._write_all_unlocked(items)
                logger.info("Deleted prompter document: %s", doc_id)
                return True
            return False

    def clear_queue(self) -> int:
        with self._lock:
            items = self._read_all_unlocked()
            count = len(items)
            self._write_all_unlocked([])
            logger.info("Cleared all %d prompter documents", count)
            return count

prompter_service = PrompterService()

