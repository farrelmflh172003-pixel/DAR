import os
import json
import time
import uuid
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger("menkopolkam.saved_files")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
TOP_DATABASE_DIR = ROOT_DIR / "database"
BACKEND_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Primary database storage points to top-level database directory
DATA_DIR = TOP_DATABASE_DIR if TOP_DATABASE_DIR.exists() else BACKEND_DATA_DIR
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
    selected_answer_en: Optional[str] = ""
    english_translations: Optional[Dict[str, str]] = Field(default_factory=dict)
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
            "kemenko_role": "Dialogue AI Representative memimpin Satgas Terpadu Keamanan Laut dan mengoordinasikan gelar operasi Bakamla, TNI AL, dan KKP.",
            "field_monitoring_agenda": "1. Kunjungan kerja pimpinan Dialogue AI Representative ke Pangkalan Bakamla dan Lanal Ranai Natuna.\n2. Evaluasi kesiapan radar pantai dan sarana patroli bersama pimpinan daerah Natuna.",
            "latest_news": "Bakamla RI dan TNI AL terus mengintensifkan patroli terkoordinasi di perairan Natuna Utara guna memastikan kepatuhan hukum internasional dan pengamanan nelayan tradisional.",
            "model_version": "GPT-4o & Gemini 1.5 Pro Hybrid"
        },
        "chatgpt_answers": {
            "main_answer": "Indonesia secara konsisten menjunjung prinsip diplomasi 'bebas aktif' dan supremasi hukum internasional, khususnya UNCLOS 1982. Di Laut Natuna Utara, kami memperkuat patroli terpadu Bakamla dan TNI AL dalam koridor penegakan hukum maritim sipil, sembari terus mendorong finalisasi Code of Conduct (CoC) di ASEAN.",
            "concise_answer": "Indonesia menegakkan hak berdaulat di ZEE Natuna Utara melalui peningkatan patroli gabungan sipil-maritim (Bakamla) berlandaskan UNCLOS 1982 dan diplomasi preventif ASEAN CoC.",
            "brief_analysis": "Isu ini menuntut keseimbangan antara ketegasan kedaulatan maritim dan penghindaran jebakan eskalasi militer terbuka. Risiko utama adalah insiden laut tidak sengaja oleh armada non-militer asing.",
            "monitoring_issues": "Hasil pemantauan lapangan menunjukkan intensitas kapal asing non-militer masih berulang di batas luar ZEE Natuna Utara.",
            "resolution_recommendations": "1. Penguatan logistik armada patroli Bakamla di pangkalan Ranai Natuna.\n2. Optimalisasi jalur komunikasi diplomatik bilateral khusus (hotline) insiden laut.",
            "kemenko_role": "Dialogue AI Representative memimpin Satgas Terpadu Keamanan Laut dan mengoordinasikan gelar operasi Bakamla, TNI AL, dan KKP.",
            "field_monitoring_agenda": "1. Kunjungan kerja pimpinan Dialogue AI Representative ke Pangkalan Bakamla dan Lanal Ranai Natuna.\n2. Evaluasi kesiapan radar pantai dan sarana patroli bersama pimpinan daerah Natuna.",
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
        "selected_answer_en": "Indonesia consistently upholds the 'free and active' diplomatic posture and the rule of international law, notably UNCLOS 1982. In the North Natuna Sea, our sovereign EEZ, we reinforce coordinated patrols by Bakamla and the Indonesian Navy strictly within maritime law enforcement while actively advancing ASEAN Code of Conduct negotiations to safeguard regional stability.",
        "english_translations": {
            "card_1": "Minister, regarding the recent escalation of gray-zone maritime incursions near North Natuna, what concrete steps is Indonesia taking to enforce UNCLOS 1982 without escalating regional military tensions?",
            "card_2": "Minister, regarding the recent escalation of gray-zone maritime incursions near North Natuna, what concrete steps is Indonesia taking to enforce UNCLOS 1982 without escalating regional military tensions?",
            "card_3": "Indonesia consistently upholds the 'free and active' diplomatic posture and the rule of international law, notably UNCLOS 1982. In the North Natuna Sea, our sovereign EEZ, we reinforce coordinated patrols by Bakamla and the Indonesian Navy strictly within maritime law enforcement while actively advancing ASEAN Code of Conduct negotiations to safeguard regional stability.",
            "card_4": "Indonesia enforces its sovereign rights in the North Natuna EEZ through reinforced civilian-maritime joint patrols grounded on UNCLOS 1982 and preventive diplomacy via the ASEAN CoC.",
            "card_5": "This strategic dilemma balances resolute defense of maritime sovereignty against unintentional military escalations in contested gray-zone waters.",
            "card_8": "Indonesia's position is resolute and non-negotiable: waters north of the Natuna Islands constitute Indonesia's lawful EEZ under UNCLOS 1982. Our measured posture prioritizes civil maritime law enforcement via Bakamla and multilateral de-escalation.",
            "card_9": "Sovereignty and sovereign rights in Natuna rest squarely on UNCLOS 1982. We maintain coordinated civil law enforcement coupled with preventative ASEAN diplomacy.",
            "card_10": "Strategic implications prioritize maritime supply-chain security and international legal legitimacy without projecting offensive intent.",
            "card_20": "Verified News (ChatGPT): Bakamla RI conducts joint coordinated patrols in the North Natuna Sea to safeguard sovereign rights and UNCLOS 1982 compliance.",
            "card_21": "Verified News (Gemini): Maritime patrol deployment reinforced with naval aviation surveillance across North Natuna waters.",
            "card_11": "Indonesia consistently upholds the 'free and active' diplomatic posture and the rule of international law, notably UNCLOS 1982. In the North Natuna Sea, our sovereign EEZ, we reinforce coordinated patrols by Bakamla and the Indonesian Navy strictly within maritime law enforcement while actively advancing ASEAN Code of Conduct negotiations to safeguard regional stability."
        },
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
            "main_answer": "Indonesia melalui BSSN dan Dialogue AI Representative memprioritaskan pelindungan Sistem Elektronik Strategis Nasional dengan menerapkan standar mitigasi siber terpadu dan kerja sama berbagi intelijen ancaman secara bilateral, dengan tetap menjamin kedaulatan data dan privasi nasional.",
            "concise_answer": "Penyelarasan dilakukan melalui pembentukan protokol respons insiden bersama, berbagi intelijen ancaman real-time, dan penguatan kerangka regulasi pelindungan infrastruktur kritis.",
            "brief_analysis": "Kerentanan infrastruktur energi dan keuangan menjadi target utama ransomware global. Peluang: MoU pertukaran forensik digital bilateral. Tantangan: Penyelarasan kerangka hukum pelindungan data.",
            "monitoring_issues": "Tantangan mencakup pemetaan kerentanan sistem warisan (legacy systems) dan perlunya sertifikasi standar ISO 27001 pada penyedia infrastruktur kritis.",
            "resolution_recommendations": "1. Pembentukan Satgas Reaksi Cepat Penanganan Insiden Siber Lintas Instansi.\n2. Standardisasi pelaporan insiden ransomware dalam waktu 1x24 jam.",
            "kemenko_role": "Mengoordinasikan interoperabilitas keamanan siber antara BSSN, Kemkomdigi, BIN, dan instansi terkait.",
            "field_monitoring_agenda": "1. Audit kesiapsiagaan Pusat Operasi Keamanan Siber Nasional (Pusopskamsinas).\n2. Simulasi latihan siber bersama negara mitra kawasan.",
            "latest_news": "Rangkuman Berita: BSSN dan mitra internasional menyepakati protokol respons insiden siber guna memitigasi serangan ransomware pada infrastruktur kritis nasional.",
            "model_version": "GPT-4o & Gemini 1.5 Pro Hybrid"
        },
        "chatgpt_answers": {
            "main_answer": "Indonesia melalui BSSN dan Dialogue AI Representative memprioritaskan pelindungan Sistem Elektronik Strategis Nasional dengan menerapkan standar mitigasi siber terpadu.",
            "concise_answer": "Penyelarasan dilakukan melalui pembentukan protokol respons insiden bersama dan berbagi intelijen ancaman real-time.",
            "brief_analysis": "Kerentanan infrastruktur energi dan keuangan menjadi target utama ransomware global.",
            "monitoring_issues": "Tantangan mencakup pemetaan kerentanan sistem warisan pada penyedia infrastruktur kritis.",
            "resolution_recommendations": "1. Pembentukan Satgas Reaksi Cepat Penanganan Insiden Siber Lintas Instansi.\n2. Standardisasi pelaporan insiden ransomware 1x24 jam.",
            "kemenko_role": "Mengoordinasikan interoperabilitas keamanan siber antara BSSN, Kemkomdigi, BIN, dan instansi terkait.",
            "field_monitoring_agenda": "Audit kesiapsiagaan Pusat Operasi Keamanan Siber Nasional (Pusopskamsinas).",
            "latest_news": "Rangkuman Berita Siber: Peningkatan kewaspadaan terhadap varian ransomware baru yang menargetkan sektor publik.",
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
            "latest_news": "Laporan Siber Terupdate: Deteksi dini anomali lalu lintas data mencegah eskalasi serangan siber berskala besar.",
            "model_version": "Gemini"
        },
        "selected_answer": "Indonesia melalui BSSN dan Dialogue AI Representative memprioritaskan pelindungan Sistem Elektronik Strategis Nasional...",
        "selected_answer_en": "Indonesia, through BSSN and Dialogue AI Representative, prioritizes safeguarding Critical National Information Infrastructure by implementing unified cyber mitigation standards and bilateral threat-intelligence sharing while strictly upholding data sovereignty.",
        "english_translations": {
            "card_1": "How is the Indonesian government aligning its National Cyber Security Strategy with international bilateral partners to counter ransomware threats against critical national infrastructure?",
            "card_2": "How is the Indonesian government aligning its National Cyber Security Strategy with international bilateral partners to counter ransomware threats against critical national infrastructure?",
            "card_3": "Indonesia, through BSSN and Dialogue AI Representative, prioritizes safeguarding Critical National Information Infrastructure by implementing unified cyber mitigation standards and bilateral threat-intelligence sharing while strictly upholding data sovereignty.",
            "card_4": "Alignment is achieved through shared incident response protocols, real-time threat intelligence exchanges, and robust critical infrastructure protection frameworks.",
            "card_5": "Securing energy and financial systems against global ransomware attacks while preserving institutional digital sovereignty.",
            "card_8": "Indonesia's cybersecurity resilience rests on proactive collaboration with trusted bilateral partners, prioritizing national data sovereignty.",
            "card_9": "Cooperation emphasizes Indicator of Compromise (IoC) sharing and integrated digital forensics capacity building.",
            "card_10": "Ransomware mitigation requires coordinated public-private crisis management without introducing foreign technological dependencies.",
            "card_20": "Verified News: Heightened vigilance against novel ransomware variants targeting critical public utilities.",
            "card_21": "Verified News: Early anomaly detection and real-time perimeter monitoring prevent cross-sector cyber escalation.",
            "card_11": "Indonesia, through BSSN and Dialogue AI Representative, prioritizes safeguarding Critical National Information Infrastructure by implementing unified cyber mitigation standards and bilateral threat-intelligence sharing while strictly upholding data sovereignty."
        },
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
            if BACKEND_DATA_DIR.exists() and DATA_DIR != BACKEND_DATA_DIR:
                try:
                    mirror_path = BACKEND_DATA_DIR / "saved_files.json"
                    with open(mirror_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error("Error writing saved files: %s", e)
            return False

    def _write_all(self, data: List[Dict[str, Any]]) -> bool:
        with self._lock:
            return self._write_all_unlocked(data)

    def list_files(self, sort_order: str = "newest_first") -> List[Dict[str, Any]]:
        with self._lock:
            files = self._read_all_unlocked()
            def _sort_key(item: Dict[str, Any]):
                ca = item.get("created_at") or ""
                if ca:
                    return ca
                fid = item.get("id") or ""
                parts = fid.split("-")
                if len(parts) >= 2 and parts[1].isdigit():
                    return f"epoch_{int(parts[1]):015d}"
                return item.get("timestamp") or ""

            if sort_order == "oldest_first":
                files.sort(key=_sort_key, reverse=False)
            else:
                files.sort(key=_sort_key, reverse=True)
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

            file_id = item.get("id") or f"doc-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
            
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
                "selected_answer_en": item.get("selected_answer_en", "") or (item.get("english_translations", {}) or {}).get("card_11", ""),
                "english_translations": item.get("english_translations") or {},
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

    def delete_files(self, file_ids: List[str]) -> int:
        with self._lock:
            files = self._read_all_unlocked()
            initial_len = len(files)
            ids_set = set(file_ids)
            files = [f for f in files if f.get("id") not in ids_set]
            deleted_count = initial_len - len(files)
            if deleted_count > 0:
                self._write_all_unlocked(files)
                logger.info("Deleted %d files", deleted_count)
            return deleted_count

    def clear_all(self) -> int:
        with self._lock:
            files = self._read_all_unlocked()
            count = len(files)
            self._write_all_unlocked([])
            logger.info("Cleared all %d saved files", count)
            return count

    def restore_seeds(self) -> int:
        with self._lock:
            self._write_all_unlocked(INITIAL_SEEDS)
            logger.info("Restored %d initial seeds", len(INITIAL_SEEDS))
            return len(INITIAL_SEEDS)

saved_file_service = SavedFileService()

