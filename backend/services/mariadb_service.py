import re
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
        # 1. Try mysql.connector first
        try:
            import mysql.connector
            return mysql.connector.connect(
                host=settings.MARIADB_HOST,
                port=settings.MARIADB_PORT,
                user=settings.MARIADB_USER,
                password=settings.MARIADB_PASSWORD,
                database=settings.MARIADB_DATABASE,
                connection_timeout=3,
                autocommit=True
            )
        except ImportError:
            pass
        except Exception as e:
            logger.debug("mysql.connector failed: %s, trying pymysql fallback", e)

        # 2. Try pymysql fallback
        try:
            import pymysql
            return pymysql.connect(
                host=settings.MARIADB_HOST,
                port=settings.MARIADB_PORT,
                user=settings.MARIADB_USER,
                password=settings.MARIADB_PASSWORD,
                database=settings.MARIADB_DATABASE,
                connect_timeout=3,
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor
            )
        except Exception as e:
            logger.debug("MariaDB direct connection error: %s", e)
            return None

    def _init_database(self):
        """Ensures the MariaDB database and core tables exist with connection timeout protection."""
        conn = None
        try:
            # Validate database name to prevent injection
            safe_db = re.sub(r'[^a-zA-Z0-9_]', '', settings.MARIADB_DATABASE) or "menkopolkam_ai_hub"

            # Connect without database first to ensure database exists
            try:
                import mysql.connector
                conn = mysql.connector.connect(
                    host=settings.MARIADB_HOST,
                    port=settings.MARIADB_PORT,
                    user=settings.MARIADB_USER,
                    password=settings.MARIADB_PASSWORD,
                    connection_timeout=3
                )
            except Exception:
                try:
                    import pymysql
                    conn = pymysql.connect(
                        host=settings.MARIADB_HOST,
                        port=settings.MARIADB_PORT,
                        user=settings.MARIADB_USER,
                        password=settings.MARIADB_PASSWORD,
                        connect_timeout=3
                    )
                except Exception:
                    conn = None

            if not conn:
                self._connected = False
                logger.info("MariaDB server not reachable on %s:%s. Operating with resilient JSON file fallback.", settings.MARIADB_HOST, settings.MARIADB_PORT)
                return

            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{safe_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE `{safe_db}`")
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

            # Seed default system accounts (Ring 1 Defense Edition - 10 Users)
            users = [
                ('jenderal.dudung', 'DudungVVIP2026!', 'Jenderal TNI (Purn.) Prof. Dr. Dudung Abdurachman', 'Menteri', '🎖️', 'Penasihat Khusus Presiden RI Urusan Pertahanan Nasional (Principal VVIP)', True),
                ('stafahli.geopolitik', 'Geopolitik2026!', 'Staf Ahli Geopolitik & Hukum Laut', 'Admin', '🌐', 'Tenaga Ahli Analisis Wilayah Maritim & UNCLOS 1982', True),
                ('stafahli.alutsista', 'Alutsista2026!', 'Staf Ahli Doktrin & Industri Pertahanan', 'Admin', '🛡️', 'Tenaga Ahli Modernisasi Alutsista & Kebijakan Strategis Pertahanan', True),
                ('stafahli.siber', 'SiberSandi2026!', 'Staf Ahli Keamanan Siber & Intelijen', 'Admin', '🛰️', 'Tenaga Ahli Ketahanan Siber & Intelijen Strategis', True),
                ('ajudan.adc1', 'AjudanVVIP2026!', 'Kolonel Inf. Ajudan Pribadi 1 (ADC Lapangan)', 'Menteri', '📱', 'Ajudan Utama Pendamping Sidang & Protokoler VVIP (Mobile APK)', True),
                ('ajudan.adc2', 'AjudanVVIP2026!', 'Letkol Laut Ajudan Pribadi 2 (ADC Operasional)', 'Menteri', '💼', 'Ajudan Lapangan Koordinasi Logistik & Pengawalan Delegasi (Mobile APK)', True),
                ('notulis.utama', 'Notulis2026!', 'Mayor Perwira Notulis Sidang Utama', 'Admin', '📝', 'Perumus Notulensi & Verifikator Dokumen Kenegaraan Resmi', True),
                ('notulis.analis', 'Analis2026!', 'Analis Data & Rangkuman Dokumen', 'Admin', '📊', 'Editor Naskah Dokumen & Rekomendasi Penyelesaian Kebijakan', True),
                ('viewer.pemantau', 'Viewer2026!', 'Ruang Pantau / Pengamat Sidang', 'Viewer', '👁️', 'Akses Pantau Notulensi & Live Teleprompter (Mode Peninjau)', False),
                ('admin.sandi', 'SandiSistem2026!', 'Administrator Sandi & Keamanan Sistem', 'Superadmin', '⚡', 'Superadmin Sistem, Manajemen Kunci Enkripsi & Audit Keamanan', True),
                ('admin', 'admin', 'Admin Operasional', 'Admin', '🛡️', 'Administrator Operasional Pusat Dialogue AI Representative', True),
                ('superadmin', 'superadmin', 'Superadmin Sistem', 'Superadmin', '⚡', 'Superadmin Keamanan & Akses Penuh Sistem', True),
                ('viewer', 'viewer', 'Pengamat Kebijakan', 'Viewer', '👁️', 'Pengamat & Peninjau Dokumen Resmi Dialogue AI Representative (Akses Pantau)', False),
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
            logger.info("MariaDB initialized successfully (database: %s)", safe_db)
        except Exception as e:
            logger.info("MariaDB initialization notice: %s. Using resilient JSON storage fallback.", e)
            self._connected = False
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

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
