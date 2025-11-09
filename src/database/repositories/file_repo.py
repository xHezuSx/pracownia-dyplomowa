"""
File Repository
CRUD operations for downloaded_files table with MD5 deduplication.
"""

import hashlib
from typing import Optional, List, Dict
from ..connection import get_connection, get_cursor, ensure_connection


def calculate_md5(file_path: str) -> Optional[str]:
    """
    Calculate MD5 hash of a file.
    
    Args:
        file_path: Absolute path to file
    
    Returns:
        str: MD5 hash hexdigest or None on error
    """
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
    """
    Check if file already exists by MD5 hash (deduplication).
    
    Args:
        md5_hash: MD5 hash to check
    
    Returns:
        bool: True if file exists, False otherwise
    """
    try:
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
) -> Optional[int]:
    """
    Insert downloaded file record with MD5 deduplication check.
    
    Args:
        company: Company name/ticker
        report_id: Foreign key to reports table
        file_name: Original filename
        file_path: Absolute path to stored file
        file_type: File extension (pdf, zip, etc.)
        file_size: File size in bytes
        md5_hash: MD5 hash for deduplication
        is_summarized: Whether file has been summarized
        summary_text: AI-generated summary (optional)
    
    Returns:
        int: File ID or None if duplicate or error
    """
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
        connection = get_connection()
        if connection:
            connection.rollback()
        print(f"Error inserting downloaded file: {e}")
        return None


def update_file_summary(file_id: int, summary_text: str):
    """
    Update file summary after AI processing.
    
    Args:
        file_id: File ID to update
        summary_text: Generated summary text
    """
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
        connection = get_connection()
        if connection:
            connection.rollback()
        print(f"Error updating file summary: {e}")


def get_downloaded_files(company: str = None, is_summarized: bool = None) -> List[Dict]:
    """
    Get downloaded files with optional filters.
    
    Args:
        company: Filter by company name
        is_summarized: Filter by summarization status
    
    Returns:
        List[Dict]: List of file records
    """
    ensure_connection()
    try:
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
    """
    Get downloaded file by company and file name.
    
    Args:
        company: Company name/ticker
        file_name: File name to search for
    
    Returns:
        Dict: File record or None if not found
    """
    ensure_connection()
    try:
        cursor = get_cursor()
        sql = "SELECT * FROM downloaded_files WHERE company = %s AND file_name = %s LIMIT 1"
        cursor.execute(sql, (company, file_name))
        return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching file by name: {e}")
        return None
