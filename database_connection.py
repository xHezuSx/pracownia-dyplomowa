"""
Database Connection Module v2.0 - English Unified Structure
Supports: companies, reports, search_history, scheduled_jobs, 
          summary_reports, job_execution_log, downloaded_files
"""

import pymysql
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

# Database connection settings
HOST = "localhost"
USER = "user"
PASSWORD = "qwerty123"
DATABASE = "gpw data"

# Global connection and cursor
connection = None
cursor = None

def connect():
    """Establish database connection"""
    global connection, cursor
    try:
        connection = pymysql.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            cursorclass=pymysql.cursors.DictCursor,  # Return results as dictionaries
            autocommit=False,
            connect_timeout=10
        )
        cursor = connection.cursor()
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

def ensure_connection():
    """Ensure database connection is alive, reconnect if needed"""
    global connection, cursor
    try:
        if connection is None:
            return connect()
        # Test connection with ping
        connection.ping(reconnect=True)
        return True
    except Exception:
        return connect()

# Initialize connection
connect()


# ============================================================================
# COMPANIES TABLE - Company Management
# ============================================================================

def insert_company(name: str, full_name: str = None, sector: str = None) -> int:
    """Insert or get company ID"""
    ensure_connection()
    try:
        # Check if company exists
        company_id = get_company_id(name)
        if company_id:
            return company_id
        
        sql = """
            INSERT INTO companies (name, full_name, sector)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (name, full_name, sector))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"Error inserting company: {e}")
        return None


def get_company_id(name: str) -> Optional[int]:
    """Get company ID by name"""
    ensure_connection()
    try:
        sql = "SELECT id FROM companies WHERE name LIKE %s"
        cursor.execute(sql, (name,))
        result = cursor.fetchone()
        return result['id'] if result else None
    except Exception as e:
        print(f"Error getting company ID: {e}")
        return None


def get_all_companies() -> List[Dict]:
    """Get all companies"""
    ensure_connection()
    try:
        sql = "SELECT * FROM companies ORDER BY name"
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching companies: {e}")
        return []


# ============================================================================
# REPORTS TABLE - GPW Reports Management
# ============================================================================

def insert_report(
    company_id: int,
    date: str,
    title: str,
    report_type: str,
    report_category: str,
    rate_change: float = None,
    exchange_rate: float = None,
    link: str = None
) -> int:
    """Insert GPW report"""
    try:
        sql = """
            INSERT INTO reports 
            (company_id, date, title, report_type, report_category, 
             rate_change, exchange_rate, link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            company_id, date, title, report_type, report_category,
            rate_change, exchange_rate, link
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"Error inserting report: {e}")
        return None


def get_reports(
    company_id: int = None,
    date_from: str = None,
    date_to: str = None,
    report_type: str = None,
    limit: int = 100
) -> List[Dict]:
    """Get reports with filters"""
    try:
        sql = "SELECT * FROM reports WHERE 1=1"
        params = []
        
        if company_id:
            sql += " AND company_id = %s"
            params.append(company_id)
        
        if date_from:
            sql += " AND date >= %s"
            params.append(date_from)
        
        if date_to:
            sql += " AND date <= %s"
            params.append(date_to)
        
        if report_type:
            sql += " AND report_type = %s"
            params.append(report_type)
        
        sql += " ORDER BY date DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return []


# ============================================================================
# DOWNLOADED_FILES TABLE - File Management with MD5 Deduplication
# ============================================================================

def calculate_md5(file_path: str) -> str:
    """Calculate MD5 hash of a file"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error calculating MD5: {e}")
        return None


def file_exists_by_md5(md5_hash: str) -> bool:
    """Check if file already exists by MD5 hash"""
    try:
        sql = "SELECT COUNT(*) as count FROM downloaded_files WHERE md5_hash = %s"
        cursor.execute(sql, (md5_hash,))
        result = cursor.fetchone()
        return result['count'] > 0
    except Exception as e:
        print(f"Error checking file existence: {e}")
        return False


def insert_downloaded_file(
    company: str,
    report_id: int,
    file_name: str,
    file_path: str,
    file_type: str,
    file_size: int,
    md5_hash: str,
    is_summarized: bool = False,
    summary_text: str = None
) -> int:
    """Insert downloaded file record"""
    try:
        # Check for duplicates
        if file_exists_by_md5(md5_hash):
            print(f"File already exists (MD5: {md5_hash})")
            return None
        
        sql = """
            INSERT INTO downloaded_files 
            (company, report_id, file_name, file_path, file_type, 
             file_size, md5_hash, is_summarized, summary_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            company, report_id, file_name, file_path, file_type,
            file_size, md5_hash, is_summarized, summary_text
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"Error inserting downloaded file: {e}")
        return None


def update_file_summary(file_id: int, summary_text: str):
    """Update file summary after AI processing"""
    try:
        sql = """
            UPDATE downloaded_files
            SET is_summarized = TRUE, summary_text = %s
            WHERE id = %s
        """
        cursor.execute(sql, (summary_text, file_id))
        connection.commit()
    except Exception as e:
        connection.rollback()
        print(f"Error updating file summary: {e}")


def get_downloaded_files(company: str = None, is_summarized: bool = None) -> List[Dict]:
    """Get downloaded files with optional filters"""
    try:
        sql = "SELECT * FROM downloaded_files WHERE 1=1"
        params = []
        
        if company:
            sql += " AND company = %s"
            params.append(company)
        
        if is_summarized is not None:
            sql += " AND is_summarized = %s"
            params.append(is_summarized)
        
        sql += " ORDER BY created_at DESC"
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching downloaded files: {e}")
        return []


# ============================================================================
# SEARCH_HISTORY TABLE - Search & Execution Tracking
# ============================================================================

def insert_search_history(
    company_name: str,
    report_amount: int,
    download_type: str,
    report_date: str,
    report_type: str = None,
    report_category: str = None,
    model_used: str = None,
    execution_time: float = None
) -> int:
    """Insert search history record"""
    ensure_connection()
    try:
        sql = """
            INSERT INTO search_history
            (company_name, report_amount, download_type, report_date,
             report_type, report_category, model_used, execution_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            company_name, report_amount, download_type, report_date,
            report_type, report_category, model_used, execution_time
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"Error inserting search history: {e}")
        return None


def get_search_history(limit: int = 50) -> List[Dict]:
    """Get recent search history"""
    ensure_connection()
    try:
        sql = """
            SELECT * FROM search_history
            ORDER BY created_at DESC
            LIMIT %s
        """
        cursor.execute(sql, (limit,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching search history: {e}")
        return []


# ============================================================================
# SCHEDULED_JOBS TABLE - Cron Job Management
# ============================================================================

def insert_scheduled_job(
    job_name: str,
    company: str,
    date_from: str,
    date_to: str,
    model: str,
    cron_schedule: str,
    enabled: bool = True,
    report_types: List[str] = None,
    report_categories: List[str] = None
) -> int:
    """Insert or update scheduled job"""
    try:
        # Convert lists to JSON
        report_types_json = json.dumps(report_types) if report_types else None
        report_categories_json = json.dumps(report_categories) if report_categories else None
        
        sql = """
            INSERT INTO scheduled_jobs
            (job_name, company, date_from, date_to, model, cron_schedule,
             enabled, report_types, report_categories)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                company = VALUES(company),
                date_from = VALUES(date_from),
                date_to = VALUES(date_to),
                model = VALUES(model),
                cron_schedule = VALUES(cron_schedule),
                enabled = VALUES(enabled),
                report_types = VALUES(report_types),
                report_categories = VALUES(report_categories),
                updated_at = NOW()
        """
        cursor.execute(sql, (
            job_name, company, date_from, date_to, model, cron_schedule,
            enabled, report_types_json, report_categories_json
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"Error inserting scheduled job: {e}")
        return None


def get_scheduled_job(job_name: str) -> Optional[Dict]:
    """Get scheduled job by name"""
    try:
        sql = "SELECT * FROM scheduled_jobs WHERE job_name = %s"
        cursor.execute(sql, (job_name,))
        result = cursor.fetchone()
        
        if result:
            # Parse JSON fields
            if result['report_types']:
                result['report_types'] = json.loads(result['report_types'])
            if result['report_categories']:
                result['report_categories'] = json.loads(result['report_categories'])
        
        return result
    except Exception as e:
        print(f"Error fetching scheduled job: {e}")
        return None


def get_all_scheduled_jobs(enabled_only: bool = False) -> List[Dict]:
    """Get all scheduled jobs"""
    try:
        sql = "SELECT * FROM scheduled_jobs"
        if enabled_only:
            sql += " WHERE enabled = TRUE"
        sql += " ORDER BY job_name"
        
        cursor.execute(sql)
        results = cursor.fetchall()
        
        # Parse JSON fields
        for result in results:
            if result['report_types']:
                result['report_types'] = json.loads(result['report_types'])
            if result['report_categories']:
                result['report_categories'] = json.loads(result['report_categories'])
        
        return results
    except Exception as e:
        print(f"Error fetching scheduled jobs: {e}")
        return []


def update_job_run_stats(job_name: str, next_run: datetime = None):
    """Update job statistics after execution"""
    try:
        sql = """
            UPDATE scheduled_jobs
            SET 
                last_run = NOW(),
                next_run = %s,
                run_count = run_count + 1,
                updated_at = NOW()
            WHERE job_name = %s
        """
        cursor.execute(sql, (next_run, job_name))
        connection.commit()
    except Exception as e:
        connection.rollback()
        print(f"Error updating job stats: {e}")


def delete_scheduled_job(job_name: str):
    """Delete scheduled job"""
    try:
        sql = "DELETE FROM scheduled_jobs WHERE job_name = %s"
        cursor.execute(sql, (job_name,))
        connection.commit()
    except Exception as e:
        connection.rollback()
        print(f"Error deleting scheduled job: {e}")


# ============================================================================
# SUMMARY_REPORTS TABLE - Collective Reports Management
# ============================================================================

def insert_summary_report(
    job_name: str,
    company: str,
    date_from: str,
    date_to: str,
    report_count: int,
    document_count: int,
    file_path: str,
    file_format: str,
    file_size: int,
    model_used: str,
    summary_preview: str = None,
    tags: List[str] = None
) -> int:
    """Insert summary report record"""
    try:
        tags_json = json.dumps(tags) if tags else None
        
        sql = """
            INSERT INTO summary_reports
            (job_name, company, date_from, date_to, report_count,
             document_count, file_path, file_format, file_size,
             model_used, summary_preview, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            job_name, company, date_from, date_to, report_count,
            document_count, file_path, file_format, file_size,
            model_used, summary_preview, tags
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"Error inserting summary report: {e}")
        return None


def get_summary_reports(
    company: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """Get summary reports with filters"""
    ensure_connection()
    try:
        sql = "SELECT * FROM summary_reports WHERE 1=1"
        params = []
        
        if company:
            sql += " AND company = %s"
            params.append(company)
        
        if date_from:
            sql += " AND date_from >= %s"
            params.append(date_from)
        
        if date_to:
            sql += " AND date_to <= %s"
            params.append(date_to)
        
        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        
        # Parse JSON tags
        for result in results:
            if result['tags']:
                result['tags'] = json.loads(result['tags'])
        
        return results
    except Exception as e:
        print(f"Error fetching summary reports: {e}")
        return []


def get_summary_report_by_id(report_id: int) -> Optional[Dict]:
    """Get summary report by ID"""
    try:
        sql = "SELECT * FROM summary_reports WHERE id = %s"
        cursor.execute(sql, (report_id,))
        result = cursor.fetchone()
        
        if result and result['tags']:
            result['tags'] = json.loads(result['tags'])
        
        return result
    except Exception as e:
        print(f"Error fetching summary report: {e}")
        return None


# ============================================================================
# JOB_EXECUTION_LOG TABLE - Execution Audit Trail
# ============================================================================

def insert_job_execution(
    job_name: str,
    status: str = 'running'
) -> int:
    """Insert job execution log (start of execution)"""
    try:
        sql = """
            INSERT INTO job_execution_log
            (job_name, status, started_at)
            VALUES (%s, %s, NOW())
        """
        cursor.execute(sql, (job_name, status))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print(f"Error inserting job execution: {e}")
        return None


def update_job_execution(
    execution_id: int,
    status: str,
    reports_found: int = None,
    documents_processed: int = None,
    summary_report_id: int = None,
    error_message: str = None,
    log_file_path: str = None
):
    """Update job execution log (end of execution)"""
    try:
        sql = """
            UPDATE job_execution_log
            SET 
                status = %s,
                finished_at = NOW(),
                duration_seconds = TIMESTAMPDIFF(SECOND, started_at, NOW()),
                reports_found = %s,
                documents_processed = %s,
                summary_report_id = %s,
                error_message = %s,
                log_file_path = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            status, reports_found, documents_processed,
            summary_report_id, error_message, log_file_path,
            execution_id
        ))
        connection.commit()
    except Exception as e:
        connection.rollback()
        print(f"Error updating job execution: {e}")


def get_job_execution_logs(job_name: str = None, limit: int = 50) -> List[Dict]:
    """Get job execution logs"""
    try:
        sql = "SELECT * FROM job_execution_log WHERE 1=1"
        params = []
        
        if job_name:
            sql += " AND job_name = %s"
            params.append(job_name)
        
        sql += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching execution logs: {e}")
        return []


# ============================================================================
# DATABASE VIEWS - Quick Access Helpers
# ============================================================================

def get_active_jobs_view() -> List[Dict]:
    """Get active jobs from v_active_jobs view"""
    ensure_connection()
    try:
        sql = "SELECT * FROM v_active_jobs"
        cursor.execute(sql)
        results = cursor.fetchall()
        
        # Parse JSON fields
        for result in results:
            if result.get('report_types'):
                result['report_types'] = json.loads(result['report_types'])
            if result.get('report_categories'):
                result['report_categories'] = json.loads(result['report_categories'])
        
        return results
    except Exception as e:
        print(f"Error fetching active jobs view: {e}")
        return []


def get_company_stats_view() -> List[Dict]:
    """Get company statistics from v_company_stats view"""
    try:
        sql = "SELECT * FROM v_company_stats ORDER BY total_reports DESC"
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching company stats view: {e}")
        return []



# ============================================================================
# MODULE CLEANUP
# ============================================================================

def close_connection():
    """Close database connection"""
    global connection, cursor
    if cursor:
        cursor.close()
    if connection:
        connection.close()


if __name__ == "__main__":
    print("Database Connection Module v2.0")
    print(f"Connected to: {DATABASE}")
    print(f"Available tables: companies, reports, search_history,")
    print(f"                  scheduled_jobs, summary_reports,")
    print(f"                  job_execution_log, downloaded_files")
    
    # Test connection
    companies = get_all_companies()
    print(f"\nFound {len(companies)} companies in database")
    for company in companies:
        print(f"  - {company['name']}")
