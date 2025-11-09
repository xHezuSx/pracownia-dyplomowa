"""
Main Scraper Script - Backward Compatibility Wrapper
Orchestrates GPW web scraping using modular core components.
"""

import os
import pandas as pd
from typing import Tuple, Optional

from src.core.scraper import (
    scrape_gpw_reports, get_attachments, map_report_type_to_enum,
    map_report_category_to_enum, download_file, get_file_name
)
from src.core.summarizer import get_summaries, generate_collective_summary_with_llm
from src.core.pdf_generator import generate_summary_report
from database_connection import (
    insert_company, get_company_id, insert_report, insert_downloaded_file,
    file_exists_by_md5, calculate_md5, insert_search_history
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_PATH = os.path.join(SCRIPT_DIR, "REPORTS")


def scrape(company, limit, date, report_type, report_category, download_csv, 
           download_file_types, model_name="llama3.2:latest", job_name="manual"):
    """Main scraping orchestrator - coordinates all scraping operations."""
    empty_df = pd.DataFrame(columns=["date", "title", "report type", "report category",
                                      "exchange rate", "rate change", "link"])
    
    # Validate company name
    if not company or not isinstance(company, str) or company.strip() == "":
        return "Error: Company name is required", empty_df, "", None, None, []
    
    report_df, error_msg = scrape_gpw_reports(company, limit, date, report_type, report_category)
    if error_msg:
        return error_msg, empty_df, "", None, None, []
    
    insert_search_history(company, limit, " ".join(download_file_types), date,
                         " ".join(report_type) if report_type else None,
                         " ".join(report_category) if report_category else None)
    
    company_id = insert_company(company.lower()) or get_company_id(company.lower())
    
    report_ids = []
    for _, row in report_df.iterrows():
        report_id = insert_report(
            company_id, row['date'], row['title'],
            map_report_type_to_enum(row['report type']),
            map_report_category_to_enum(row['report category']),
            row['exchange rate'], row['rate change'], row['link']
        )
        report_ids.append(report_id)
    
    os.makedirs(REPORTS_PATH, exist_ok=True)
    company_dir = os.path.join(REPORTS_PATH, company)
    if_downloaded = False
    
    if not os.path.exists(company_dir) and (len(download_file_types) or download_csv):
        os.makedirs(company_dir)
        if_downloaded = True
    
    downloaded_file_names = []
    downloaded_files = 0
    
    if download_file_types:
        for i, link in enumerate(report_df['link']):
            attachments, file_titles = get_attachments(link, download_file_types)
            for j, (url, name) in enumerate(zip(attachments, file_titles)):
                filename = get_file_name(i+1, j+1, company, name)
                file_path = os.path.join(REPORTS_PATH, company, filename)
                downloaded_file_names.append(filename)
                download_file(url, file_path)
                downloaded_files += 1
                
                try:
                    md5 = calculate_md5(file_path)
                    if md5 and not file_exists_by_md5(md5):
                        insert_downloaded_file(
                            company.lower(), report_ids[i] if i < len(report_ids) else None,
                            filename, file_path, filename.split('.')[-1].lower(),
                            os.path.getsize(file_path), md5, False
                        )
                        print(f"✓ Plik: {filename}")
                except Exception as e:
                    print(f"⚠ Błąd: {e}")
    
    output_info = f"downloaded {downloaded_files} files " if downloaded_files else ""
    
    if download_csv:
        report_df.to_csv(os.path.join(REPORTS_PATH, company, f"{company}({limit}) report.csv"))
        if_downloaded = True
        output_info += "| CSV saved"
    
    summaries = "*No documents to summarize*"
    collective_summary = None
    
    if "PDF" in download_file_types or "HTML" in download_file_types:
        summaries = get_summaries(downloaded_file_names, company, model_name)
        if summaries != "*No documents to summarize*":
            collective_summary = generate_collective_summary_with_llm(summaries, company, model_name)
    
    summary_report_path = None
    if summaries != "*No documents to summarize*" and downloaded_file_names:
        summary_report_path, collective_summary = generate_summary_report(
            job_name, company, date, report_df, summaries, model_name,
            len(downloaded_file_names), collective_summary
        )
    
    if if_downloaded:
        return (f"SUCCESS! {output_info}\n files saved in:\n\t\t {os.path.join(os.getcwd(), 'REPORTS', company)}",
                report_df, summaries, summary_report_path, collective_summary, downloaded_file_names)
    
    return f"SUCCESS! {output_info}", report_df, summaries, summary_report_path, collective_summary, []


if __name__ == "__main__":
    print("✅ scrape_script.py wrapper ready")
