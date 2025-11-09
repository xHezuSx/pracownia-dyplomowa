-- ============================================================================
-- GPW SCRAPER DATABASE v2.0 - PRODUCTION READY
-- Unified English structure for consistency
-- ============================================================================

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

-- Drop and recreate database
DROP DATABASE IF EXISTS `gpw data`;
CREATE DATABASE `gpw data` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `gpw data`;

-- ============================================================================
-- TABLE 1: companies - Listed companies from GPW
-- ============================================================================
CREATE TABLE `companies` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `full_name` VARCHAR(500) DEFAULT NULL COMMENT 'Full company name',
  `sector` VARCHAR(100) DEFAULT NULL COMMENT 'Industry sector',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_name` (`name`),
  KEY `idx_sector` (`sector`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Companies listed on GPW stock exchange';

-- ============================================================================
-- TABLE 2: reports - Detailed GPW report data
-- ============================================================================
CREATE TABLE `reports` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `company_id` INT(11) DEFAULT NULL,
  `date` DATE DEFAULT NULL,
  `title` TEXT DEFAULT NULL,
  `report_type` ENUM('current','semi-annual','quarterly','interim','annual') DEFAULT NULL,
  `report_category` ENUM('ESPI','EBI') DEFAULT NULL,
  `rate_change` DOUBLE DEFAULT NULL COMMENT 'Stock price change percentage',
  `exchange_rate` DOUBLE DEFAULT NULL COMMENT 'Stock price',
  `link` TEXT DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_company` (`company_id`),
  KEY `idx_date` (`date`),
  KEY `idx_type` (`report_type`),
  KEY `idx_category` (`report_category`),
  CONSTRAINT `fk_reports_company` FOREIGN KEY (`company_id`) 
    REFERENCES `companies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Detailed report data from GPW';

-- ============================================================================
-- TABLE 3: search_history - User search history
-- ============================================================================
CREATE TABLE `search_history` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `company_name` VARCHAR(255) DEFAULT NULL,
  `report_amount` INT(11) DEFAULT NULL,
  `download_type` VARCHAR(50) DEFAULT NULL COMMENT 'PDF, HTML, CSV',
  `report_date` DATE DEFAULT NULL,
  `report_type` VARCHAR(200) DEFAULT NULL,
  `report_category` VARCHAR(100) DEFAULT NULL,
  `model_used` VARCHAR(100) DEFAULT NULL COMMENT 'AI model used for summarization',
  `execution_time` INT(11) DEFAULT NULL COMMENT 'Execution time in seconds',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_company` (`company_name`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User search history';

-- ============================================================================
-- TABLE 4: scheduled_jobs - Cron job configurations
-- ============================================================================
CREATE TABLE `scheduled_jobs` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `job_name` VARCHAR(255) NOT NULL COMMENT 'Unique job identifier',
  `company` VARCHAR(255) NOT NULL,
  `date_from` DATE DEFAULT NULL,
  `date_to` DATE DEFAULT NULL,
  `model` VARCHAR(100) DEFAULT 'llama3.2:latest',
  `cron_schedule` VARCHAR(100) NOT NULL COMMENT 'Cron expression (e.g. 0 9 * * 1)',
  `report_limit` INT(11) DEFAULT 5 COMMENT 'Maximum number of reports to fetch (1-100)',
  `enabled` BOOLEAN DEFAULT TRUE,
  `report_types` JSON DEFAULT NULL COMMENT 'Array of report types ["current","quarterly"]',
  `report_categories` JSON DEFAULT NULL COMMENT 'Array of categories ["ESPI","EBI"]',
  `last_run` TIMESTAMP NULL DEFAULT NULL COMMENT 'Last execution timestamp',
  `next_run` TIMESTAMP NULL DEFAULT NULL COMMENT 'Next scheduled execution',
  `run_count` INT(11) DEFAULT 0 COMMENT 'Total number of executions',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_job_name` (`job_name`),
  KEY `idx_company` (`company`),
  KEY `idx_enabled` (`enabled`),
  KEY `idx_next_run` (`next_run`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Automated job configurations';

-- ============================================================================
-- TABLE 5: summary_reports - Collective summary reports (MD/PDF)
-- ============================================================================
CREATE TABLE `summary_reports` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `job_name` VARCHAR(255) NOT NULL COMMENT 'Job that generated this report',
  `company` VARCHAR(255) NOT NULL,
  `date_from` DATE NULL,
  `date_to` DATE NULL,
  `report_count` INT(11) NOT NULL DEFAULT 0 COMMENT 'Number of reports in summary',
  `document_count` INT(11) NOT NULL DEFAULT 0 COMMENT 'Number of processed documents (PDF/HTML)',
  `file_path` TEXT NOT NULL COMMENT 'Path to .md or .pdf file',
  `file_format` ENUM('md', 'pdf') NOT NULL DEFAULT 'md',
  `file_size` INT(11) NULL COMMENT 'File size in bytes',
  `model_used` VARCHAR(100) DEFAULT NULL COMMENT 'AI model used for summarization',
  `summary_preview` TEXT DEFAULT NULL COMMENT 'First 500 characters of summary',
  `tags` JSON DEFAULT NULL COMMENT 'Tags for categorization ["quarterly-report","2025"]',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_job_name` (`job_name`),
  KEY `idx_company` (`company`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_dates` (`date_from`, `date_to`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Collective summary reports generated by system';

-- ============================================================================
-- TABLE 6: job_execution_log - Job execution history
-- ============================================================================
CREATE TABLE `job_execution_log` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `job_name` VARCHAR(255) NOT NULL,
  `status` ENUM('success', 'failed', 'running', 'cancelled') NOT NULL,
  `started_at` TIMESTAMP NULL,
  `finished_at` TIMESTAMP NULL,
  `duration_seconds` INT(11) DEFAULT NULL,
  `reports_found` INT(11) DEFAULT 0,
  `documents_processed` INT(11) DEFAULT 0,
  `summary_report_id` INT(11) DEFAULT NULL COMMENT 'FK to summary_reports',
  `error_message` TEXT DEFAULT NULL,
  `log_file_path` VARCHAR(500) DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_job_name` (`job_name`),
  KEY `idx_status` (`status`),
  KEY `idx_started_at` (`started_at`),
  KEY `fk_summary_report` (`summary_report_id`),
  CONSTRAINT `fk_execution_summary` FOREIGN KEY (`summary_report_id`) 
    REFERENCES `summary_reports` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Execution history of scheduled jobs';

-- ============================================================================
-- TABLE 7: downloaded_files - Registry of all downloaded files
-- ============================================================================
CREATE TABLE `downloaded_files` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `company` VARCHAR(255) NOT NULL,
  `report_id` INT(11) DEFAULT NULL COMMENT 'FK to reports.id',
  `file_name` VARCHAR(500) NOT NULL,
  `file_path` TEXT NOT NULL,
  `file_type` ENUM('pdf', 'html', 'csv') NOT NULL,
  `file_size` INT(11) DEFAULT NULL,
  `md5_hash` VARCHAR(32) DEFAULT NULL COMMENT 'Hash for duplicate detection',
  `is_summarized` BOOLEAN DEFAULT FALSE,
  `summary_text` LONGTEXT DEFAULT NULL COMMENT 'AI summary for this file',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_hash` (`md5_hash`),
  KEY `idx_company` (`company`),
  KEY `idx_file_type` (`file_type`),
  KEY `idx_summarized` (`is_summarized`),
  KEY `fk_report` (`report_id`),
  CONSTRAINT `fk_file_report` FOREIGN KEY (`report_id`) 
    REFERENCES `reports` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Registry of all downloaded files with deduplication';

-- ============================================================================
-- VIEWS FOR EASIER QUERIES
-- ============================================================================

-- View: Active jobs with latest status
CREATE VIEW `v_active_jobs` AS
SELECT 
    sj.id,
    sj.job_name,
    sj.company,
    sj.model,
    sj.cron_schedule,
    sj.enabled,
    sj.last_run,
    sj.next_run,
    sj.run_count,
    COUNT(DISTINCT sr.id) as summary_count,
    (SELECT status FROM job_execution_log WHERE job_name = sj.job_name ORDER BY id DESC LIMIT 1) as last_status
FROM scheduled_jobs sj
LEFT JOIN summary_reports sr ON sr.job_name = sj.job_name
GROUP BY sj.id;

-- View: Company statistics
CREATE VIEW `v_company_stats` AS
SELECT 
    c.name as company,
    c.sector,
    COUNT(DISTINCT r.id) as total_reports,
    COUNT(DISTINCT df.id) as downloaded_files,
    COUNT(DISTINCT sr.id) as summary_reports,
    MAX(r.date) as latest_report_date,
    MAX(sr.created_at) as latest_summary_date
FROM companies c
LEFT JOIN reports r ON r.company_id = c.id
LEFT JOIN downloaded_files df ON df.company = c.name
LEFT JOIN summary_reports sr ON sr.company = c.name
GROUP BY c.id, c.name, c.sector;

-- ============================================================================
-- STORED PROCEDURES
-- ============================================================================

DELIMITER $$

-- Procedure: Update job statistics after execution
CREATE PROCEDURE `update_job_stats`(
    IN p_job_name VARCHAR(255),
    IN p_status ENUM('success', 'failed', 'running', 'cancelled'),
    IN p_reports_found INT,
    IN p_documents_processed INT,
    IN p_duration INT,
    IN p_summary_report_id INT,
    IN p_error_message TEXT,
    IN p_log_file_path VARCHAR(500)
)
BEGIN
    DECLARE v_started_at TIMESTAMP;
    
    SET v_started_at = NOW() - INTERVAL p_duration SECOND;
    
    -- Insert execution log
    INSERT INTO job_execution_log 
    (job_name, status, started_at, finished_at, duration_seconds, reports_found, 
     documents_processed, summary_report_id, error_message, log_file_path)
    VALUES 
    (p_job_name, p_status, v_started_at, NOW(), p_duration, p_reports_found, 
     p_documents_processed, p_summary_report_id, p_error_message, p_log_file_path);
    
    -- Update job statistics
    UPDATE scheduled_jobs 
    SET 
        last_run = NOW(),
        run_count = run_count + 1
    WHERE job_name = p_job_name;
END$$

-- Procedure: Check if file already exists by MD5
CREATE PROCEDURE `check_file_exists`(
    IN p_md5_hash VARCHAR(32),
    OUT p_exists BOOLEAN,
    OUT p_file_id INT
)
BEGIN
    SELECT COUNT(*) > 0, id INTO p_exists, p_file_id
    FROM downloaded_files
    WHERE md5_hash = p_md5_hash
    LIMIT 1;
END$$

DELIMITER ;

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Sample companies
INSERT INTO `companies` (`name`, `full_name`, `sector`) VALUES
('Asseco', 'Asseco Poland S.A.', 'Technology'),
('kęty', 'Grupa Kęty S.A.', 'Industry'),
('PKO BP', 'Powszechna Kasa Oszczędności Bank Polski S.A.', 'Banking'),
('PZU', 'Powszechny Zakład Ubezpieczeń S.A.', 'Insurance'),
('CD Projekt', 'CD Projekt S.A.', 'Technology'),
('KGHM', 'KGHM Polska Miedź S.A.', 'Mining'),
('Orlen', 'PKN Orlen S.A.', 'Energy'),
('PGE', 'PGE Polska Grupa Energetyczna S.A.', 'Energy');

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
