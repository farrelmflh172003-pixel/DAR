import logging
from typing import Dict, List, Optional, Any
from config import settings

logger = logging.getLogger(__name__)

class MariaDBService:
    def __init__(self):
        self._pool = None
        self._connected = False
        self._init_database()

    def _get_connection(self):
        try:
            import mysql.connector
            return mysql.connector.connect(
                host=settings.MARIADB_HOST,
                port=settings.MARIADB_PORT,
                user=settings.MARIADB_USER,
                password=settings.MARIADB_PASSWORD,
                database=settings.MARIADB_DATABASE,
                autocommit=True
            )
        except Exception as e:
            logger.warning("MariaDB direct connection error: %s", e)
            return None

    def _init_database(self):
        """Ensures the MariaDB database and core tables exist."""
        try:
            import mysql.connector
            # Connect without database first to ensure database exists
            conn = mysql.connector.connect(
                host=settings.MARIADB_HOST,
                port=settings.MARIADB_PORT,
                user=settings.MARIADB_USER,
                password=settings.MARIADB_PASSWORD
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.MARIADB_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {settings.MARIADB_DATABASE}")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                role ENUM('Admin', 'Superadmin', 'Viewer', 'Menteri', 'Development') NOT NULL,
                avatar VARCHAR(10) NOT NULL,
                description TEXT,
                is_protected BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_history (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50),
                action VARCHAR(100),
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Seed default system accounts: Admin, Superadmin, Viewer
            users = [
                ('admin', 'admin', 'Admin Operasional', 'Admin', '🛡️', 'Administrator Operasional Pusat Kemenko Polkam', True),
                ('superadmin', 'superadmin', 'Superadmin Sistem', 'Superadmin', '⚡', 'Superadmin Keamanan & Akses Penuh Sistem', True),
                ('viewer', 'viewer', 'Pengamat Kebijakan', 'Viewer', '👁️', 'Pengamat & Peninjau Dokumen Resmi Polkam (Akses Pantau)', False),
            ]
            for u in users:
                cursor.execute("""
                INSERT INTO users (username, password, name, role, avatar, description, is_protected)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    password=VALUES(password),
                    name=VALUES(name),
                    role=VALUES(role),
                    avatar=VALUES(avatar),
                    description=VALUES(description),
                    is_protected=VALUES(is_protected)
                """, u)
            conn.commit()
            cursor.close()
            conn.close()
            self._connected = True
            logger.info("MariaDB initialized successfully (database: %s)", settings.MARIADB_DATABASE)
        except Exception as e:
            logger.warning("MariaDB initialization warning: %s", e)
            self._connected = False

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = %s LIMIT 1", (username.strip().lower(),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row
        except Exception as e:
            logger.error("MariaDB get_user error: %s", e)
            if conn:
                conn.close()
            return None

    def log_session_action(self, username: str, action: str, details: str = ""):
        conn = self._get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO session_history (username, action, details) VALUES (%s, %s, %s)",
                (username, action, details)
            )
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning("MariaDB log_session_action error: %s", e)
            if conn:
                conn.close()

mariadb_service = MariaDBService()
