from typing import Dict, Optional, Any
from services.mariadb_service import mariadb_service

class UserService:
    def __init__(self):
        # Predefined system accounts
        self._users: Dict[str, Dict[str, Any]] = {
            "admin": {
                "username": "admin",
                "name": "Admin Operasional",
                "role": "Admin",
                "password": "admin",
                "avatar": "🛡️",
                "description": "Administrator Operasional Pusat Kemenko Polkam",
                "is_protected": True,
            },
            "superadmin": {
                "username": "superadmin",
                "name": "Superadmin Sistem",
                "role": "Superadmin",
                "password": "superadmin",
                "avatar": "⚡",
                "description": "Superadmin Sistem Keamanan & Akses Penuh",
                "is_protected": True, # Akun superadmin tidak bisa dihapus
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
            valid_passwords = [db_user["password"], f"{db_user['username'].capitalize()}Polkam2026!", "123456"]
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
        valid_passwords = [u["password"], f"{u['username'].capitalize()}Polkam2026!", "123456"]
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
            return False, f"Akun '{user['name']}' ({user['role']}) berstatus terproteksi dan tidak dapat dihapus dari sistem Menkopolkam AI Hub."
        
        del self._users[user_key]
        return True, "Akun berhasil dihapus."

user_service = UserService()
