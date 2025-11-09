# 🗄️ DIAGRAM STRUKTURY BAZY DANYCH GPW Scraper v2.0

**Last Updated:** 2025-01-25  
**Language:** English (unified structure)  
**Database:** `gpw data` (MySQL/MariaDB)  
**Version:** 2.0 - Complete Redesign

---

## 📊 CORE DATA STRUCTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GPW SCRAPER DATABASE v2.0 - ENGLISH                       │
│                        🔄 Synchronized with codebase                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────────┐
│   COMPANIES      │◄────┐   │      REPORTS         │
├──────────────────┤     │   ├──────────────────────┤
│ id (PK)          │     └───┤ company_id (FK)      │
│ name             │         │ id (PK)              │
│ full_name        │         │ date                 │
│ sector           │         │ title                │
│ created_at       │         │ report_type          │
└──────────────────┘         │ report_category      │
        │                    │ rate_change          │
        │                    │ exchange_rate, link  │
        │                    │ created_at           │
        │                    └──────────────────────┘
        │                             │
        │                             │
        │                    ┌────────▼──────────────┐
        │                    │  DOWNLOADED_FILES     │
        │                    ├───────────────────────┤
        │                    │ id (PK)               │
        ├────────────────────┤ company               │
        │                    │ report_id (FK)        │
        │                    │ file_name             │
        │                    │ file_path             │
        │                    │ file_type (pdf/html)  │
        │                    │ md5_hash (UNIQUE)     │◄─── Deduplication
        │                    │ is_summarized         │
        │                    │ summary_text (LONG)   │
        │                    │ file_size             │
        │                    │ created_at            │
        │                    └───────────────────────┘
        │
        │
        ▼
┌──────────────────────────┐
│    SEARCH_HISTORY        │
├──────────────────────────┤
│ id (PK)                  │
│ company_name             │
│ report_amount            │
│ download_type            │
│ report_date              │
│ report_type              │
│ report_category          │
│ model_used          ◄────┼─── AI model tracking
│ execution_time      ◄────┼─── Performance metric
│ created_at               │
└──────────────────────────┘
```

---

## 🤖 AUTOMATION & SCHEDULING SYSTEM

```
════════════════════════════════════════════════════════════════════════════
                        SCHEDULER & AUTOMATION
════════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────┐         ┌────────────────────────────┐
│      SCHEDULED_JOBS              │         │  JOB_EXECUTION_LOG         │
├──────────────────────────────────┤         ├────────────────────────────┤
│ id (PK)                          │◄────┐   │ id (PK)                    │
│ job_name (UNIQUE)                │     └───┤ job_name (FK)              │
│ company, date_from, date_to      │         │ status (running/success    │
│ model, cron_schedule             │         │        /error)             │
│ enabled (TRUE/FALSE)             │         │ started_at                 │
│ report_types (JSON)         ◄────┼───┐     │ finished_at                │
│ report_categories (JSON)    ◄────┼───┤     │ duration_seconds           │
│ last_run, next_run               │   │     │ reports_found              │
│ run_count                        │   │     │ documents_processed        │
│ created_at                       │   │     │ summary_report_id (FK) ────┼───┐
│ updated_at                       │   │     │ error_message              │   │
└──────────────────────────────────┘   │     │ log_file_path              │   │
                                       │     │ created_at                 │   │
                                       │     └────────────────────────────┘   │
                                       │                                      │
                     ┌─────────────────▼──────────────────────┐              │
                     │         SUMMARY_REPORTS                │              │
                     ├────────────────────────────────────────┤              │
                     │ id (PK)                                │◄─────────────┘
                     │ job_name                               │
                     │ company, date_from, date_to            │
                     │ report_count, document_count           │
                     │ file_path (SUMMARY_REPORTS/*.md)       │
                     │ file_format (markdown/pdf)             │
                     │ file_size, model_used                  │
                     │ summary_preview (TEXT)                 │
                     │ tags (JSON) ["asseco", "insiders"]     │
                     │ created_at                             │
                     └────────────────────────────────────────┘

JSON Fields Details:
─────────────────────
report_types:       ["EBI", "ESPI", ...]
report_categories:  ["raporty bieżące", "raporty okresowe", ...]
tags:               ["company-name", "topic", "year-2025"]
```

---

## 📋 DATABASE VIEWS

### **v_active_jobs** - Active Scheduler Overview
```sql
SELECT 
    id, job_name, company, model, cron_schedule,
    enabled, last_run, next_run, run_count
FROM scheduled_jobs
WHERE enabled = TRUE
ORDER BY next_run ASC
```
**Purpose:** Quick view of what's currently scheduled to run

---

### **v_company_stats** - Company Statistics
```sql
SELECT 
    c.name,
    COUNT(DISTINCT r.id) as total_reports,
    COUNT(DISTINCT df.id) as total_files,
    SUM(df.file_size) as total_size_bytes,
    COUNT(DISTINCT CASE WHEN df.is_summarized THEN df.id END) as summarized_count
FROM companies c
LEFT JOIN reports r ON c.id = r.company_id
LEFT JOIN downloaded_files df ON r.id = df.report_id
GROUP BY c.id, c.name
```
**Purpose:** Analytics dashboard - files downloaded, summarization progress per company

---

## ⚙️ STORED PROCEDURES

### **update_job_stats()** - Automatic Job Metadata Update
```sql
DELIMITER $$
CREATE PROCEDURE update_job_stats(IN p_job_name VARCHAR(100))
BEGIN
    DECLARE v_next_run DATETIME;
    -- Calculate next run time based on cron_schedule
    SET v_next_run = calculate_next_cron_time(cron_schedule);
    
    UPDATE scheduled_jobs
    SET 
        last_run = NOW(),
        next_run = v_next_run,
        run_count = run_count + 1,
        updated_at = NOW()
    WHERE job_name = p_job_name;
END$$
DELIMITER ;
```
**Purpose:** Called after each scheduled job execution to update metadata

---

### **check_file_exists()** - MD5 Deduplication Check
```sql
DELIMITER $$
CREATE FUNCTION check_file_exists(p_md5_hash CHAR(32))
RETURNS BOOLEAN
DETERMINISTIC
BEGIN
    DECLARE file_exists BOOLEAN;
    
    SELECT COUNT(*) > 0 INTO file_exists
    FROM downloaded_files
    WHERE md5_hash = p_md5_hash;
    
    RETURN file_exists;
END$$
DELIMITER ;
```
**Purpose:** Check if file already exists before downloading (duplicate prevention)

---

## 🔗 FOREIGN KEY RELATIONSHIPS

```
companies.id  ──┬──> reports.company_id
                │
                └──> downloaded_files.company

reports.id ───────> downloaded_files.report_id

scheduled_jobs.job_name ───> job_execution_log.job_name

summary_reports.id ───> job_execution_log.summary_report_id
```

### **ON DELETE CASCADE Rules:**
- Delete company → deletes all reports, downloaded_files, summary_reports
- Delete report → deletes downloaded_files entries
- Delete scheduled_job → deletes execution_log entries
- Delete summary_report → SETS NULL in job_execution_log

---

## 📁 DATA FLOW DIAGRAM

```
   USER INPUT                 SCRAPING                    STORAGE
┌─────────────┐           ┌──────────────┐          ┌──────────────────┐
│ UI / Cron   │──────────>│ scrape_script│─────────>│ downloaded_files │
│  Request    │           │  .py         │          │  (PDF/HTML)      │
└─────────────┘           └──────┬───────┘          └────────┬─────────┘
                                 │                           │
                                 ▼                           ▼
                          ┌──────────────┐          ┌──────────────────┐
                          │  summary.py  │◄─────────│ MD5 Check        │
                          │ (AI Process) │          │ (deduplication)  │
                          └──────┬───────┘          └──────────────────┘
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │ SUMMARY_REPORTS/     │
                     │   report_name.md     │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │  summary_reports     │
                     │  (database record)   │
                     └──────────────────────┘
```

---

## 📊 SAMPLE DATA COUNTS (after migration)

| Table             | Expected Records |
|-------------------|------------------|
| companies         | ~8               |
| reports           | ~500-1000        |
| downloaded_files  | ~300-600         |
| search_history    | ~50-100          |
| scheduled_jobs    | ~5-10            |
| summary_reports   | ~10-20           |
| job_execution_log | ~50-100          |

---

## 🔒 INDEXES & PERFORMANCE

```sql
-- Primary Keys (AUTO_INCREMENT)
companies.id
reports.id
downloaded_files.id
search_history.id
scheduled_jobs.id
summary_reports.id
job_execution_log.id

-- Unique Constraints
scheduled_jobs.job_name
downloaded_files.md5_hash  ◄─── Critical for deduplication

-- Foreign Key Indexes (automatic in InnoDB)
reports.company_id
downloaded_files.report_id
job_execution_log.job_name
job_execution_log.summary_report_id
```

---

## 📝 MIGRATION NOTES

### **From v1.0 → v2.0:**

**Table Renames (Polish → English):**
- `firma` → `companies`
- `dane` → `reports`
- `historia` → `search_history`

**Column Renames:**
- `id_firmy` → `id`
- `Id_firmy` → `company_id`
- `nazwa` → `name`
- `pelna_nazwa` → `full_name`
- `data_dodania` → `created_at`
- `id_raportu` → `id`
- `data` → `date`
- `tytul_raportu` → `title`
- `typ_raportu` → `report_type`
- `kategoria_raportu` → `report_category`
- `zmiana` → `rate_change`
- `kurs` → `exchange_rate`
- `data_pobrania` → `created_at`
- `data_wyszukiwania` → `created_at`

**New Tables Added:**
- `scheduled_jobs` - Replaces /configs/*.json files
- `summary_reports` - Tracks collective MD reports
- `job_execution_log` - Audit trail for automated runs
- `downloaded_files` - File management with MD5 deduplication

**Schema Improvements:**
- JSON columns for flexible configuration (report_types, tags)
- MD5 hashing for file deduplication
- Full audit trail with execution logs
- CASCADE delete rules for data integrity
- Views for common queries
- Stored procedures for automation

---

## 🚀 NEXT STEPS

1. ✅ **Database Installation**
   ```bash
   mysqldump -u user -pqwerty123 "gpw data" > backup_$(date +%Y%m%d).sql
   mysql -u user -pqwerty123 < gpw_data_v2_final.sql
   ```

2. ⚠️ **Code Updates Required:**
   - `database_connection.py` - Add functions for all new tables
   - `config_manager.py` - Migrate to database storage
   - `cron_manager.py` - Sync with scheduled_jobs table
   - `scrape_script.py` - Add MD5 hashing for deduplication
   - `run_scheduled.py` - Log executions to job_execution_log

3. 📊 **Testing Checklist:**
   - [ ] Verify all tables created
   - [ ] Test new database functions
   - [ ] Create test scheduled job via UI
   - [ ] Verify cron synchronization
   - [ ] Test MD5 deduplication
   - [ ] Run automated job and check logs

---

**Remember:** This diagram should be updated whenever database schema changes!

*Generated for GPW Scraper v2.0 - Complete Database Redesign*
