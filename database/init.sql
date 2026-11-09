-- ==============================================================================
-- DIALOGUE AI REPRESENTATIVE - Database Initialization Script (Docker / MariaDB)
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS `menkopolkam_ai_hub`
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `menkopolkam_ai_hub`;

-- 1. Table: users
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Table: saved_files
CREATE TABLE IF NOT EXISTS saved_files (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    timestamp VARCHAR(50),
    speaker VARCHAR(100),
    original_audio_text TEXT,
    detected_language VARCHAR(10),
    detected_language_name VARCHAR(50),
    translated_indonesian_text TEXT,
    selected_answer TEXT,
    notes TEXT,
    ai_answers_json LONGTEXT,
    chatgpt_answers_json LONGTEXT,
    gemini_answers_json LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Table: session_history
CREATE TABLE IF NOT EXISTS session_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50),
    action VARCHAR(100),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Default Users Seed (Ring 1 Defense Edition - 10 Users)
INSERT INTO users (username, password, name, role, avatar, description, is_protected)
VALUES 
    ('jenderal.dudung', 'DudungVVIP2026!', 'Jenderal TNI (Purn.) Prof. Dr. Dudung Abdurachman', 'Menteri', '🎖️', 'Penasihat Khusus Presiden RI Urusan Pertahanan Nasional (Principal VVIP)', TRUE),
    ('stafahli.geopolitik', 'Geopolitik2026!', 'Staf Ahli Geopolitik & Hukum Laut', 'Admin', '🌐', 'Tenaga Ahli Analisis Wilayah Maritim & UNCLOS 1982', TRUE),
    ('stafahli.alutsista', 'Alutsista2026!', 'Staf Ahli Doktrin & Industri Pertahanan', 'Admin', '🛡️', 'Tenaga Ahli Modernisasi Alutsista & Kebijakan Strategis Pertahanan', TRUE),
    ('stafahli.siber', 'SiberSandi2026!', 'Staf Ahli Keamanan Siber & Intelijen', 'Admin', '🛰️', 'Tenaga Ahli Ketahanan Siber & Intelijen Strategis', TRUE),
    ('ajudan.adc1', 'AjudanVVIP2026!', 'Kolonel Inf. Ajudan Pribadi 1 (ADC Lapangan)', 'Menteri', '📱', 'Ajudan Utama Pendamping Sidang & Protokoler VVIP (Mobile APK)', TRUE),
    ('ajudan.adc2', 'AjudanVVIP2026!', 'Letkol Laut Ajudan Pribadi 2 (ADC Operasional)', 'Menteri', '💼', 'Ajudan Lapangan Koordinasi Logistik & Pengawalan Delegasi (Mobile APK)', TRUE),
    ('notulis.utama', 'Notulis2026!', 'Mayor Perwira Notulis Sidang Utama', 'Admin', '📝', 'Perumus Notulensi & Verifikator Dokumen Kenegaraan Resmi', TRUE),
    ('notulis.analis', 'Analis2026!', 'Analis Data & Rangkuman Dokumen', 'Admin', '📊', 'Editor Naskah Dokumen & Rekomendasi Penyelesaian Kebijakan', TRUE),
    ('viewer.pemantau', 'Viewer2026!', 'Ruang Pantau / Pengamat Sidang', 'Viewer', '👁️', 'Akses Pantau Notulensi & Live Teleprompter (Mode Peninjau)', FALSE),
    ('admin.sandi', 'SandiSistem2026!', 'Administrator Sandi & Keamanan Sistem', 'Superadmin', '⚡', 'Superadmin Sistem, Manajemen Kunci Enkripsi & Audit Keamanan', TRUE),
    -- Baseline System Fallbacks
    ('admin', 'admin', 'Admin Operasional', 'Admin', '🛡️', 'Administrator Operasional Pusat Dialogue AI Representative', TRUE),
    ('superadmin', 'superadmin', 'Superadmin Sistem', 'Superadmin', '⚡', 'Superadmin Keamanan & Akses Penuh Sistem', TRUE),
    ('viewer', 'viewer', 'Pengamat Kebijakan', 'Viewer', '👁️', 'Pengamat & Peninjau Dokumen Resmi Polkam (Akses Pantau)', FALSE)
ON DUPLICATE KEY UPDATE
    password=VALUES(password),
    name=VALUES(name),
    role=VALUES(role),
    avatar=VALUES(avatar),
    description=VALUES(description),
    is_protected=VALUES(is_protected);

