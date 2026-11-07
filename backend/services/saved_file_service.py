import os
import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger("menkopolkam.saved_files")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAVED_FILES_PATH = DATA_DIR / "saved_files.json"

class AIAnswerBundleDict(BaseModel):
    main_answer: str = ""
    concise_answer: str = ""
    brief_analysis: str = ""
    monitoring_issues: str = ""
    resolution_recommendations: str = ""
    kemenko_role: str = ""
    field_monitoring_agenda: str = ""
    latest_news: str = ""
    model_version: Optional[str] = "Diplomatic Intelligence Hybrid"

class SavedFileModel(BaseModel):
    id: str
    title: str = "Sesi Tanpa Judul"
    timestamp: str = ""
    speaker: str = "Delegasi / Penanya"
    original_audio_text: str = ""  # Menulis ulang tangkapan suara (asing)
    detected_language: str = "auto"
    detected_language_name: str = "Otomatis"
    translated_indonesian_text: str = ""  # Menulis ulang tangkapan suara (hasil translate indo) 100% translate
    ai_answers: AIAnswerBundleDict = Field(default_factory=AIAnswerBundleDict)
    chatgpt_answers: Optional[Dict[str, Any]] = None
    gemini_answers: Optional[Dict[str, Any]] = None
    selected_answer: Optional[str] = ""
    notes: Optional[str] = ""
    created_at: str = ""
    updated_at: str = ""

INITIAL_SEEDS = [
    {
        "id": "doc-natuna-01",
        "title": "Kedaulatan Maritim & Penegakan UNCLOS 1982 di Laut Natuna Utara",
        "timestamp": "04 Nov 2026, 10:14 WIB",
        "speaker": "H.E. Special Envoy on Indo-Pacific Maritime Affairs",
        "original_audio_text": "Minister, regarding the recent escalation of gray-zone maritime incursions near North Natuna, what concrete steps is Indonesia taking to enforce UNCLOS 1982 without escalating regional military tensions?",
        "detected_language": "en",
        "detected_language_name": "English (Inggris)",
        "translated_indonesian_text": "Menteri, terkait eskalasi intrusi maritim 'zona abu-abu' baru-baru ini di dekat Natuna Utara, langkah konkret apa yang diambil Indonesia untuk menegakkan UNCLOS 1982 tanpa memicu eskalasi ketegangan militer regional?",
        "ai_answers": {
            "main_answer": "Indonesia secara konsisten menjunjung prinsip diplomasi 'bebas aktif' dan supremasi hukum internasional, khususnya UNCLOS 1982. Di Laut Natuna Utara, yang merupakan ZEE berdaulat Indonesia, kami memperkuat patroli terpadu Bakamla dan TNI AL dalam koridor penegakan hukum maritim sipil, sembari terus mendorong finalisasi Code of Conduct (CoC) di ASEAN guna menjaga stabilitas.",
            "concise_answer": "Indonesia menegakkan hak berdaulat di ZEE Natuna Utara melalui peningkatan patroli gabungan sipil-maritim (Bakamla) berlandaskan UNCLOS 1982 dan diplomasi preventif ASEAN CoC.",
            "brief_analysis": "Isu ini menuntut keseimbangan antara ketegasan kedaulatan maritim dan penghindaran jebakan eskalasi militer terbuka. Risiko utama adalah insiden laut tidak sengaja oleh armada non-militer asing.",
            "monitoring_issues": "Hasil pemantauan lapangan menunjukkan intensitas kapal asing non-militer masih berulang di batas luar ZEE Natuna Utara.",
            "resolution_recommendations": "1. Penguatan logistik armada patroli Bakamla di pangkalan Ranai Natuna.\n2. Optimalisasi jalur komunikasi diplomatik bilateral khusus (hotline) insiden laut.",
            "kemenko_role": "Kemenko Polkam memimpin Satgas Terpadu Keamanan Laut dan mengoordinasikan gelar operasi Bakamla, TNI AL, dan KKP.",
            "field_monitoring_agenda": "1. Kunjungan kerja Menko Polkam ke Pangkalan Bakamla dan Lanal Ranai Natuna.\n2. Evaluasi kesiapan radar pantai dan sarana patroli bersama Bupati Natuna.",
            "latest_news": "Bakamla RI dan TNI AL terus mengintensifkan patroli terkoordinasi di perairan Natuna Utara guna memastikan kepatuhan hukum internasional dan pengamanan nelayan tradisional.",
            "model_version": "GPT-4o & Gemini 1.5 Pro Hybrid"
        },
        "chatgpt_answers": {
            "main_answer": "Indonesia secara konsisten menjunjung prinsip diplomasi 'bebas aktif' dan supremasi hukum internasional, khususnya UNCLOS 1982. Di Laut Natuna Utara, kami memperkuat patroli terpadu Bakamla dan TNI AL dalam koridor penegakan hukum maritim sipil, sembari terus mendorong finalisasi Code of Conduct (CoC) di ASEAN.",
            "concise_answer": "Indonesia menegakkan hak berdaulat di ZEE Natuna Utara melalui peningkatan patroli gabungan sipil-maritim (Bakamla) berlandaskan UNCLOS 1982 dan diplomasi preventif ASEAN CoC.",
            "brief_analysis": "Isu ini menuntut keseimbangan antara ketegasan kedaulatan maritim dan penghindaran jebakan eskalasi militer terbuka. Risiko utama adalah insiden laut tidak sengaja oleh armada non-militer asing.",
            "monitoring_issues": "Hasil pemantauan lapangan menunjukkan intensitas kapal asing non-militer masih berulang di batas luar ZEE Natuna Utara.",
            "resolution_recommendations": "1. Penguatan logistik armada patroli Bakamla di pangkalan Ranai Natuna.\n2. Optimalisasi jalur komunikasi diplomatik bilateral khusus (hotline) insiden laut.",
            "kemenko_role": "Kemenko Polkam memimpin Satgas Terpadu Keamanan Laut dan mengoordinasikan gelar operasi Bakamla, TNI AL, dan KKP.",
            "field_monitoring_agenda": "1. Kunjungan kerja Menko Polkam ke Pangkalan Bakamla dan Lanal Ranai Natuna.\n2. Evaluasi kesiapan radar pantai dan sarana patroli bersama Bupati Natuna.",
            "latest_news": "Rangkuman Berita: Bakamla RI menggelar patroli bersama di Laut Natuna Utara guna amankan hak berdaulat dan tegakkan kepatuhan UNCLOS 1982.",
            "model_version": "ChatGPT"
        },
        "gemini_answers": {
            "main_answer": "Posisi Indonesia teguh dan tidak dapat dinegosiasikan: perairan di utara Kepulauan Natuna adalah ZEE Indonesia yang sah menurut UNCLOS 1982. Respons terukur kami menitikberatkan pada penguatan kehadiran hukum maritim melalui Bakamla dan penegakan hukum sipil.",
            "concise_answer": "Kedaulatan dan hak berdaulat Indonesia di Natuna berlandaskan mutlak pada UNCLOS 1982. Kami mengedepankan penegakan hukum sipil terkoordinasi dan de-eskalasi diplomatik melalui dialog multilateral ASEAN.",
            "brief_analysis": "Implikasi strategis berfokus pada ketahanan rantai pasok maritim dan legitimasi hukum multilateral. Risiko diplomatik muncul apabila ada salah persepsi bahwa kehadiran aparat disamakan dengan postur ofensif.",
            "monitoring_issues": "Intelijen maritim mengidentifikasi taktik gray-zone memanfaatkan kapal riset dan penangkap ikan berbendera asing tanpa izin resmi.",
            "resolution_recommendations": "1. Peningkatan integrasi data satelit maritim dengan sistem komando kendali terpusat.\n2. Diplomasi maritim multilateral memperjuangkan penataan zona tangkap damai.",
            "kemenko_role": "Mengawal perumusan regulasi Omnibus Hukum Laut Keamanan Maritim dan konsolidasi kepemimpinan tunggal penegakan hukum laut sipil.",
            "field_monitoring_agenda": "1. Gelar apel kesiapsiagaan operasi terpadu pengamanan perbatasan di Selat Lampa Natuna.\n2. Peninjauan sistem radar maritim dan dialog langsung dengan nelayan sentra Natuna.",
            "latest_news": "Laporan Berita: Penempatan unsur patroli laut diperkuat dengan dukungan helikopter maritim untuk pengawasan perairan Natuna Utara.",
            "model_version": "Gemini"
        },
        "selected_answer": "Indonesia secara konsisten menjunjung prinsip diplomasi 'bebas aktif' dan supremasi hukum internasional, khususnya UNCLOS 1982...",
        "notes": "Dokumentasi resmi arahan Menko Polkam untuk konferensi pers bilateral.",
        "created_at": "2026-11-04T10:14:22+07:00",
        "updated_at": "2026-11-04T10:14:22+07:00"
    },
    {
        "id": "doc-cyber-02",
        "title": "Strategi Keamanan Siber Nasional & Penangkalan Ransomware Kritis",
        "timestamp": "04 Nov 2026, 11:05 WIB",
        "speaker": "Ambassador for Cyber Affairs & Digital Diplomacy",
        "original_audio_text": "How is the Indonesian government aligning its National Cyber Security Strategy with international bilateral partners to counter ransomware threats against critical national infrastructure?",
        "detected_language": "en",
        "detected_language_name": "English (Inggris)",
        "translated_indonesian_text": "Bagaimana pemerintah Indonesia menyelaraskan Strategi Keamanan Siber Nasional dengan mitra bilateral internasional untuk menangkal ancaman ransomware terhadap infrastruktur kritis nasional?",
        "ai_answers": {
            "main_answer": "Indonesia melalui BSSN dan Kemenko Polkam memprioritaskan pelindungan Sistem Elektronik Strategis Nasional dengan menerapkan standar mitigasi siber terpadu dan kerja sama berbagi intelijen ancaman secara bilateral, dengan tetap menjamin kedaulatan data dan privasi nasional.",
            "concise_answer": "Penyelarasan dilakukan melalui pembentukan protokol respons insiden bersama, berbagi intelijen ancaman real-time, dan penguatan kerangka regulasi pelindungan infrastruktur kritis.",
            "brief_analysis": "Kerentanan infrastruktur energi dan keuangan menjadi target utama ransomware global. Peluang: MoU pertukaran forensik digital bilateral. Tantangan: Penyelarasan kerangka hukum pelindungan data.",
            "monitoring_issues": "Tantangan mencakup pemetaan kerentanan sistem warisan (legacy systems) dan perlunya sertifikasi standar ISO 27001 pada penyedia infrastruktur kritis.",
            "resolution_recommendations": "1. Pembentukan Satgas Reaksi Cepat Penanganan Insiden Siber Lintas K/L.\n2. Standardisasi pelaporan insiden ransomware dalam waktu 1x24 jam.",
            "kemenko_role": "Mengoordinasikan interoperabilitas keamanan siber nasional antara BSSN, Kemkomdigi, BIN, dan Polri.",
            "field_monitoring_agenda": "1. Audit kesiapsiagaan Pusat Operasi Keamanan Siber Nasional (Pusopskamsinas).\n2. Simulasi latihan siber bersama negara mitra kawasan.",
            "latest_news": "Rangkuman Berita: BSSN dan mitra internasional menyepakati protokol respons insiden siber guna memitigasi serangan ransomware pada infrastruktur kritis nasional.",
            "model_version": "GPT-4o & Gemini 1.5 Pro Hybrid"
        },
        "chatgpt_answers": {
            "main_answer": "Indonesia melalui BSSN dan Kemenko Polkam memprioritaskan pelindungan Sistem Elektronik Strategis Nasional dengan menerapkan standar mitigasi siber terpadu.",
            "concise_answer": "Penyelarasan dilakukan melalui pembentukan protokol respons insiden bersama dan berbagi intelijen ancaman real-time.",
            "brief_analysis": "Kerentanan infrastruktur energi dan keuangan menjadi target utama ransomware global.",
            "monitoring_issues": "Tantangan mencakup pemetaan kerentanan sistem warisan pada penyedia infrastruktur kritis.",
            "resolution_recommendations": "1. Pembentukan Satgas Reaksi Cepat Penanganan Insiden Siber Lintas K/L.\n2. Standardisasi pelaporan insiden ransomware 1x24 jam.",
            "kemenko_role": "Mengoordinasikan interoperabilitas keamanan siber nasional antara BSSN, Kemkomdigi, BIN, dan Polri.",
            "field_monitoring_agenda": "Audit kesiapsiagaan Pusat Operasi Keamanan Siber Nasional (Pusopskamsinas).",
            "latest_news": "Rangkuman Berita Siber (ChatGPT): Peningkatan kewaspadaan terhadap varian ransomware baru yang menargetkan sektor publik.",
            "model_version": "ChatGPT"
        },
        "gemini_answers": {
            "main_answer": "Pendekatan ketahanan siber Indonesia bertumpu pada kolaborasi proaktif dengan mitra bilateral terpercaya dengan mengutamakan kedaulatan data nasional.",
            "concise_answer": "Kerja sama difokuskan pada pertukaran indikator kompromi (IoC) dan peningkatan kapasitas forensik digital secara terpadu.",
            "brief_analysis": "Mitigasi ransomware menuntut respons terintegrasi antara sektor publik dan privat tanpa menciptakan ketergantungan teknologi asing.",
            "monitoring_issues": "Intelijen siber mendeteksi pola serangan yang memanfaatkan celah zero-day pada sistem perangkat lunak institusi publik.",
            "resolution_recommendations": "Penyusunan kerangka regulasi pelindungan infrastruktur informasi vital dan peningkatan adopsi arsitektur Zero Trust.",
            "kemenko_role": "Mengawal penyelarasan kebijakan strategis keamanan siber dengan kepentingan diplomasi digital luar negeri.",
            "field_monitoring_agenda": "Peninjauan kesiapan infrastruktur komputasi awan pemerintah dan pusat data nasional.",
            "latest_news": "Laporan Siber Terupdate (Gemini): Deteksi dini anomali lalu lintas data mencegah eskalasi serangan siber berskala besar.",
            "model_version": "Gemini"
        },
        "selected_answer": "Indonesia melalui BSSN dan Kemenko Polkam memprioritaskan pelindungan Sistem Elektronik Strategis Nasional...",
        "notes": "Dokumentasi sesi pembahasan diplomasi siber internasional.",
        "created_at": "2026-11-04T11:05:18+07:00",
        "updated_at": "2026-11-04T11:05:18+07:00"
    }
]

class SavedFileService:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        with self._lock:
            if not SAVED_FILES_PATH.exists():
                try:
                    with open(SAVED_FILES_PATH, "w", encoding="utf-8") as f:
                        json.dump(INITIAL_SEEDS, f, ensure_ascii=False, indent=2)
                    logger.info("Initialized default saved files repository at %s", SAVED_FILES_PATH)
                except Exception as e:
                    logger.error("Failed to initialize saved files: %s", e)

    def _read_all_unlocked(self) -> List[Dict[str, Any]]:
        try:
            if not SAVED_FILES_PATH.exists():
                return []
            with open(SAVED_FILES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            logger.error("Error reading saved files: %s", e)
            return []

    def _read_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._read_all_unlocked()

    def _write_all_unlocked(self, data: List[Dict[str, Any]]) -> bool:
        try:
            temp_path = SAVED_FILES_PATH.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, SAVED_FILES_PATH)
            return True
        except Exception as e:
            logger.error("Error writing saved files: %s", e)
            return False

    def _write_all(self, data: List[Dict[str, Any]]) -> bool:
        with self._lock:
            return self._write_all_unlocked(data)

    def list_files(self, sort_order: str = "oldest_first") -> List[Dict[str, Any]]:
        with self._lock:
            files = self._read_all_unlocked()
            # Sort oldest first (paling lama ke paling terbaru) as requested
            if sort_order == "newest_first":
                files.sort(key=lambda x: (x.get("created_at", "") or x.get("timestamp", "")), reverse=True)
            else:
                files.sort(key=lambda x: (x.get("created_at", "") or x.get("timestamp", "")), reverse=False)
            return files

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            files = self._read_all_unlocked()
            for f in files:
                if f.get("id") == file_id:
                    return f
            return None

    def create_file(self, item: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            files = self._read_all_unlocked()
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
            now_wib = time.strftime("%d %b %Y, %H:%M WIB")

            file_id = item.get("id") or f"doc-{int(time.time()*1000)}"
            
            # Clean up title if empty
            title = item.get("title", "").strip()
            if not title:
                orig = item.get("original_audio_text", "").strip()
                trans = item.get("translated_indonesian_text", "").strip()
                source_txt = trans or orig
                title = (source_txt[:60] + "...") if len(source_txt) > 60 else (source_txt or f"Dokumen Sesi {now_wib}")

            record = {
                "id": file_id,
                "title": title,
                "timestamp": item.get("timestamp") or now_wib,
                "speaker": item.get("speaker") or "Delegasi / Penanya",
                "original_audio_text": item.get("original_audio_text", ""),
                "detected_language": item.get("detected_language", "auto"),
                "detected_language_name": item.get("detected_language_name", "Otomatis"),
                "translated_indonesian_text": item.get("translated_indonesian_text", ""),
                "ai_answers": item.get("ai_answers", {
                    "main_answer": "",
                    "concise_answer": "",
                    "brief_analysis": "",
                    "monitoring_issues": "",
                    "resolution_recommendations": "",
                    "kemenko_role": "",
                    "field_monitoring_agenda": "",
                    "latest_news": "",
                    "model_version": "GPT-4o & Gemini 1.5 Pro Hybrid"
                }),
                "chatgpt_answers": item.get("chatgpt_answers"),
                "gemini_answers": item.get("gemini_answers"),
                "selected_answer": item.get("selected_answer", ""),
                "notes": item.get("notes", ""),
                "created_at": item.get("created_at") or now_iso,
                "updated_at": now_iso
            }

            # Check if exists, update or insert at front
            existing_idx = next((i for i, f in enumerate(files) if f.get("id") == file_id), None)
            if existing_idx is not None:
                files[existing_idx] = record
            else:
                files.insert(0, record)

            self._write_all_unlocked(files)
            logger.info("Saved file recorded: %s (%s)", file_id, title)
            return record

    def update_file(self, file_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            files = self._read_all_unlocked()
            for idx, f in enumerate(files):
                if f.get("id") == file_id:
                    for k, v in updates.items():
                        if k not in ("id", "created_at"):
                            f[k] = v
                    f["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
                    files[idx] = f
                    self._write_all_unlocked(files)
                    logger.info("Updated file: %s", file_id)
                    return f
            return None

    def delete_file(self, file_id: str) -> bool:
        with self._lock:
            files = self._read_all_unlocked()
            initial_len = len(files)
            files = [f for f in files if f.get("id") != file_id]
            if len(files) < initial_len:
                self._write_all_unlocked(files)
                logger.info("Deleted file: %s", file_id)
                return True
            return False

saved_file_service = SavedFileService()

