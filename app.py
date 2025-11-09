#!/usr/bin/env python3
"""
GPW Scraper - Główny interfejs użytkownika
============================================

Aplikacja Gradio do scrapingu i automatyzacji raportów z GPW.

Funkcje:
- 🔍 Ręczny scraping raportów giełdowych
- ⏰ Automatyzacja z harmonogramem cron  
- 📊 Podsumowania AI (Ollama + K-means clustering)
- 💾 Historia wyszukiwań (MySQL)

Uruchomienie:
    python app.py
"""

import gradio as gr
from scrape_script import scrape
from database_connection import get_search_history
from datetime import datetime
from ollama_manager import (
    get_available_models,
    get_installed_models,
    is_model_installed,
    pull_model,
    get_model_display_name,
)
import pandas as pd
import os

# Funkcje harmonogramu
from config_manager import (
    ConfigManager,
    ScrapingConfig,
)
from cron_manager import CronManager


# ============================================================================
# ZAKŁADKA 1: SCRAPING - Funkcje pomocnicze
# ============================================================================

def run_scrape_ui(
    company_name,
    report_amount,
    date_obj,
    report_types,
    categories,
    download_checkbox,
    download_types_file,
    selected_model,
):
    """Wrapper dla funkcji scrape z automatycznym pobieraniem modeli."""
    if not date_obj:
        date_str = ""
    else:
        try:
            if isinstance(date_obj, str):
                parsed = datetime.fromisoformat(date_obj)
            else:
                parsed = date_obj
            date_str = parsed.strftime("%d-%m-%Y")
        except Exception:
            date_str = ""
    
    # Wyciągnij nazwę modelu (usuń markery ✓ / ○)
    model_name = selected_model.split(" (")[0].replace("✓ ", "").replace("○ ", "")
    
    # Sprawdź czy model jest zainstalowany
    if not is_model_installed(model_name):
        yield (
            f"Model {model_name} nie jest zainstalowany. Rozpoczynam pobieranie...\n"
            f"To może zająć kilka minut w zależności od rozmiaru modelu.",
            pd.DataFrame(
                columns=[
                    "date",
                    "title",
                    "report type",
                    "report category",
                    "exchange rate",
                    "rate change",
                    "link",
                ]
            ),
            "*Pobieranie modelu...*",
        )
        
        progress_text = ""
        def progress_callback(line):
            nonlocal progress_text
            progress_text += line + "\n"
        
        success, message = pull_model(model_name, progress_callback)
        
        if not success:
            yield (
                f"Błąd pobierania modelu:\n{message}",
                pd.DataFrame(
                    columns=[
                        "date",
                        "title",
                        "report type",
                        "report category",
                        "exchange rate",
                        "rate change",
                        "link",
                    ]
                ),
                "*Pobieranie nieudane*",
            )
            return
        
        yield (
            f"Model {model_name} został pobrany pomyślnie!\nRozpoczynanie scrapingu...",
            pd.DataFrame(
                columns=[
                    "date",
                    "title",
                    "report type",
                    "report category",
                    "exchange rate",
                    "rate change",
                    "link",
                ]
            ),
            "*Model gotowy, rozpoczynam pobieranie raportów...*",
        )
    
    # Wykonaj scraping
    result = scrape(
        company_name,
        report_amount,
        date_str,
        report_types,
        categories,
        download_checkbox,
        download_types_file,
        model_name,
    )
    
    # Rozpakuj wynik (NOWE: 6 elementów)
    if len(result) == 6:
        summary_text, df, summaries, summary_report_path, collective_summary, downloaded_files = result
        
        # Dodaj info o zbiorczym raporcie do statusu
        if summary_report_path:
            summary_text += f"\n\n📄 **Zbiorczy raport zapisany:** `{summary_report_path}`"
        
        # Jeśli nie ma collective summary, użyj placeholder
        if not collective_summary or collective_summary.strip() == "":
            collective_summary = "*Brak zbiorczego podsumowania (nie wygenerowano streszczeń)*"
        
        result = (summary_text, df, summaries, collective_summary)
    elif len(result) == 5:
        # Fallback dla starej wersji (5 elementów)
        summary_text, df, summaries, summary_report_path, collective_summary = result
        if summary_report_path:
            summary_text += f"\n\n📄 **Zbiorczy raport zapisany:** `{summary_report_path}`"
        result = (summary_text, df, summaries, collective_summary)
    else:
        # Bardzo stara wersja (4 elementy) - fallback
        summary_text, df, summaries, summary_report_path = result
        if summary_report_path:
            summary_text += f"\n\n📄 **Zbiorczy raport zapisany:** `{summary_report_path}`"
        result = (summary_text, df, summaries, "*Brak zbiorczego podsumowania*")
    
    yield result


def get_model_choices():
    """Generuje listę modeli z oznaczeniem statusu instalacji."""
    available = get_available_models()
    installed = get_installed_models()
    choices = []
    for model in available:
        is_installed = model in installed
        choices.append(get_model_display_name(model, is_installed))
    return choices


# ============================================================================
# ZAKŁADKA 2: HARMONOGRAM - Funkcje pomocnicze
# ============================================================================

def schedule_to_cron(frequency: str, time_hour: int, time_minute: int, day_of_week: str = None, day_of_month: int = None):
    """
    Konwertuje prosty opis harmonogramu na cron expression.
    
    Args:
        frequency: 'daily', 'weekly', 'monthly', 'custom'
        time_hour: Godzina (0-23)
        time_minute: Minuta (0-59)
        day_of_week: 'Monday', 'Tuesday', ... (dla weekly)
        day_of_month: 1-31 (dla monthly)
    
    Returns:
        str: Cron expression (format: minute hour day month weekday)
    """
    dow_mapping = {
        'Poniedziałek': '1',
        'Wtorek': '2',
        'Środa': '3',
        'Czwartek': '4',
        'Piątek': '5',
        'Sobota': '6',
        'Niedziela': '0'
    }
    
    if frequency == 'Codziennie':
        return f"{time_minute} {time_hour} * * *"
    elif frequency == 'Co tydzień':
        dow = dow_mapping.get(day_of_week, '1')
        return f"{time_minute} {time_hour} * * {dow}"
    elif frequency == 'Co miesiąc':
        dom = day_of_month if day_of_month else 1
        return f"{time_minute} {time_hour} {dom} * *"
    else:
        return f"{time_minute} {time_hour} * * *"


def cron_to_human_readable(cron_expr: str) -> str:
    """Konwertuje cron expression na czytelny opis."""
    parts = cron_expr.split()
    if len(parts) != 5:
        return cron_expr
    
    minute, hour, day, month, weekday = parts
    
    time_str = f"{hour}:{minute.zfill(2)}"
    
    if day == '*' and month == '*' and weekday == '*':
        return f"Codziennie o {time_str}"
    elif day == '*' and month == '*' and weekday != '*':
        dow_names = ['Niedziela', 'Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota']
        dow_name = dow_names[int(weekday)] if weekday.isdigit() and int(weekday) < 7 else f"dzień {weekday}"
        return f"Co tydzień w {dow_name} o {time_str}"
    elif day != '*' and month == '*' and weekday == '*':
        return f"Co miesiąc {day}. dnia o {time_str}"
    else:
        return cron_expr


def get_all_configs_as_text():
    """Zwraca listę wszystkich konfiguracji jako sformatowany tekst."""
    manager = ConfigManager()
    configs = manager.list_configs()
    
    if not configs:
        return "Brak zapisanych konfiguracji."
    
    text = "## 📋 Zapisane konfiguracje\n\n"
    for config in configs:
        status = "✓ Aktywna" if config.enabled else "✗ Wyłączona"
        text += f"### {config.job_name}\n"
        text += f"- **Status:** {status}\n"
        text += f"- **Firma:** {config.company}\n"
        text += f"- **Okres:** {config.date_from} - {config.date_to}\n"
        text += f"- **Model:** {config.model}\n"
        text += f"- **Harmonogram:** `{config.cron_schedule}`\n"
        text += f"- **Opis:** {config.description}\n\n"
        text += "---\n\n"
    
    return text


def get_installed_jobs_as_text():
    """Zwraca listę zainstalowanych zadań cron jako tekst."""
    cron_mgr = CronManager()
    jobs = cron_mgr.get_installed_jobs()
    
    if not jobs:
        return "ℹ️ Brak zainstalowanych zadań w crontab."
    
    text = f"## 📅 Zainstalowane zadania ({len(jobs)})\n\n"
    text += "```\n"
    for job in jobs:
        text += f"{job}\n"
    text += "```\n"
    
    return text


def create_new_config(job_name, company, date_from, date_to, model, cron_schedule, description, enabled):
    """Tworzy nową konfigurację."""
    try:
        # Konwersja dat - gr.DateTime może zwrócić string, datetime, float (timestamp) lub None
        def format_date(date_input):
            if not date_input:
                return ""
            
            # Float timestamp z Gradio DateTime
            if isinstance(date_input, (int, float)):
                try:
                    from datetime import datetime as dt
                    parsed = dt.fromtimestamp(date_input)
                    return parsed.strftime("%d-%m-%Y")
                except:
                    return ""
            
            # String ISO format
            if isinstance(date_input, str):
                try:
                    parsed = datetime.fromisoformat(date_input.replace('Z', '+00:00'))
                    return parsed.strftime("%d-%m-%Y")
                except:
                    # Może już jest w formacie dd-mm-yyyy
                    if '-' in date_input and len(date_input) == 10:
                        return date_input
                    return ""
            
            # Obiekt datetime
            if hasattr(date_input, 'strftime'):
                return date_input.strftime("%d-%m-%Y")
            
            return ""
        
        config = ScrapingConfig(
            job_name=job_name,
            company=company,
            date_from=format_date(date_from),
            date_to=format_date(date_to),
            model=model,
            cron_schedule=cron_schedule,
            enabled=enabled,
            description=description
        )
        
        manager = ConfigManager()
        manager.save_config(config)
        
        return (
            f"✅ Konfiguracja '{job_name}' została zapisana!",
            get_all_configs_as_text()
        )
    except Exception as e:
        return (f"❌ Błąd: {e}", get_all_configs_as_text())


def create_new_config_advanced(job_name, company, date_from, date_to, model, cron_schedule, description, enabled, report_limit=100, report_types=None, report_categories=None):
    """
    Tworzy nową konfigurację z zaawansowanymi opcjami.
    
    NOTE: date_from i date_to są przechowywane dla kompatybilności, ale nieużywane.
    Pobierane są wszystkie dostępne raporty (bez ograniczenia zakresu dat).
    report_limit określa maksymalną liczbę wyników wyszukiwania.
    """
    try:
        # Konwersja dat - gr.DateTime może zwrócić string, datetime, float (timestamp) lub None
        def format_date(date_input):
            if not date_input:
                return ""
            
            # Float timestamp z Gradio DateTime
            if isinstance(date_input, (int, float)):
                try:
                    from datetime import datetime as dt
                    parsed = dt.fromtimestamp(date_input)
                    return parsed.strftime("%d-%m-%Y")
                except:
                    return ""
            
            # String ISO format
            if isinstance(date_input, str):
                try:
                    parsed = datetime.fromisoformat(date_input.replace('Z', '+00:00'))
                    return parsed.strftime("%d-%m-%Y")
                except:
                    # Może już jest w formacie dd-mm-yyyy
                    if '-' in date_input and len(date_input) == 10:
                        return date_input
                    return ""
            
            # Obiekt datetime
            if hasattr(date_input, 'strftime'):
                return date_input.strftime("%d-%m-%Y")
            
            return ""
        
        config = ScrapingConfig(
            job_name=job_name,
            company=company,
            date_from=format_date(date_from),
            date_to=format_date(date_to),
            model=model,
            cron_schedule=cron_schedule,
            enabled=enabled,
            report_limit=report_limit,
            description=description,
            report_types=report_types if report_types else None,
            report_categories=report_categories if report_categories else None
        )
        
        manager = ConfigManager()
        manager.save_config(config)
        
        return (
            f"✅ Konfiguracja '{job_name}' została zapisana!",
            get_all_configs_as_text()
        )
    except Exception as e:
        return (f"❌ Błąd: {e}", get_all_configs_as_text())


def run_job_now(job_name):
    """
    Ręcznie uruchamia zadanie bez czekania na harmonogram cron.
    """
    import subprocess
    import sys
    
    if not job_name or job_name.strip() == "":
        return "❌ Wybierz zadanie do uruchomienia"

    try:
        # Uruchom run_scheduled.py w tle
        python_exe = sys.executable
        script_path = os.path.join(os.path.dirname(__file__), "run_scheduled.py")
        
        result = subprocess.run(
            [python_exe, script_path, job_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout
        )
        
        output = f"▶️ Uruchomiono zadanie '{job_name}'\n\n"
        output += "📝 **Output:**\n```\n"
        output += result.stdout if result.stdout else "(brak output)"
        output += "\n```\n"
        
        if result.stderr:
            output += "\n⚠️ **Errors:**\n```\n"
            output += result.stderr
            output += "\n```\n"
        
        if result.returncode == 0:
            output += "\n✅ **Status:** Zakończone pomyślnie"
        else:
            output += f"\n❌ **Status:** Błąd (kod {result.returncode})"
        
        return output
        
    except subprocess.TimeoutExpired:
        return f"⏱️ Przekroczono limit czasu (5 min) dla zadania '{job_name}'"
    except Exception as e:
        return f"❌ Błąd uruchamiania: {e}"


def get_execution_history(job_filter=None, limit=20):
    """
    Pobiera historię wykonań zadań z bazy danych.
    
    Returns:
        List of lists for Gradio DataFram: [job_name, status, started_at, duration, reports_found, wyniki, error_msg]
    """
    from database_connection import get_job_execution_logs
    from pathlib import Path
    
    try:
        logs = get_job_execution_logs(job_name=job_filter if job_filter else None, limit=limit)
        
        rows = []
        for log in logs:
            # Status icon
            status_icon = {
                'success': '✅ Sukces',
                'failed': '❌ Błąd',
                'running': '⏳ W trakcie',
                'no_reports': 'ℹ️ Brak raportów'
            }.get(log.get('status', 'unknown'), '❓ Nieznany')
            
            # Duration calculation
            started = log.get('started_at')
            finished = log.get('finished_at')
            duration = "N/A"
            if started and finished:
                duration_sec = (finished - started).total_seconds()
                if duration_sec < 60:
                    duration = f"{duration_sec:.1f}s"
                else:
                    duration = f"{duration_sec/60:.1f}min"
            
            # Error message (truncate if too long)
            error_msg = log.get('error_message', '')
            if error_msg and len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            
            # Result file info
            log_file = log.get('log_file_path', '')
            results_info = "-"
            if log_file and Path(log_file).exists():
                job_name = log.get('job_name', '')
                docs = log.get('documents_processed', 0)
                results_info = f"📄 {docs} doc" if docs > 0 else f"📂 Log"
            
            rows.append([
                log.get('job_name', 'N/A'),
                status_icon,
                started.strftime('%Y-%m-%d %H:%M:%S') if started else 'N/A',
                duration,
                log.get('reports_found', 0),
                results_info,
                error_msg or '-'
            ])
        
        return rows if rows else [["Brak historii wykonań", "-", "-", "-", "-", "-", "-"]]
        
    except Exception as e:
        return [[f"Błąd: {e}", "-", "-", "-", "-", "-"]]


def create_from_template_ui(template_name, company):
    """Tworzy konfigurację z szablonu (deprecated in v2.0)."""
    return (f"⚠️  Funkcja szablonów została usunięta w v2.0. Użyj 'Utwórz Nowy' zamiast tego.", get_all_configs_as_text())


def delete_config_ui(job_name):
    """Usuwa konfigurację."""
    manager = ConfigManager()
    
    if manager.delete_config(job_name):
        return (f"✅ Usunięto konfigurację '{job_name}'", get_all_configs_as_text())
    else:
        return (f"❌ Nie znaleziono konfiguracji '{job_name}'", get_all_configs_as_text())


def install_cron_jobs():
    """Instaluje zadania do crontab."""
    cron_mgr = CronManager()
    success, message = cron_mgr.install_jobs()
    
    return (message, get_installed_jobs_as_text())


def uninstall_cron_jobs():
    """Usuwa zadania z crontab."""
    cron_mgr = CronManager()
    success, message = cron_mgr.uninstall_jobs()
    
    return (message, get_installed_jobs_as_text())


def export_config_ui(job_name):
    """Eksportuje konfigurację do pliku (v2.0 - from database)."""
    import json
    manager = ConfigManager()
    config = manager.load_config(job_name)
    
    if config:
        output_path = f"/tmp/{job_name}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        return (f"✅ Wyeksportowano do: {output_path}", output_path)
    else:
        return (f"❌ Nie znaleziono konfiguracji '{job_name}'", None)


def import_config_ui(file):
    """Importuje konfigurację z pliku (v2.0 - saves to database)."""
    import json
    if file is None:
        return ("❌ Nie wybrano pliku", get_all_configs_as_text())
    
    try:
        import json
        manager = ConfigManager()
        
        with open(file.name, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = ScrapingConfig.from_dict(data)
        manager.save_config(config)
        
        return (
            f"✅ Zaimportowano konfigurację '{config.job_name}'!",
            get_all_configs_as_text()
        )
    except Exception as e:
        return (f"❌ Błąd importu: {e}", get_all_configs_as_text())


def validate_cron_expression_ui(cron_expr):
    """Waliduje wyrażenie cron."""
    cron_mgr = CronManager()
    valid, message = cron_mgr.validate_cron_expression(cron_expr)
    
    return message


# ============================================================================
# GŁÓWNY INTERFEJS GRADIO
# ============================================================================

with gr.Blocks(title="GPW Scraper") as demo:
    gr.Markdown("# 📊 GPW Scraper - Narzędzie do analizy raportów giełdowych")
    gr.Markdown(
        "Scraping raportów z GPW + automatyczne podsumowania AI + harmonogram cron"
    )
    
    with gr.Tabs():
        # ====================================================================
        # ZAKŁADKA 1: SCRAPING
        # ====================================================================
        with gr.Tab("🔍 Scraping"):
            gr.Markdown("### Ręczne pobieranie i analiza raportów GPW")
            
            with gr.Row():
                with gr.Column():
                    with gr.Row():
                        company_name = gr.Dropdown(
                            choices=[],
                            label="Nazwa firmy",
                            info="Jaką firmę chcesz przeanalizować?",
                            interactive=True,
                            filterable=True,
                            allow_custom_value=True
                        )
                        refresh_companies_scraping = gr.Button("🔄", scale=0, size="sm")
                    
                    def refresh_companies_dropdown():
                        """Pobiera listę spółek z bazy danych"""
                        from database_connection import get_all_companies
                        companies = get_all_companies()
                        company_names = sorted([c.get('name', c) if isinstance(c, dict) else str(c) for c in companies])
                        return gr.update(choices=company_names)
                    
                    refresh_companies_scraping.click(
                        fn=refresh_companies_dropdown,
                        inputs=[],
                        outputs=[company_name]
                    )
                    
                    # Inicjalne ładowanie spółek
                    demo.load(fn=refresh_companies_dropdown, outputs=[company_name])
                    report_amount = gr.Slider(
                        1,
                        25,
                        label="Liczba raportów",
                        info="Ile raportów pobrać?",
                        value=5,
                        step=1,
                    )
                    with gr.Row():
                        download_checkbox = gr.Checkbox(
                            value=True,
                            interactive=True,
                            label="Pobierz CSV z raportami",
                        )
                        download_types_file = gr.Checkboxgroup(
                            ["PDF", "HTML"],
                            label="Pobierz pliki",
                            info="Pobieranie może zająć chwilę dla dużych raportów",
                        )
                
                with gr.Column():
                    date = gr.DateTime(
                        include_time=False,
                        type="string",
                        label="Data (opcjonalnie)",
                        info="Jeśli puste, pobierze raporty ze wszystkich dat",
                    )
                    report_types = gr.Checkboxgroup(
                        ["current", "semi-annual", "quarterly", "interim", "annual"],
                        label="Typ raportu",
                        info="Rodzaj raportu do pobrania",
                        value=["current", "semi-annual", "quarterly", "interim", "annual"],
                    )
                    categories = gr.Checkboxgroup(
                        ["EBI", "ESPI"],
                        label="Kategoria raportu",
                        info="Kategoria raportów GPW",
                        value=["EBI", "ESPI"],
                    )
                    
                    # Wybór modelu Ollama
                    with gr.Row():
                        model_dropdown = gr.Dropdown(
                            choices=get_model_choices(),
                            value=get_model_choices()[0] if get_model_choices() else "llama3.2:latest",
                            label="Model Ollama",
                            info="✓ = zainstalowany, ○ = zostanie pobrany automatycznie",
                            interactive=True,
                        )
                        refresh_btn = gr.Button("🔄", scale=0, size="sm")
                    
                    refresh_btn.click(
                        fn=lambda: get_model_choices(),
                        inputs=[],
                        outputs=[model_dropdown],
                    )
                
                with gr.Column():
                    # Historia wyszukiwań
                    gr.Markdown("### 📜 Historia wyszukiwań (ostatnie 2)")
                    
                    # Dynamiczna historia z przyciskiem odświeżenia
                    def refresh_search_history():
                        """Odśwież historię wyszukiwań"""
                        temp = {
                            "Company Name": [],
                            "Report amount": [],
                            "Download report types": [],
                            "Report date": [],
                            "Report type": [],
                            "Report category": [],
                        }
                        text = ""
                        itr = 0
                        # Get search history from database (v2.0) - last 2 searches only
                        historia_db = get_search_history(limit=2)
                        historia_z_bazy = [
                            [
                                h['company_name'],
                                h['report_amount'],
                                h['download_type'],
                                h['report_date'],
                                h['report_type'] or 'not specified',
                                h['report_category'] or 'not specified',
                                h['created_at'].strftime('%Y-%m-%d %H:%M:%S') if h.get('created_at') else 'N/A'
                            ]
                            for h in historia_db
                        ]
                        
                        if not historia_z_bazy:
                            return "*Brak historii wyszukiwań*"
                        
                        for lista in historia_z_bazy:
                            for element, key in zip(lista, temp.keys()):
                                if element == "" or element is None:
                                    element = "not specified"
                                temp[key].append(element)
                                text += "\n- **" + key + ":** *" + str(element) + "*"
                            itr += 1
                            if itr < len(historia_z_bazy):
                                text += "\n"
                                text += "-" * 50
                        
                        return text
                    
                    history = gr.Markdown(
                        value=refresh_search_history(),
                        label="SEARCH HISTORY",
                    )
                    
                    # Przycisk odświeżenia historii
                    with gr.Row():
                        refresh_history_btn = gr.Button("🔄 Odśwież historię", scale=1, size="sm")
                    
                    refresh_history_btn.click(
                        fn=refresh_search_history,
                        inputs=[],
                        outputs=[history],
                    )
            
            with gr.Row():
                submit_btn = gr.Button(
                    value="▶️ Uruchom scraping",
                    variant="primary",
                    scale=1,
                )
            
            with gr.Row():
                output_text = gr.Textbox(label="Status", scale=1)
            
            with gr.Row():
                output_dataframe = gr.DataFrame(
                    headers=[
                        "date",
                        "title",
                        "report type",
                        "report category",
                        "exchange rate",
                        "rate change",
                        "link",
                    ],
                    label="Pobrane dane",
                    scale=5,
                )
            
            with gr.Row():
                output_summaries = gr.Markdown(
                    label="Podsumowania AI (szczegółowe)",
                )
            
            # NOWE: Zbiorczy raport LLM
            with gr.Row():
                output_collective = gr.Markdown(
                    label="📋 Zbiorczy raport LLM",
                    value="*Zbiorczy raport pojawi się tutaj po wygenerowaniu streszczeń...*",
                )
            
            submit_btn.click(
                fn=run_scrape_ui,
                inputs=[
                    company_name,
                    report_amount,
                    date,
                    report_types,
                    categories,
                    download_checkbox,
                    download_types_file,
                    model_dropdown,
                ],
                outputs=[output_text, output_dataframe, output_summaries, output_collective],
            )
        
        # ====================================================================
        
        # ====================================================================
        # ZAKŁADKA 2: AUTOMATYZACJA (NOWY PROSTY INTERFEJS)
        # ====================================================================
        with gr.Tab("⏰ Automatyzacja"):
            gr.Markdown("## 🤖 Automatyczne raporty - Proste i intuicyjne")
            
            # Sekcja 1: Utwórz nowe zadanie
            with gr.Accordion("➕ Utwórz nowe zadanie", open=True):
                gr.Markdown("### Szybka konfiguracja zadania")
                
                with gr.Row():
                    with gr.Column(scale=2):
                        auto_job_name = gr.Textbox(
                            label="📝 Nazwa zadania",
                            placeholder="np. PKO_codzienny",
                            info="Bez spacji (użyj _ zamiast)"
                        )
                        auto_company = gr.Textbox(label="🏢 Firma", placeholder="np. PKO")
                        
                        auto_report_limit = gr.Slider(
                            label="📝 Ile raportów pobrać?",
                            minimum=1,
                            maximum=100,
                            value=5,
                            step=1,
                            info="Limit wyników wyszukiwania"
                        )
                        
                        auto_model = gr.Dropdown(
                            label="🤖 Model AI",
                            choices=["llama3.2:latest", "gemma:7b", "qwen2.5:7b"],
                            value="llama3.2:latest"
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### ⏰ Harmonogram")
                        auto_frequency = gr.Dropdown(
                            label="Częstotliwość",
                            choices=["Codziennie", "Co tydzień", "Co miesiąc"],
                            value="Codziennie"
                        )
                        
                        with gr.Row():
                            auto_hour = gr.Slider(label="Godzina", minimum=0, maximum=23, value=9, step=1)
                            auto_minute = gr.Slider(label="Minuta", minimum=0, maximum=59, value=0, step=5)
                        
                        auto_day_of_week = gr.Dropdown(
                            label="Dzień tygodnia",
                            choices=["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"],
                            value="Poniedziałek",
                            visible=False
                        )
                        
                        auto_day_of_month = gr.Slider(
                            label="Dzień miesiąca",
                            minimum=1, maximum=31, value=1, step=1, visible=False
                        )
                        
                        auto_schedule_preview = gr.Markdown("**⏰ Codziennie o 09:00**")
                        
                        def update_preview(freq, hour, minute, dow, dom):
                            time_str = f"{int(hour):02d}:{int(minute):02d}"
                            if freq == "Codziennie":
                                return f"**⏰ Codziennie o {time_str}**"
                            elif freq == "Co tydzień":
                                return f"**⏰ Co tydzień w {dow} o {time_str}**"
                            else:
                                return f"**⏰ Co miesiąc {int(dom)}. dnia o {time_str}**"
                        
                        def toggle_fields(freq):
                            if freq == "Co tydzień":
                                return gr.update(visible=True), gr.update(visible=False)
                            elif freq == "Co miesiąc":
                                return gr.update(visible=False), gr.update(visible=True)
                            return gr.update(visible=False), gr.update(visible=False)
                        
                        auto_frequency.change(fn=toggle_fields, inputs=[auto_frequency], outputs=[auto_day_of_week, auto_day_of_month])
                        
                        for comp in [auto_frequency, auto_hour, auto_minute, auto_day_of_week, auto_day_of_month]:
                            comp.change(fn=update_preview, inputs=[auto_frequency, auto_hour, auto_minute, auto_day_of_week, auto_day_of_month], outputs=[auto_schedule_preview])
                
                gr.Markdown("---")
                gr.Markdown("### ⚙️ Opcje zaawansowane (opcjonalne)")
                
                with gr.Accordion("🔧 Szczegóły scrapingu", open=False):
                    with gr.Row():
                        auto_report_types = gr.CheckboxGroup(
                            label="📑 Typy raportów",
                            choices=["current", "quarterly", "semi-annual", "annual", "interim"],
                            value=["current", "quarterly", "semi-annual", "annual"],
                            info="Wybierz, które typy raportów pobrać"
                        )
                        
                        auto_report_categories = gr.CheckboxGroup(
                            label="📂 Kategorie",
                            choices=["ESPI", "EBI"],
                            value=["ESPI", "EBI"],
                            info="ESPI = raporty giełdowe, EBI = raporty bankowe"
                        )
                
                create_job_btn = gr.Button("✨ Utwórz zadanie", variant="primary", size="lg")
                create_job_output = gr.Textbox(label="Status")
                
                def create_job_simple(job_name, company, report_limit, model, freq, h, m, dow, dom, rep_types, rep_cats):
                    cron = schedule_to_cron(freq, int(h), int(m), dow, int(dom))
                    # Use advanced options if provided
                    report_types = rep_types if rep_types else None
                    report_categories = rep_cats if rep_cats else None
                    # Use today's date for both date_from and date_to (compatibility), report_limit is the key param
                    from datetime import datetime as dt
                    today_str = dt.now().strftime("%d-%m-%Y")
                    return create_new_config_advanced(job_name, company, today_str, today_str, model, cron, f"{freq} - {company}", True, int(report_limit), report_types, report_categories)[0]
                
                create_job_btn.click(
                    fn=create_job_simple,
                    inputs=[auto_job_name, auto_company, auto_report_limit, auto_model, auto_frequency, auto_hour, auto_minute, auto_day_of_week, auto_day_of_month, auto_report_types, auto_report_categories],
                    outputs=[create_job_output]
                )
            
            gr.Markdown("---")
            
            # Sekcja 2: Zarządzaj zadaniami
            with gr.Accordion("📋 Moje zadania", open=True):
                refresh_btn = gr.Button("🔄 Odśwież", variant="secondary")
                
                jobs_table = gr.Dataframe(
                    headers=["Nazwa", "Firma", "Model", "Harmonogram", "Status"],
                    interactive=False
                )
                
                def get_jobs_table():
                    from config_manager import ConfigManager
                    from cron_manager import CronManager
                    
                    mgr = ConfigManager()
                    cron_mgr = CronManager()
                    configs = mgr.list_configs()
                    
                    installed = set()
                    for line in cron_mgr.get_installed_jobs():
                        if "run_scheduled.py" in line:
                            name = line.split("run_scheduled.py")[1].split()[0].strip() if len(line.split("run_scheduled.py")) > 1 else ""
                            if name:
                                installed.add(name)
                    
                    rows = []
                    for cfg in configs:
                        status = "✅ Aktywne" if cfg.enabled else "⏸️ Wyłączone"
                        if cfg.enabled and cfg.job_name not in installed:
                            status += " (brak w cron)"
                        
                        rows.append([
                            cfg.job_name,
                            cfg.company,
                            cfg.model,
                            cron_to_human_readable(cfg.cron_schedule),
                            status
                        ])
                    
                    return rows if rows else [["Brak zadań", "-", "-", "-", "-"]]
                
                refresh_btn.click(fn=get_jobs_table, outputs=[jobs_table])
                demo.load(fn=get_jobs_table, outputs=[jobs_table])
                
                gr.Markdown("### ⚡ Akcje")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("**▶️ Uruchom teraz**")
                        run_select = gr.Dropdown(label="Wybierz zadanie", choices=[], interactive=True)
                        run_btn = gr.Button("▶️ Uruchom", variant="primary")
                        run_output = gr.Textbox(label="Log", lines=10)
                    
                    with gr.Column():
                        gr.Markdown("**🗑️ Usuń zadanie**")
                        del_select = gr.Dropdown(label="Wybierz zadanie", choices=[], interactive=True)
                        del_btn = gr.Button("🗑️ Usuń", variant="stop")
                        del_output = gr.Textbox(label="Status")
                
                def get_names():
                    from config_manager import ConfigManager
                    names = [c.job_name for c in ConfigManager().list_configs()]
                    return gr.update(choices=names), gr.update(choices=names)
                
                refresh_btn.click(fn=get_names, outputs=[run_select, del_select])
                demo.load(fn=get_names, outputs=[run_select, del_select])
                
                run_btn.click(fn=run_job_now, inputs=[run_select], outputs=[run_output])
                del_btn.click(fn=delete_config_ui, inputs=[del_select], outputs=[del_output])
            
            gr.Markdown("---")
            
            # Sekcja 3: Instalacja w systemie
            with gr.Accordion("🔧 Instalacja w systemie cron", open=False):
                gr.Markdown("**Zainstaluj w crontab** aby zadania uruchamiały się automatycznie")
                
                with gr.Row():
                    install_btn = gr.Button("✅ Zainstaluj", variant="primary")
                    uninstall_btn = gr.Button("🗑️ Odinstaluj", variant="stop")
                
                cron_status = gr.Textbox(label="Status", lines=3)
                
                install_btn.click(fn=install_cron_jobs, outputs=[cron_status])
                uninstall_btn.click(fn=uninstall_cron_jobs, outputs=[cron_status])
                
                refresh_cron_btn = gr.Button("🔄 Pokaż zainstalowane")
                cron_display = gr.Markdown(value=get_installed_jobs_as_text())
                refresh_cron_btn.click(fn=get_installed_jobs_as_text, outputs=[cron_display])
            
            gr.Markdown("---")
            
            # Sekcja 4: Historia
            with gr.Accordion("📊 Historia wykonań", open=True):
                gr.Markdown("### 📜 Ostatnie uruchomienia")
                
                with gr.Row():
                    hist_filter = gr.Dropdown(
                        label="Filtruj",
                        choices=["Wszystkie"],
                        value="Wszystkie"
                    )
                    hist_refresh = gr.Button("🔄 Odśwież")
                
                hist_table = gr.Dataframe(
                    headers=["Zadanie", "Status", "Start", "Czas", "Raporty", "Wyniki", "Błąd"],
                    interactive=False
                )
                
                def refresh_hist(flt):
                    return get_execution_history(None if flt == "Wszystkie" else flt, 30)
                
                hist_refresh.click(fn=refresh_hist, inputs=[hist_filter], outputs=[hist_table])
                demo.load(fn=lambda: get_execution_history(None, 30), outputs=[hist_table])
                
                def update_filter():
                    from config_manager import ConfigManager
                    names = [c.job_name for c in ConfigManager().list_configs()]
                    return gr.update(choices=["Wszystkie"] + names)
                
                refresh_btn.click(fn=update_filter, outputs=[hist_filter])

        # ====================================================================
        # ZAKŁADKA 3: AKTYWNE HARMONOGRAMY
        # ====================================================================
        with gr.Tab("📊 Aktywne Harmonogramy"):
            gr.Markdown("### Status aktywnych zadań automatyzacji")
            
            refresh_active_btn = gr.Button("🔄 Odśwież status", variant="secondary")
            active_jobs_display = gr.Dataframe(
                headers=["Nazwa", "Firma", "Model", "Harmonogram", "Status", "Ostatnie uruchomienie", "Liczba uruchomień"],
                interactive=False
            )
            
            def get_active_jobs_status():
                """Pobiera status aktywnych zadań (v2.0 - from database)."""
                from config_manager import ConfigManager
                from database_connection import get_active_jobs_view
                from cron_manager import CronManager
                import os
                
                config_mgr = ConfigManager()
                cron_mgr = CronManager()
                
                # Use database view for active jobs
                active_jobs = get_active_jobs_view()
                installed_jobs_lines = cron_mgr.get_installed_jobs()
                # Wyciągnij nazwy zadań z linii crontab (format: ... run_scheduled.py NAZWA >> ...)
                installed_job_names = set()
                for line in installed_jobs_lines:
                    if "run_scheduled.py" in line:
                        parts = line.split("run_scheduled.py")
                        if len(parts) > 1:
                            name = parts[1].split()[0].strip()
                            installed_job_names.add(name)
                
                rows = []
                for job in active_jobs:  # job is database row from v_active_jobs view
                    job_name = job['job_name']
                    status = "✅ Aktywny" if job['enabled'] and job_name in installed_job_names else "⏸️ Nieaktywny"
                    
                    # Get last run from database
                    last_run = job['last_run'].strftime('%Y-%m-%d %H:%M:%S') if job.get('last_run') else "Nigdy"
                    run_count = job.get('run_count', 0)
                    
                    rows.append([
                        job_name,
                        job['company'],
                        job['model'],
                        job['cron_schedule'],
                        status,
                        last_run,
                        run_count
                    ])
                
                return rows
            
            refresh_active_btn.click(
                fn=get_active_jobs_status,
                inputs=[],
                outputs=[active_jobs_display]
            )
            
            # Auto-load przy otwarciu
            demo.load(fn=get_active_jobs_status, outputs=[active_jobs_display])
        
        # ====================================================================
        # ZAKŁADKA 4: ZBIORCZE RAPORTY
        # ====================================================================
        with gr.Tab("📚 Zbiorcze Raporty"):
            gr.Markdown("### Przeglądaj wygenerowane raporty zbiorcze")
            
            with gr.Row():
                filter_company = gr.Textbox(label="Filtruj po firmie", placeholder="np. Asseco")
                filter_job = gr.Textbox(label="Filtruj po zadaniu", placeholder="np. tygodniowy")
                search_reports_btn = gr.Button("🔍 Szukaj", variant="primary")
            
            reports_display = gr.Dataframe(
                headers=["ID", "Zadanie", "Firma", "Data od", "Data do", "Liczba raportów", "Format", "Rozmiar", "Data utworzenia"],
                interactive=False
            )
            
            with gr.Row():
                report_id_input = gr.Number(label="ID raportu do pobrania", precision=0)
                download_report_btn = gr.Button("📥 Pobierz raport", variant="secondary")
            
            # Podgląd raportu - PDF (pełna szerokość)
            report_pdf_viewer = gr.HTML(label="📋 Podgląd PDF", value="<p style='text-align: center; color: gray;'>PDF pojawi się tutaj...</p>")

            download_file_output = gr.File(label="Pobierz plik")
            
            def search_summary_reports(company_filter, job_filter):
                """Wyszukuje zbiorcze raporty z bazy (v2.0)."""
                from database_connection import get_summary_reports
                
                try:
                    # Build kwargs to avoid None type issues
                    kwargs = {'limit': 50}
                    if company_filter:
                        kwargs['company'] = company_filter
                    
                    results = get_summary_reports(**kwargs)
                    
                    # Filter by job_name if provided
                    if job_filter:
                        results = [r for r in results if job_filter.lower() in r['job_name'].lower()]
                    
                    rows = []
                    for row in results:
                        # row is dict from database_connection
                        rows.append([
                            row['id'],
                            row['job_name'],
                            row['company'],
                            row['date_from'] if row['date_from'] else "N/A",
                            row['date_to'] if row['date_to'] else "N/A",
                            row['report_count'],
                            row['file_format'].upper() if row['file_format'] else "N/A",
                            f"{row['file_size'] / 1024:.1f} KB" if row['file_size'] else "N/A",
                            row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row.get('created_at') else "N/A"
                        ])
                    
                    return rows
                except Exception as e:
                    return [[f"Błąd: {e}", "", "", "", "", "", "", "", ""]]
            
            def load_report_content(report_id):
                """Ładuje zawartość raportu do podglądu (zwraca HTML do `report_pdf_viewer` oraz ścieżkę pliku)."""
                from database_connection import get_summary_report_by_id
                import os
                import base64

                if not report_id:
                    return "<p style='text-align: center; color: gray;'>Wprowadź ID raportu</p>", None

                try:
                    report = get_summary_report_by_id(int(report_id))
                    if not report:
                        return "<p style='text-align: center; color: gray;'>Raport nie znaleziony</p>", None

                    file_path = report['file_path']

                    if not os.path.exists(file_path):
                        return f"<p style='text-align: center; color: red;'>Plik nie istnieje: {file_path}</p>", None

                    # Check file format
                    file_ext = os.path.splitext(file_path)[1].lower()

                    if file_ext == '.pdf':
                        # PDF - embed jako iframe z base64
                        try:
                            with open(file_path, 'rb') as f:
                                pdf_data = base64.b64encode(f.read()).decode('utf-8')

                            # Tworzymy HTML z embeddowanym PDF-em
                            pdf_html = f"""
                            <div style="height: 800px;">
                                <iframe
                                    src="data:application/pdf;base64,{pdf_data}"
                                    width="100%"
                                    height="100%"
                                    style="border: none;"
                                >
                                    Twoja przeglądarka nie obsługuje PDF-ów. 
                                    <a href="data:application/pdf;base64,{pdf_data}" download="raport.pdf">Pobierz PDF</a>
                                </iframe>
                            </div>
                            """

                            return pdf_html, file_path
                        except Exception as pdf_err:
                            return f"<p style='text-align: center; color: red;'>Błąd ładowania PDF: {pdf_err}</p>", file_path

                    elif file_ext in ['.md', '.txt']:
                        # Markdown/text - pokaż jako preformatted HTML
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        safe_html = f"<pre style='white-space: pre-wrap; word-break: break-word;'>{content}</pre>"
                        return safe_html, file_path
                    else:
                        return f"<p style='text-align: center; color: orange;'>Nieobsługiwany format pliku: {file_ext}</p>", file_path

                except Exception as e:
                    import traceback
                    error_msg = f"Błąd: {e}"
                    return f"<p style='text-align: center; color: red;'>{error_msg}</p><pre>{traceback.format_exc()}</pre>", None
            
            search_reports_btn.click(
                fn=search_summary_reports,
                inputs=[filter_company, filter_job],
                outputs=[reports_display]
            )
            
            download_report_btn.click(
                fn=load_report_content,
                inputs=[report_id_input],
                outputs=[report_pdf_viewer, download_file_output]
            )
            
            # Auto-load przy otwarciu
            demo.load(
                fn=lambda: search_summary_reports("", ""),
                outputs=[reports_display]
            )
        
        # ====================================================================
        # ZAKŁADKA 5: INFO
        # ====================================================================
        with gr.Tab("ℹ️ Informacje"):
            gr.Markdown(
                """
                # GPW Scraper - Dokumentacja
                
                ## 🔍 Scraping
                
                Pobiera raporty z Giełdy Papierów Wartościowych i automatycznie generuje 
                podsumowania używając AI (Ollama + K-means clustering).
                
                **Funkcje:**
                - Wyszukiwanie raportów po nazwie firmy i dacie
                - Filtrowanie po typie (current, quarterly, annual itp.)
                - Automatyczne podsumowania PDF przez LLM
                - Zapis historii do MySQL
                - Export do CSV
                
                ## ⏰ Harmonogram
                
                Pozwala zaplanować automatyczne raporty używając systemu cron.
                
                **Funkcje:**
                - Konfiguracje JSON (firma, daty, model, harmonogram)
                - Gotowe szablony (codzienny, tygodniowy, miesięczny)
                - Instalacja/usuwanie zadań cron
                - Import/Export konfiguracji
                
                **Przykładowe użycie cron:**
                ```
                0 9 * * 1  - Każdy poniedziałek o 9:00
                0 10 1 * * - 1. dzień miesiąca o 10:00
                */30 * * * * - Co 30 minut
                ```
                
                ## 🤖 Modele AI
                
                System używa modeli Ollama do generowania podsumowań:
                - **llama3.2:latest** (3.6GB) - zalecany, szybki
                - **gemma:7b** (8.8GB) - dokładniejszy
                - **qwen2.5:7b** - alternatywny model
                
                Modele są automatycznie pobierane przy pierwszym użyciu.
                
                ## 📁 Struktura katalogów
                
                ```
                pracownia-dyplomowa/
                ├── configs/              # Konfiguracje harmonogramu (JSON)
                ├── logs/                 # Logi wykonania zadań cron
                ├── scheduled_results/    # Wyniki automatyczne
                ├── REPORTS/              # Pobrane pliki PDF/HTML
                └── ...
                ```
                
                ## 📚 Więcej informacji
                
                - [CRON_AUTOMATION.md](./CRON_AUTOMATION.md) - Pełna dokumentacja automatyzacji
                - [AUTOMATION_SUMMARY.md](./AUTOMATION_SUMMARY.md) - Podsumowanie funkcji
                - [README.md](./README.md) - Ogólny opis projektu
                
                ## 🛠️ Technologie
                
                - **Backend:** Python 3.12, BeautifulSoup4, PyMySQL, Pandas
                - **AI:** Ollama, LangChain, HuggingFace Embeddings
                - **Frontend:** Gradio 5.12.0
                - **Automatyzacja:** Cron, JSON configs
                - **GPU:** CUDA (optional, dla przyspieszenia)
                
                ---
                
                **Wersja:** 2.0  
                **Data:** 25.10.2025  
                **Autor:** GPW Scraper Team
                """
            )

# Uruchomienie aplikacji
if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        show_api=False  # Workaround for Gradio 5.12.0 DataFrame bug
    )
