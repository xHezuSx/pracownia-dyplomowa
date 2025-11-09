"""
History Repository
CRUD operations for search_history and summary_reports tables.
"""

import json
from typing import Optional, List, Dict
from datetime import datetime
from ..connection import get_connection, get_cursor, ensure_connection, execute_query


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
) -> Optional[int]:
    """
    Insert search history record.
    
    Args:
        company_name: Company ticker/name
        report_amount: Number of reports searched
        download_type: Type of download operation
        report_date: Search date (DD-MM-YYYY or YYYY-MM-DD)
        report_type: Report type filter
        report_category: Category filter
        model_used: AI model used
        execution_time: Operation duration in seconds
    
    Returns:
        int: History ID or None on error
    """
    ensure_connection()
    connection = None
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
    """
    Get recent search history.
    
    Args:
        limit: Maximum number of results
    
    Returns:
        List[Dict]: List of search history records
    """
    ensure_connection()
    try:
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
) -> Optional[int]:
    """
    Insert summary report record.
    
    Args:
        job_name: Associated job name
        company: Company ticker/name
        date_from: Start date of report period
        date_to: End date of report period
        report_count: Number of reports included
        document_count: Number of documents processed
        file_path: Path to generated PDF report
        file_format: File format (pdf, md, etc.)
        file_size: File size in bytes
        model_used: AI model used for summarization
        summary_preview: Short preview text
        tags: List of tags for categorization
    
    Returns:
        int: Summary report ID or None on error
    """
    connection = None
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
    """
    Get summary reports with filters.
    
    Args:
        company: Filter by company name
        date_from: Filter by start date
        date_to: Filter by end date
        limit: Maximum number of results
    
    Returns:
        List[Dict]: List of summary report records with parsed JSON tags
    """
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
    """
    Get summary report by ID.
    
    Args:
        report_id: Summary report ID
    
    Returns:
        Dict: Summary report record with parsed JSON tags or None if not found
    """
    ensure_connection()
    try:
        cursor = get_cursor()
        sql = "SELECT * FROM summary_reports WHERE id = %s"
        cursor.execute(sql, (report_id,))
        result = cursor.fetchone()
        
        if result and result.get('tags'):
            result['tags'] = json.loads(result['tags'])
        
        return result
    except Exception as e:
        print(f"Error fetching summary report: {e}")
        return None


# ============================================================================
# DATABASE VIEWS - Quick Access Helpers
# ============================================================================

def get_company_stats_view() -> List[Dict]:
    """
    Get company statistics from v_company_stats view.
    
    Returns:
        List[Dict]: List of company statistics records
    """
    try:
        sql = "SELECT * FROM v_company_stats ORDER BY total_reports DESC"
        results = execute_query(sql, fetch_all=True)
        return results if results else []
    except Exception as e:
        print(f"Error fetching company stats view: {e}")
        return []
