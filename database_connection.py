"""
Database Connection Module v2.0 - English Unified Structure
Supports: companies, reports, search_history, scheduled_jobs, 
          summary_reports, job_execution_log, downloaded_files
Thread-safe with thread-local connections.
"""

import os
import pymysql
import hashlib
import json
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection settings from environment variables
HOST = os.getenv("DB_HOST", "localhost")
USER = os.getenv("DB_USER", "user")
PASSWORD = os.getenv("DB_PASSWORD", "qwerty123")
DATABASE = os.getenv("DB_NAME", "gpw data")

# Thread-local storage for connections
_thread_local = threading.local()

def get_connection():
    """Get thread-local database connection"""
    if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
        try:
            _thread_local.connection = pymysql.connect(
                host=HOST,
                user=USER,
                password=PASSWORD,
                database=DATABASE,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,
                charset='utf8mb4'
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            _thread_local.connection = None
    return _thread_local.connection

def get_cursor():
    """Get cursor for current thread's connection"""
    conn = get_connection()
    if conn is None:
        return None
    if not hasattr(_thread_local, 'cursor') or _thread_local.cursor is None:
        _thread_local.cursor = conn.cursor()
    return _thread_local.cursor

# Backward compatibility - connection and cursor as properties
@property
def connection():
    """Get current thread's connection (backward compatibility)"""
    return get_connection()

@property  
def cursor():
    """Get current thread's cursor (backward compatibility)"""
    return get_cursor()

# Actually, Python doesn't support module-level properties, so use simple reassignment
# This allows old code using `connection` and `cursor` to work
def _get_globals():
    """Update module globals for backward compatibility"""
    import sys
    current_module = sys.modules[__name__]
    current_module.connection = get_connection()
    current_module.cursor = get_cursor()
    return current_module.connection, current_module.cursor

def connect():
    """Establish database connection for current thread"""
    try:
        conn = get_connection()
        if conn:
            get_cursor()
            return True
        return False
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

def ensure_connection():
    """Ensure database connection is alive, reconnect if needed"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_connection()
            if conn is None:
                if connect():
                    return True
            else:
                # Test connection with ping
                conn.ping(reconnect=True)
                return True
        except Exception as e:
            # Connection failed, force reconnect
            try:
                conn = get_connection()
                if conn:
                    conn.close()
            except:
                pass
            _thread_local.connection = None
            _thread_local.cursor = None
            
            if attempt < max_retries - 1:
                # Try again
                continue
            else:
                # Final attempt
                return connect()
    
    return False


def execute_query(sql: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
    """
    Execute SQL query with automatic reconnect on packet sequence error.
    Thread-safe implementation using thread-local connections.
    
    Returns:
    - None if INSERT/UPDATE/DELETE
    - Single dict if fetch_one=True
    - List of dicts if fetch_all=True
    """
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            connection = get_connection()
            cursor = get_cursor()
            if not ensure_connection():
                raise Exception("Could not establish database connection")
            
            conn = get_connection()
            cursor = get_cursor()
            
            if conn is None or cursor is None:
                raise Exception("Database connection or cursor is not initialized")
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for packet sequence or connection errors
            if "packet sequence" in error_msg or "connection" in error_msg or "lost" in error_msg or "protocol" in error_msg:
                try:
                    conn = get_connection()
                    if conn:
                        conn.close()
                except:
                    pass
                _thread_local.connection = None
                _thread_local.cursor = None
                
                if attempt < max_retries - 1:
                    # Try to reconnect and retry
                    if connect():
                        continue
            
            # If we get here, it's a real error
            try:
                conn = get_connection()
                if conn:
                    conn.rollback()
            except:
                pass
            raise

# Note: Connections are now thread-local and created on-demand
# No need for global initialization

# ============================================================================
# COMPANIES TABLE - Company Management
# ============================================================================

def insert_company(name: str, full_name: str = None, sector: str = None) -> int:
    """Insert or get company ID"""
    ensure_connection()
    try:
        connection = get_connection()
        cursor = get_cursor()
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
        connection = get_connection()
        cursor = get_cursor()
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
        connection = get_connection()
        cursor = get_cursor()
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
        # Convert date format: if contains time (space), extract only date part
        if date and " " in date:
            date = date.split()[0]
        
        # Convert DD-MM-YYYY → YYYY-MM-DD for MySQL
        if date:
            try:
                connection = get_connection()
                cursor = get_cursor()
                date_obj = datetime.strptime(date, "%d-%m-%Y")
                date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                # If parsing fails, keep original format
                pass
        
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
        connection = get_connection()
        cursor = get_cursor()
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
        connection = get_connection()
        cursor = get_cursor()
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
        connection = get_connection()
        cursor = get_cursor()
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
        connection = get_connection()
        cursor = get_cursor()
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
    ensure_connection()
    try:
        connection = get_connection()
        cursor = get_cursor()
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


def get_downloaded_file_by_name(company: str, file_name: str) -> Optional[Dict]:
    """Get downloaded file by company and file name"""
    ensure_connection()
    try:
        connection = get_connection()
        cursor = get_cursor()
        sql = "SELECT * FROM downloaded_files WHERE company = %s AND file_name = %s LIMIT 1"
        cursor.execute(sql, (company, file_name))
        return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching file by name: {e}")
        return None


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
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = get_cursor()
        
        # Convert empty date string to None
        if not report_date or report_date.strip() == "":
            report_date = None
        else:
            # Extract date part if time is present
            if " " in report_date:
                report_date = report_date.split()[0]
            
            # Convert DD-MM-YYYY → YYYY-MM-DD for MySQL
            try:
                date_obj = datetime.strptime(report_date, "%d-%m-%Y")
                report_date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                # If parsing fails, keep original format
                pass
        
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
        if connection:
            try:
                connection.rollback()
            except:
                pass
        print(f"Error inserting search history: {e}")
        return None


def get_search_history(limit: int = 50) -> List[Dict]:
    """Get recent search history"""
    ensure_connection()
    try:
        connection = get_connection()
        cursor = get_cursor()
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
    report_limit: int = 5,
    report_types: List[str] = None,
    report_categories: List[str] = None
) -> int:
    """Insert or update scheduled job"""
    try:
        # Ensure report_limit column exists (compatibility with older schema)
        try:
            execute_query(
                "ALTER TABLE scheduled_jobs ADD COLUMN report_limit INT DEFAULT 5 AFTER cron_schedule",
                timeout=2
            )
        except:
            pass  # Column already exists or error occurred
        
        # Convert date format from DD-MM-YYYY to YYYY-MM-DD
        def convert_date(date_str):
            if not date_str:
                return None
            if '-' in date_str and len(date_str) == 10:
                parts = date_str.split('-')
                if len(parts[0]) == 2:  # DD-MM-YYYY
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return date_str
        
        date_from = convert_date(date_from)
        date_to = convert_date(date_to)
        
        # Convert lists to JSON
        report_types_json = json.dumps(report_types) if report_types else None
        report_categories_json = json.dumps(report_categories) if report_categories else None
        
        sql = """
            INSERT INTO scheduled_jobs
            (job_name, company, date_from, date_to, model, cron_schedule,
             enabled, report_limit, report_types, report_categories)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                company = VALUES(company),
                date_from = VALUES(date_from),
                date_to = VALUES(date_to),
                model = VALUES(model),
                cron_schedule = VALUES(cron_schedule),
                enabled = VALUES(enabled),
                report_limit = VALUES(report_limit),
                report_types = VALUES(report_types),
                report_categories = VALUES(report_categories),
                updated_at = NOW()
        """
        
        result = execute_query(sql, (
            job_name, company, date_from, date_to, model, cron_schedule,
            enabled, report_limit, report_types_json, report_categories_json
        ))
        
        return result if result else 0
    except Exception as e:
        print(f"Error inserting scheduled job: {e}")
        # Try again without report_limit column (backward compatibility)
        try:
            sql_fallback = """
                INSERT INTO scheduled_jobs
                (job_name, company, date_from, date_to, model, cron_schedule, enabled, report_types, report_categories)
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
            result = execute_query(sql_fallback, (
                job_name, company, date_from, date_to, model, cron_schedule,
                enabled, report_types_json, report_categories_json
            ))
            print(f"✅ Saved job without report_limit column (backward compat)")
            return result if result else 0
        except Exception as e2:
            print(f"Error (fallback also failed): {e2}")
            raise e


def get_scheduled_job(job_name: str) -> Optional[Dict]:
    """Get scheduled job by name"""
    ensure_connection()
    try:
        connection = get_connection()
        cursor = get_cursor()
        sql = "SELECT * FROM scheduled_jobs WHERE job_name = %s"
        cursor.execute(sql, (job_name,))
        result = cursor.fetchone()
        
        if result:
            # Parse JSON fields
            if result['report_types']:
                result['report_types'] = json.loads(result['report_types'])
            if result['report_categories']:
                result['report_categories'] = json.loads(result['report_categories'])
            
            # Set default for report_limit if column doesn't exist
            if 'report_limit' not in result or result['report_limit'] is None:
                result['report_limit'] = 5
        
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
        
        results = execute_query(sql, fetch_all=True)
        
        # Parse JSON fields
        if results:
            for result in results:
                if result.get('report_types'):
                    result['report_types'] = json.loads(result['report_types'])
                if result.get('report_categories'):
                    result['report_categories'] = json.loads(result['report_categories'])
        
        return results if results else []
    except Exception as e:
        print(f"Error fetching scheduled jobs: {e}")
        return []


def update_job_run_stats(job_name: str, next_run: datetime = None):
    """Update job statistics after execution"""
    try:
        connection = get_connection()
        cursor = get_cursor()
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
        connection = get_connection()
        cursor = get_cursor()
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
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = get_cursor()
        
        tags_json = json.dumps(tags) if tags else None
        
        # Convert DD-MM-YYYY → YYYY-MM-DD for MySQL (if needed)
        def convert_date(date_str):
            if not date_str or date_str == "N/A":
                return None
            if " " in date_str:
                date_str = date_str.split()[0]
            try:
                date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                return date_str
        
        date_from = convert_date(date_from)
        date_to = convert_date(date_to)
        
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
            model_used, summary_preview, tags_json
        ))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        if connection:
            try:
                connection.rollback()
            except:
                pass
        print(f"Error inserting summary report: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_summary_reports(
    company: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """Get summary reports with filters"""
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
        
        results = execute_query(sql, tuple(params), fetch_all=True)
        
        # Parse JSON tags
        if results:
            for result in results:
                if result.get('tags'):
                    result['tags'] = json.loads(result['tags'])
        
        return results if results else []
    except Exception as e:
        print(f"Error fetching summary reports: {e}")
        return []


def get_summary_report_by_id(report_id: int) -> Optional[Dict]:
    """Get summary report by ID"""
    ensure_connection()
    try:
        connection = get_connection()
        cursor = get_cursor()
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
        connection = get_connection()
        cursor = get_cursor()
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
        connection = get_connection()
        cursor = get_cursor()
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
        
        results = execute_query(sql, tuple(params), fetch_all=True)
        return results if results else []
    except Exception as e:
        print(f"Error fetching execution logs: {e}")
        return []


# ============================================================================
# DATABASE VIEWS - Quick Access Helpers
# ============================================================================

def get_active_jobs_view() -> List[Dict]:
    """Get active jobs from v_active_jobs view"""
    try:
        sql = "SELECT * FROM v_active_jobs"
        results = execute_query(sql, fetch_all=True)
        
        # Parse JSON fields
        if results:
            for result in results:
                if result.get('report_types'):
                    result['report_types'] = json.loads(result['report_types'])
                if result.get('report_categories'):
                    result['report_categories'] = json.loads(result['report_categories'])
        
        return results if results else []
    except Exception as e:
        print(f"Error fetching active jobs view: {e}")
        return []


def get_company_stats_view() -> List[Dict]:
    """Get company statistics from v_company_stats view"""
    try:
        connection = get_connection()
        cursor = get_cursor()
        sql = "SELECT * FROM v_company_stats ORDER BY total_reports DESC"
        results = execute_query(sql, fetch_all=True)
        return results if results else []
    except Exception as e:
        print(f"Error fetching company stats view: {e}")
        return []



# ============================================================================
# MODULE CLEANUP
# ============================================================================

def close_connection():
    """Close database connection for current thread"""
    try:
        connection = get_connection()
        cursor = get_cursor()
        cursor = get_cursor()
        if cursor:
            cursor.close()
    except:
        pass
    
    try:
        conn = get_connection()
        if conn:
            conn.close()
    except:
        pass
    
    _thread_local.connection = None
    _thread_local.cursor = None


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
