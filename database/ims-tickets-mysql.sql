-- =============================================================================
-- IMS IT Ticketing System — MySQL 8.0+ Schema
-- Run this script once against a fresh database.
-- =============================================================================

SET NAMES utf8mb4;
SET time_zone = '+00:00';
SET foreign_key_checks = 0;
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------------------------------
-- Admin users
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `admin_users` (
  `id`            INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  `username`      VARCHAR(80)      NOT NULL,
  `password_hash` VARCHAR(255)     NOT NULL COMMENT 'password_hash() output',
  `password_salt` VARCHAR(64)      NOT NULL DEFAULT '' COMMENT 'legacy JS salt — empty for PHP bcrypt rows',
  `name`          VARCHAR(160)     NOT NULL,
  `role`          ENUM('Admin','Technician','Viewer') NOT NULL DEFAULT 'Admin',
  `is_active`     TINYINT(1)       NOT NULL DEFAULT 1,
  `created_at`    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_admin_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Default admin: username=admin  password=admin123
-- Hash generated with PHP password_hash('admin123', PASSWORD_BCRYPT)
INSERT INTO `admin_users` (`username`, `password_hash`, `name`, `role`) VALUES
('admin', '$2y$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'IT Administrator', 'Admin');

-- -----------------------------------------------------------------------------
-- Departments (reference table — populated on first use if missing)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `departments` (
  `id`   SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120)      NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dept_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- Tickets
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `tickets` (
  `id`                   INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  `ticket_number`        VARCHAR(20)      NOT NULL COMMENT 'IT-YYYY-NNNNNN',
  `employee_name`        VARCHAR(160)     NOT NULL,
  `department`           VARCHAR(120)     NOT NULL,
  `contact`              VARCHAR(80)      NOT NULL DEFAULT '' COMMENT 'employee email address',
  `computer_name`        VARCHAR(120)     NOT NULL DEFAULT 'Unknown Device',
  `category`             ENUM('Hardware','Software','Network','Printer','Email','Account','Other') NOT NULL,
  `priority`             ENUM('Low','Normal','High','Critical') NOT NULL DEFAULT 'Normal',
  `description`          TEXT             NOT NULL,
  `screenshot_path`      VARCHAR(500)     NULL     DEFAULT NULL COMMENT 'relative path inside /uploads/',
  `status`               ENUM('Pending','In Progress','Waiting for User','Resolved','Closed','Cancelled') NOT NULL DEFAULT 'Pending',
  `assigned_technician`  VARCHAR(160)     NULL     DEFAULT NULL,
  `admin_notes`          TEXT             NULL     DEFAULT NULL,
  `launch_params`        JSON             NULL     DEFAULT NULL COMMENT 'GPO launcher query params',
  `created_at`           DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`           DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `resolved_at`          DATETIME         NULL     DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ticket_number` (`ticket_number`),
  KEY `idx_status_created`   (`status`, `created_at`),
  KEY `idx_priority`         (`priority`),
  KEY `idx_department`       (`department`(64)),
  KEY `idx_category`         (`category`),
  KEY `idx_computer_name`    (`computer_name`(64)),
  KEY `idx_assigned`         (`assigned_technician`(64)),
  FULLTEXT KEY `ft_search`   (`employee_name`, `department`, `computer_name`, `description`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Counter table used for atomic ticket number generation
CREATE TABLE IF NOT EXISTS `ticket_number_seq` (
  `year`    SMALLINT UNSIGNED NOT NULL,
  `seq`     INT UNSIGNED      NOT NULL DEFAULT 0,
  PRIMARY KEY (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- Timeline / audit logs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ticket_logs` (
  `id`         INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  `ticket_id`  INT UNSIGNED  NOT NULL,
  `action`     VARCHAR(80)   NOT NULL,
  `old_status` VARCHAR(40)   NULL DEFAULT NULL,
  `new_status` VARCHAR(40)   NULL DEFAULT NULL,
  `admin`      VARCHAR(160)  NOT NULL DEFAULT 'Employee',
  `notes`      TEXT          NULL DEFAULT NULL,
  `created_at` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_log_ticket` (`ticket_id`, `created_at`),
  CONSTRAINT `fk_log_ticket` FOREIGN KEY (`ticket_id`)
    REFERENCES `tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- Attachments (supports multiple files per ticket in future)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ticket_attachments` (
  `id`           INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  `ticket_id`    INT UNSIGNED  NOT NULL,
  `filename`     VARCHAR(260)  NOT NULL COMMENT 'stored filename on disk',
  `original`     VARCHAR(260)  NOT NULL COMMENT 'original upload filename',
  `mime_type`    VARCHAR(80)   NOT NULL,
  `size_bytes`   INT UNSIGNED  NOT NULL DEFAULT 0,
  `path`         VARCHAR(500)  NOT NULL COMMENT 'relative to /uploads/',
  `uploaded_by`  VARCHAR(160)  NOT NULL DEFAULT 'Employee',
  `uploaded_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_att_ticket` (`ticket_id`),
  CONSTRAINT `fk_att_ticket` FOREIGN KEY (`ticket_id`)
    REFERENCES `tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- Admin sessions (PHP session IDs mapped to users for server-side auth)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `admin_sessions` (
  `session_id`  VARCHAR(128)  NOT NULL,
  `user_id`     INT UNSIGNED  NOT NULL,
  `ip`          VARCHAR(45)   NOT NULL DEFAULT '',
  `user_agent`  VARCHAR(300)  NOT NULL DEFAULT '',
  `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at`  DATETIME      NOT NULL,
  PRIMARY KEY (`session_id`),
  KEY `idx_sess_user` (`user_id`),
  CONSTRAINT `fk_sess_user` FOREIGN KEY (`user_id`)
    REFERENCES `admin_users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET foreign_key_checks = 1;
