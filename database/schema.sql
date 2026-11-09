-- ==============================================================================
-- DIALOGUE AI REPRESENTATIVE - Relational Database Schema (MariaDB / MySQL)
-- ==============================================================================
CREATE DATABASE IF NOT EXISTS `menkopolkam_ai_hub` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `menkopolkam_ai_hub`;
-- 1. Table: users (Authentication & RBAC)
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role ENUM(
        'Admin',
        'Superadmin',
        'Viewer',
        'Menteri',
        'Development'
    ) NOT NULL,
    avatar VARCHAR(10) NOT NULL,
    description TEXT,
    is_protected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
-- 2. Table: saved_files (Official Diplomatic Question Archives & Responses)
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
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
-- 3. Table: session_history (Audit Trail Logs)
CREATE TABLE IF NOT EXISTS session_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50),
    action VARCHAR(100),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
-- ==============================================================================
-- Default System Accounts (Seed Data)
-- ==============================================================================
INSERT INTO users (
        username,
        password,
        name,
        role,
        avatar,
        description,
        is_protected
    )
VALUES (
        'admin',
        'admin',
        'Admin Operasional',
        'Admin',
        '🛡️',
        'Administrator Operasional Pusat Dialogue AI Representative',
        TRUE
    ),
    (
        'superadmin',
        'superadmin',
        'Superadmin Sistem',
        'Superadmin',
        '⚡',
        'Superadmin Keamanan & Akses Penuh Sistem',
        TRUE
    ),
    (
        'viewer',
        'viewer',
        'Pengamat Kebijakan',
        'Viewer',
        '👁️',
        'Pengamat & Peninjau Dokumen Resmi Polkam (Akses Pantau)',
        FALSE
    ) ON DUPLICATE KEY
UPDATE password =
VALUES(password),
    name =
VALUES(name),
    role =
VALUES(role),
    avatar =
VALUES(avatar),
    description =
VALUES(description),
    is_protected =
VALUES(is_protected);