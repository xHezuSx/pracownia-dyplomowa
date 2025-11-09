#!/usr/bin/env python3
"""
Skrypt wykonawczy dla zadań cron.
Uruchamia scraping na podstawie konfiguracji i zapisuje wyniki.
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Dodaj katalog projektu do PYTHONPATH
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

from config_manager import ConfigManager
from scrape_script import scrape
from database_connection import (
    insert_job_execution,
    update_job_execution,
    update_job_run_stats
)


def log(message: str):
    """Loguje wiadomość z timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def run_job(job_name: str) -> bool:
    """
    Wykonuje zadanie scrapingu na podstawie konfiguracji.
    
    Args:
        job_name: Nazwa zadania z pliku konfiguracyjnego
        
    Returns:
        True jeśli sukces, False w przypadku błędu
    """
    log(f"🚀 Rozpoczynam zadanie: {job_name}")
    
    # Wczytaj konfigurację
    manager = ConfigManager()
    config = manager.load_config(job_name)
    
    if not config:
        log(f"❌ Nie znaleziono konfiguracji: {job_name}")
        return False
    
    if not config.enabled:
        log(f"⏸️  Zadanie wyłączone: {job_name}")
        return False
    
    log(f"📋 Konfiguracja:")
    log(f"   Firma: {config.company}")
    log(f"   Okres: {config.date_from} - {config.date_to}")
    log(f"   Model: {config.model}")
    
    # Initialize execution log in database (v2.0)
    execution_id = None
    summary_report_id = None
    reports_found = 0
    documents_processed = 0
    
    try:
        # Start execution logging
        execution_id = insert_job_execution(job_name, status='running')
        log(f"📊 Execution logged to database (ID: {execution_id})")
        
        # Wykonaj scraping
        log(f"🔍 Rozpoczynam scraping...")
        
        result = scrape(
            company=config.company,
            limit=100,  # Domyślny limit wyników
            date=f"{config.date_from} - {config.date_to}",
            report_type=["current", "quarterly", "semi-annual", "annual"],  # Wszystkie typy
            report_category=["ESPI", "EBI"],  # Wszystkie kategorie
            download_csv=False,
            download_file_types=["PDF", "HTML"],  # PDF i HTML
            model_name=config.model,
            job_name=job_name  # Przekaż nazwę zadania
        )
        
        # scrape() zwraca tuple: (summary_text, dataframe, attachments, summary_report_path)
        summary_text, df, attachments, summary_report_path = result
        
        # Count processed items
        reports_found = len(df) if df is not None else 0
        documents_processed = len(attachments) if attachments else 0
        
        # Extract summary_report_id from database if summary was created
        # (insert_summary_report in scrape_script returns the ID)
        # For now we'll query by job_name + timestamp (TODO: improve this)
        
        # Zapisz wyniki do pliku
        output_dir = os.path.join(project_dir, "scheduled_results")
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(
            output_dir,
            f"{job_name}_{timestamp}.txt"
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Raport GPW - {config.company}\n")
            f.write(f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Okres: {config.date_from} - {config.date_to}\n")
            f.write(f"Model: {config.model}\n")
            f.write("="*80 + "\n\n")
            f.write(summary_text)  # Używamy rozpakowanego summary_text
            f.write("\n\n" + "="*80 + "\n")
            f.write(f"Znaleziono {len(attachments)} załączników\n")
        
        log(f"✅ Wynik zapisany: {output_file}")
        
        # Update execution log with success (v2.0)
        if execution_id:
            update_job_execution(
                execution_id=execution_id,
                status='success',
                reports_found=reports_found,
                documents_processed=documents_processed,
                summary_report_id=summary_report_id,
                log_file_path=output_file
            )
            log(f"📊 Execution log updated: {reports_found} reports, {documents_processed} documents")
        
        # Update job statistics
        update_job_run_stats(job_name)
        
        # TODO: Opcjonalnie wyślij email jeśli config.email_notify jest ustawione
        if config.email_notify:
            log(f"📧 Email powiadomienie: {config.email_notify} (nie zaimplementowane)")
        
        log(f"✅ Zadanie zakończone pomyślnie")
        return True
        
    except Exception as e:
        log(f"❌ Błąd podczas wykonywania zadania: {e}")
        
        # Update execution log with error (v2.0)
        if execution_id:
            update_job_execution(
                execution_id=execution_id,
                status='error',
                reports_found=reports_found,
                documents_processed=documents_processed,
                error_message=str(e)
            )
            log(f"📊 Execution error logged to database")
        
        import traceback
        traceback.print_exc()
        return False


def main():
    """Główna funkcja skryptu."""
    if len(sys.argv) < 2:
        print("Użycie: python run_scheduled.py <nazwa_zadania>")
        print("\nDostępne zadania:")
        manager = ConfigManager()
        for config in manager.list_configs():
            status = "✓" if config.enabled else "✗"
            print(f"  [{status}] {config.job_name} - {config.description}")
        sys.exit(1)
    
    job_name = sys.argv[1]
    
    log("="*80)
    log(f"GPW Scraper - Automatyczne zadanie")
    log("="*80)
    
    success = run_job(job_name)
    
    log("="*80)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
