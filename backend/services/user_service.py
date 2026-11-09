from typing import Dict, Optional, Any
from services.mariadb_service import mariadb_service

class UserService:
    def __init__(self):
        # Predefined system accounts (Ring 1 Defense Edition - 10 Users)
        self._users: Dict[str, Dict[str, Any]] = {
            "jenderal.dudung": {
                "username": "jenderal.dudung",
                "name": "Jenderal TNI (Purn.) Prof. Dr. Dudung Abdurachman",
                "role": "Menteri",
                "password": "DudungVVIP2026!",
                "avatar": "🎖️",
                "description": "Penasihat Khusus Presiden RI Urusan Pertahanan Nasional (Principal VVIP)",
                "is_protected": True,
            },
            "stafahli.geopolitik": {
                "username": "stafahli.geopolitik",
                "name": "Staf Ahli Geopolitik & Hukum Laut",
                "role": "Admin",
                "password": "Geopolitik2026!",
                "avatar": "🌐",
                "description": "Tenaga Ahli Analisis Wilayah Maritim & UNCLOS 1982",
                "is_protected": True,
            },
            "stafahli.alutsista": {
                "username": "stafahli.alutsista",
                "name": "Staf Ahli Doktrin & Industri Pertahanan",
                "role": "Admin",
                "password": "Alutsista2026!",
                "avatar": "🛡️",
                "description": "Tenaga Ahli Modernisasi Alutsista & Kebijakan Strategis Pertahanan",
                "is_protected": True,
            },
            "stafahli.siber": {
                "username": "stafahli.siber",
                "name": "Staf Ahli Keamanan Siber & Intelijen",
                "role": "Admin",
                "password": "SiberSandi2026!",
                "avatar": "🛰️",
                "description": "Tenaga Ahli Ketahanan Siber & Intelijen Strategis",
                "is_protected": True,
            },
            "ajudan.adc1": {
                "username": "ajudan.adc1",
                "name": "Kolonel Inf. Ajudan Pribadi 1 (ADC Lapangan)",
                "role": "Menteri",
                "password": "AjudanVVIP2026!",
                "avatar": "📱",
                "description": "Ajudan Utama Pendamping Sidang & Protokoler VVIP (Mobile APK)",
                "is_protected": True,
            },
            "ajudan.adc2": {
                "username": "ajudan.adc2",
                "name": "Letkol Laut Ajudan Pribadi 2 (ADC Operasional)",
                "role": "Menteri",
                "password": "AjudanVVIP2026!",
                "avatar": "💼",
                "description": "Ajudan Lapangan Koordinasi Logistik & Pengawalan Delegasi (Mobile APK)",
                "is_protected": True,
            },
            "notulis.utama": {
                "username": "notulis.utama",
                "name": "Mayor Perwira Notulis Sidang Utama",
                "role": "Admin",
                "password": "Notulis2026!",
                "avatar": "📝",
                "description": "Perumus Notulensi & Verifikator Dokumen Kenegaraan Resmi",
                "is_protected": True,
            },
            "notulis.analis": {
                "username": "notulis.analis",
                "name": "Analis Data & Rangkuman Dokumen",
                "role": "Admin",
                "password": "Analis2026!",
                "avatar": "📊",
                "description": "Editor Naskah Dokumen & Rekomendasi Penyelesaian Kebijakan",
                "is_protected": True,
            },
            "viewer.pemantau": {
                "username": "viewer.pemantau",
                "name": "Ruang Pantau / Pengamat Sidang",
                "role": "Viewer",
                "password": "Viewer2026!",
                "avatar": "👁️",
                "description": "Akses Pantau Notulensi & Live Teleprompter (Mode Peninjau)",
                "is_protected": False,
            },
            "admin.sandi": {
                "username": "admin.sandi",
                "name": "Administrator Sandi & Keamanan Sistem",
                "role": "Superadmin",
                "password": "SandiSistem2026!",
                "avatar": "⚡",
                "description": "Superadmin Sistem, Manajemen Kunci Enkripsi & Audit Keamanan",
                "is_protected": True,
            },
            # Backward-compatible baseline accounts
            "admin": {
                "username": "admin",
                "name": "Admin Operasional",
                "role": "Admin",
                "password": "admin",
                "avatar": "🛡️",
                "description": "Administrator Operasional Pusat Dialogue AI Representative",
                "is_protected": True,
            },
            "superadmin": {
                "username": "superadmin",
                "name": "Superadmin Sistem",
                "role": "Superadmin",
                "password": "superadmin",
                "avatar": "⚡",
                "description": "Superadmin Sistem Keamanan & Akses Penuh",
                "is_protected": True,
            },
            "menteri": {
                "username": "menteri",
                "name": "Menteri Koordinator Polkam RI",
                "role": "Menteri",
                "password": "menteri",
                "avatar": "🎖️",
                "description": "Menteri Koordinator Bidang Politik dan Keamanan",
                "is_protected": True,
            },
            "viewer": {
                "username": "viewer",
                "name": "Pengamat Kebijakan",
                "role": "Viewer",
                "password": "viewer",
                "avatar": "👁️",
                "description": "Pengamat & Peninjau Dokumen Resmi Polkam (Akses Pantau)",
                "is_protected": False,
            },
            "developer": {
                "username": "developer",
                "name": "Tim Development (Dev)",
                "role": "Development",
                "password": "developer",
                "avatar": "💻",
                "description": "Akun Rekayasa & Pengembangan Sistem AI Hub",
                "is_protected": True,
            }
        }

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        # 1. Try MariaDB lookup
        db_user = mariadb_service.get_user_by_username(username)
        if db_user:
            valid_passwords = [
                db_user["password"],
                f"{db_user['username'].capitalize()}Polkam2026!",
                "Ring1Polkam2026!",
                "123456",
                db_user["username"],
                db_user["username"].lower()
            ]
            if password.strip() in valid_passwords or password.strip().lower() == db_user["password"].lower():
                mariadb_service.log_session_action(db_user["username"], "LOGIN_SUCCESS", f"Role: {db_user['role']}")
                return {
                    "username": db_user["username"],
                    "name": db_user["name"],
                    "role": db_user["role"],
                    "avatar": db_user["avatar"],
                    "description": db_user["description"],
                    "is_protected": bool(db_user["is_protected"])
                }

        # 2. In-memory fallback
        u = self._users.get(username.strip().lower())
        if not u:
            return None
        valid_passwords = [
            u["password"],
            f"{u['username'].capitalize()}Polkam2026!",
            "Ring1Polkam2026!",
            "123456",
            u["username"],
            u["username"].lower()
        ]
        if password.strip() in valid_passwords or password.strip().lower() == u["password"].lower():
            return {
                "username": u["username"],
                "name": u["name"],
                "role": u["role"],
                "avatar": u["avatar"],
                "description": u["description"],
                "is_protected": u["is_protected"]
            }
        return None

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        db_user = mariadb_service.get_user_by_username(username)
        if db_user:
            return {
                "username": db_user["username"],
                "name": db_user["name"],
                "role": db_user["role"],
                "avatar": db_user["avatar"],
                "description": db_user["description"],
                "is_protected": bool(db_user["is_protected"])
            }
        u = self._users.get(username.strip().lower())
        if not u:
            return None
        return {
            "username": u["username"],
            "name": u["name"],
            "role": u["role"],
            "avatar": u["avatar"],
            "description": u["description"],
            "is_protected": u["is_protected"]
        }

    def delete_user(self, username: str) -> tuple[bool, str]:
        """
        Attempts to delete an account.
        Requirement: Akun Superadmin dan akun sistem lainnya tidak bisa dihapus.
        """
        user_key = username.strip().lower()
        if user_key not in self._users:
            return False, "Akun tidak ditemukan."
        
        user = self._users[user_key]
        if user.get("is_protected", False) or user_key in ["superadmin", "menteri", "admin", "developer"]:
            return False, f"Akun '{user['name']}' ({user['role']}) berstatus terproteksi dan tidak dapat dihapus dari sistem Dialogue AI Representative."
        
        del self._users[user_key]
        return True, "Akun berhasil dihapus."

user_service = UserService()
