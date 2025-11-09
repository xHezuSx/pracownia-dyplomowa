"""
PDF Report Generator Module
Handles Markdown report generation and PDF conversion.
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_connection import insert_summary_report

# Use absolute path based on script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))


def generate_summary_report(
    job_name: str,
    company: str,
    date: str,
    report_df: pd.DataFrame,
    summaries: str,
    model_name: str,
    downloaded_files_count: int,
    collective_summary: str = None
) -> Tuple[str, str]:
    """
    Generate comprehensive report in Markdown format and convert to PDF.
    Uses LLM-generated meta-summary for executive overview.
    
    Report structure:
    1. Header with metadata
    2. Collective summary (LLM-generated meta-analysis)
    3. Table of all reports
    4. Individual detailed summaries
    
    Args:
        job_name: Job identifier for database tracking
        company: Company name
        date: Date range or empty string
        report_df: DataFrame with all scraped reports
        summaries: Individual document summaries (text)
        model_name: AI model used for summarization
        downloaded_files_count: Number of downloaded files
        collective_summary: Pre-generated collective summary (optional)
    
    Returns:
        Tuple of (file_path, collective_summary)
    """
    # Create summary reports directory
    summary_dir = os.path.join(ROOT_DIR, "SUMMARY_REPORTS")
    os.makedirs(summary_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company}_{timestamp}_summary.md"
    filepath = os.path.join(summary_dir, filename)
    
    # Parse date range
    date_from_str = "N/A"
    date_to_str = "N/A"
    if date and " - " in date:
        parts = date.split(" - ")
        date_from_str = parts[0].strip()
        date_to_str = parts[1].strip()
    elif date:
        date_from_str = date_to_str = date
    
    # Generate Markdown report
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Zbiorczy Raport GPW - {company}\n\n")
        f.write(f"**Wygenerowano:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")
        
        # Metadata section
        f.write(f"## 📊 Informacje o raporcie\n\n")
        f.write(f"- **Firma:** {company}\n")
        f.write(f"- **Okres:** {date_from_str} - {date_to_str}\n")
        f.write(f"- **Liczba raportów:** {len(report_df)}\n")
        f.write(f"- **Pobranych plików:** {downloaded_files_count}\n")
        f.write(f"- **Model AI:** {model_name}\n\n")
        f.write(f"---\n\n")
        
        # Collective summary (LLM meta-analysis)
        f.write(f"## 📝 Zbiorczy Raport (Analiza LLM)\n\n")
        f.write(collective_summary if collective_summary else "*Brak zbiorczego podsumowania*")
        f.write("\n\n")
        f.write(f"---\n\n")
        
        # Reports table
        f.write(f"## 📋 Lista raportów\n\n")
        if not report_df.empty:
            f.write(report_df.to_markdown(index=False))
            f.write("\n\n")
        else:
            f.write("*Brak raportów*\n\n")
        
        f.write(f"---\n\n")
        
        # Individual AI summaries (detailed)
        f.write(f"## 🤖 Szczegółowe Podsumowania Dokumentów (AI)\n\n")
        f.write(summaries)
        f.write("\n\n")
        
        f.write(f"---\n\n")
        f.write(f"*Raport wygenerowany automatycznie przez GPW Scraper*\n")
    
    print(f"\n✅ Zbiorczy raport zapisany: {filepath}")
    
    # Convert MD → PDF
    try:
        import markdown
        from weasyprint import HTML
        
        print(f"🔄 Konwersja MD → PDF...")
        
        # Load markdown
        with open(filepath, 'r', encoding='utf-8') as f:
            md_text = f.read()
        
        # Convert MD → HTML
        html_text = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
        
        # Professional CSS styling
        css_style = """
        <style>
            @page {
                size: A4;
                margin: 15mm;
            }
            body {
                font-family: 'DejaVu Sans', Arial, sans-serif;
                line-height: 1.4;
                margin: 0;
                padding: 0;
                color: #333;
                font-size: 10pt;
            }
            h1 { 
                color: #2c3e50; 
                border-bottom: 3px solid #3498db; 
                padding-bottom: 8px;
                font-size: 16pt;
                margin-top: 10px;
            }
            h2 { 
                color: #34495e; 
                border-bottom: 2px solid #95a5a6; 
                padding-bottom: 6px; 
                margin-top: 20px;
                font-size: 13pt;
            }
            h3 { 
                color: #7f8c8d;
                font-size: 11pt;
                margin-top: 15px;
            }
            
            /* Responsive table styling */
            table { 
                border-collapse: collapse; 
                width: 100%; 
                margin: 15px 0;
                font-size: 8pt;
                table-layout: fixed;
            }
            th, td { 
                border: 1px solid #ddd; 
                padding: 4px 6px;
                text-align: left;
                word-wrap: break-word;
                overflow-wrap: break-word;
                hyphens: auto;
            }
            th { 
                background-color: #3498db; 
                color: white;
                font-weight: bold;
                font-size: 8pt;
            }
            tr:nth-child(even) { 
                background-color: #f2f2f2; 
            }
            
            /* Break long URLs and words */
            td {
                word-break: break-word;
                max-width: 0;
            }
            
            code { 
                background-color: #ecf0f1; 
                padding: 1px 4px; 
                border-radius: 2px;
                font-size: 8pt;
            }
            hr { 
                border: 0; 
                height: 1px; 
                background: #bdc3c7; 
                margin: 20px 0; 
            }
            
            /* Better paragraph spacing */
            p {
                margin: 8px 0;
                line-height: 1.4;
            }
        </style>
        """
        
        full_html = f"<html><head><meta charset='utf-8'>{css_style}</head><body>{html_text}</body></html>"
        
        # Generate PDF
        filepath_pdf = filepath.replace('.md', '.pdf')
        HTML(string=full_html).write_pdf(filepath_pdf)
        
        # Verify PDF creation
        if os.path.exists(filepath_pdf):
            print(f"✅ PDF wygenerowany: {filepath_pdf}")
            filepath = filepath_pdf
            file_format = 'pdf'
            file_size = os.path.getsize(filepath_pdf)
        else:
            raise FileNotFoundError(f"PDF nie został utworzony: {filepath_pdf}")
        
    except Exception as e:
        print(f"⚠️  Błąd konwersji do PDF: {e}")
        import traceback
        traceback.print_exc()
        print(f"   Raport pozostanie w formacie MD")
        file_format = 'markdown'
        file_size = os.path.getsize(filepath)
    
    # Save metadata to database
    try:
        insert_summary_report(
            job_name=job_name,
            company=company,
            date_from=date_from_str if date_from_str != "N/A" else None,
            date_to=date_to_str if date_to_str != "N/A" else None,
            report_count=len(report_df),
            document_count=downloaded_files_count,
            file_path=filepath,
            file_format=file_format,
            file_size=file_size,
            model_used=model_name,
            summary_preview=collective_summary[:200] if collective_summary else None,
            tags=[company.lower(), job_name.replace("_", "-")]
        )
        print(f"✅ Metadata zapisane do bazy danych")
    except Exception as e:
        print(f"⚠️  Błąd zapisu do bazy: {e}")
    
    return filepath, collective_summary or ""


def generate_markdown_report(
    company: str,
    date: str,
    report_df: pd.DataFrame,
    summaries: str,
    model_name: str,
    downloaded_files_count: int,
    collective_summary: str = None
) -> str:
    """
    Generate Markdown report without database integration.
    
    Lightweight version for testing or standalone use.
    
    Args:
        company: Company name
        date: Date range
        report_df: Reports DataFrame
        summaries: Individual summaries
        model_name: AI model name
        downloaded_files_count: Files count
        collective_summary: Meta-summary
    
    Returns:
        Path to generated Markdown file
    """
    summary_dir = os.path.join(ROOT_DIR, "SUMMARY_REPORTS")
    os.makedirs(summary_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company}_{timestamp}_summary.md"
    filepath = os.path.join(summary_dir, filename)
    
    date_from_str = "N/A"
    date_to_str = "N/A"
    if date and " - " in date:
        parts = date.split(" - ")
        date_from_str = parts[0].strip()
        date_to_str = parts[1].strip()
    elif date:
        date_from_str = date_to_str = date
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Zbiorczy Raport GPW - {company}\n\n")
        f.write(f"**Wygenerowano:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")
        
        f.write(f"## 📊 Informacje o raporcie\n\n")
        f.write(f"- **Firma:** {company}\n")
        f.write(f"- **Okres:** {date_from_str} - {date_to_str}\n")
        f.write(f"- **Liczba raportów:** {len(report_df)}\n")
        f.write(f"- **Pobranych plików:** {downloaded_files_count}\n")
        f.write(f"- **Model AI:** {model_name}\n\n")
        f.write(f"---\n\n")
        
        f.write(f"## 📝 Zbiorczy Raport (Analiza LLM)\n\n")
        f.write(collective_summary if collective_summary else "*Brak zbiorczego podsumowania*")
        f.write("\n\n---\n\n")
        
        f.write(f"## 📋 Lista raportów\n\n")
        if not report_df.empty:
            f.write(report_df.to_markdown(index=False))
            f.write("\n\n")
        else:
            f.write("*Brak raportów*\n\n")
        
        f.write(f"---\n\n")
        
        f.write(f"## 🤖 Szczegółowe Podsumowania Dokumentów (AI)\n\n")
        f.write(summaries)
        f.write("\n\n---\n\n")
        f.write(f"*Raport wygenerowany automatycznie przez GPW Scraper*\n")
    
    print(f"\n✅ Markdown raport zapisany: {filepath}")
    return filepath
