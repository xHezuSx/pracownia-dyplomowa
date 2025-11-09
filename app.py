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
    
    # Rozpakuj wynik (NOWE: 5 elementów)
    if len(result) == 5:
        summary_text, df, attachments, summary_report_path, collective_summary = result
        
        # Dodaj info o zbiorczym raporcie do statusu
        if summary_report_path:
            summary_text += f"\n\n📄 **Zbiorczy raport zapisany:** `{summary_report_path}`"
        
        # Jeśli nie ma collective summary, użyj placeholder
        if not collective_summary or collective_summary.strip() == "":
            collective_summary = "*Brak zbiorczego podsumowania (nie wygenerowano streszczeń)*"
        
        result = (summary_text, df, attachments, collective_summary)
    else:
        # Stara wersja (4 elementy) - fallback
        summary_text, df, attachments, summary_report_path = result
        if summary_report_path:
            summary_text += f"\n\n📄 **Zbiorczy raport zapisany:** `{summary_report_path}`"
        result = (summary_text, df, attachments, "*Brak zbiorczego podsumowania*")
    
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
                    company_name = gr.Textbox(
                        label="Nazwa firmy",
                        info="Jaką firmę chcesz przeanalizować?",
                        placeholder="np. Asseco, PKN Orlen, CD Projekt"
                    )
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
                    gr.Markdown("### 📜 Historia wyszukiwań")
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
                    # Get search history from database (v2.0)
                    historia_db = get_search_history(limit=100)
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

                    history = gr.Markdown(
                        value=text,
                        label="SEARCH HISTORY",
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
        # ZAKŁADKA 2: HARMONOGRAM
        # ====================================================================
        with gr.Tab("⏰ Harmonogram"):
            gr.Markdown("### Automatyczne raporty - Zarządzanie harmonogramem")
            
            with gr.Tabs():
                # Zakładka 2.1: Nowa konfiguracja
                with gr.Tab("➕ Nowa konfiguracja"):
                    gr.Markdown("#### Utwórz nową konfigurację zadania")
                    
                    with gr.Row():
                        with gr.Column():
                            new_job_name = gr.Textbox(
                                label="Nazwa zadania",
                                placeholder="np. asseco_tygodniowy",
                                info="Unikalna nazwa (bez spacji)"
                            )
                            new_company = gr.Textbox(
                                label="Nazwa firmy",
                                placeholder="np. Asseco"
                            )
                            
                            with gr.Row():
                                new_date_from = gr.DateTime(
                                    label="Data od",
                                    include_time=False
                                )
                                new_date_to = gr.DateTime(
                                    label="Data do",
                                    include_time=False
                                )
                            
                            new_model = gr.Dropdown(
                                label="Model Ollama",
                                choices=["llama3.2:latest", "gemma:7b", "qwen2.5:7b"],
                                value="llama3.2:latest"
                            )
                        
                        with gr.Column():
                            new_cron = gr.Textbox(
                                label="Harmonogram cron",
                                placeholder="0 9 * * 1",
                                info="Format: minuta godzina dzień miesiąc dzień_tygodnia"
                            )
                            
                            gr.Markdown(
                                """
                                **Przykłady:**
                                - `0 9 * * *` - codziennie o 9:00
                                - `0 9 * * 1` - każdy poniedziałek o 9:00
                                - `0 10 1 * *` - 1. dzień miesiąca o 10:00
                                - `*/30 * * * *` - co 30 minut
                                """
                            )
                            
                            validate_cron_btn = gr.Button("Sprawdź wyrażenie cron")
                            cron_validation_output = gr.Textbox(label="Walidacja")
                            
                            new_description = gr.Textbox(
                                label="Opis",
                                placeholder="Krótki opis zadania"
                            )
                            
                            new_enabled = gr.Checkbox(
                                label="Aktywne",
                                value=True
                            )
                    
                    create_config_btn = gr.Button("✨ Utwórz konfigurację", variant="primary")
                    create_output = gr.Textbox(label="Status")
                    configs_display_1 = gr.Markdown(value=get_all_configs_as_text())
                    
                    validate_cron_btn.click(
                        fn=validate_cron_expression_ui,
                        inputs=[new_cron],
                        outputs=[cron_validation_output]
                    )
                    
                    create_config_btn.click(
                        fn=create_new_config,
                        inputs=[new_job_name, new_company, new_date_from, new_date_to, new_model, new_cron, new_description, new_enabled],
                        outputs=[create_output, configs_display_1]
                    )
                
                # Zakładka 2.2: Szablony (disabled in v2.0)
                with gr.Tab("📋 Szablony"):
                    gr.Markdown("#### ⚠️ Funkcja szablonów została usunięta w wersji 2.0")
                    gr.Markdown("Użyj zakładki **'Utwórz Nowy'** aby stworzyć nową konfigurację.")
                    
                    template_name = gr.Dropdown(
                        label="Wybierz szablon (nieaktywne)",
                        choices=["Funkcja wyłączona"],
                        value="Funkcja wyłączona",
                        interactive=False
                    )
                    
                    template_company = gr.Textbox(
                        label="Nazwa firmy",
                        placeholder="Funkcja wyłączona",
                        interactive=False
                    )
                    
                    gr.Markdown(
                        """
                        **Dostępne szablony:**
                        - **codzienny_raport**: Raport z ostatnich 24h, codziennie o 8:00
                        - **tygodniowy_raport**: Raport z ostatnich 7 dni, poniedziałki o 9:00
                        - **miesieczny_raport**: Raport z ostatnich 30 dni, 1. dnia miesiąca o 10:00
                        """
                    )
                    
                    create_from_template_btn = gr.Button("✨ Utwórz z szablonu", variant="primary")
                    template_output = gr.Textbox(label="Status")
                    configs_display_2 = gr.Markdown(value=get_all_configs_as_text())
                    
                    create_from_template_btn.click(
                        fn=create_from_template_ui,
                        inputs=[template_name, template_company],
                        outputs=[template_output, configs_display_2]
                    )
                
                # Zakładka 2.3: Konfiguracje
                with gr.Tab("📄 Konfiguracje"):
                    gr.Markdown("#### Zarządzaj konfiguracjami")
                    
                    refresh_configs_btn = gr.Button("🔄 Odśwież listę")
                    configs_display_3 = gr.Markdown(value=get_all_configs_as_text())
                    
                    gr.Markdown("---")
                    gr.Markdown("#### Usuń konfigurację")
                    
                    with gr.Row():
                        delete_job_name = gr.Textbox(
                            label="Nazwa zadania do usunięcia",
                            placeholder="np. asseco_tygodniowy"
                        )
                        delete_btn = gr.Button("🗑️ Usuń", variant="stop")
                    
                    delete_output = gr.Textbox(label="Status")
                    
                    gr.Markdown("---")
                    gr.Markdown("#### Import / Export")
                    
                    with gr.Row():
                        export_job_name = gr.Textbox(
                            label="Nazwa zadania do eksportu",
                            placeholder="np. asseco_tygodniowy"
                        )
                        export_btn = gr.Button("📤 Eksportuj")
                    
                    export_output = gr.Textbox(label="Ścieżka pliku")
                    export_file = gr.File(label="Plik do pobrania")
                    
                    import_file = gr.File(
                        label="📥 Importuj konfigurację z pliku JSON",
                        file_types=[".json"]
                    )
                    import_btn = gr.Button("📥 Importuj")
                    import_output = gr.Textbox(label="Status")
                    
                    refresh_configs_btn.click(
                        fn=get_all_configs_as_text,
                        inputs=[],
                        outputs=[configs_display_3]
                    )
                    
                    delete_btn.click(
                        fn=delete_config_ui,
                        inputs=[delete_job_name],
                        outputs=[delete_output, configs_display_3]
                    )
                    
                    export_btn.click(
                        fn=export_config_ui,
                        inputs=[export_job_name],
                        outputs=[export_output, export_file]
                    )
                    
                    import_btn.click(
                        fn=import_config_ui,
                        inputs=[import_file],
                        outputs=[import_output, configs_display_3]
                    )
                
                # Zakładka 2.4: Crontab
                with gr.Tab("🔧 Crontab"):
                    gr.Markdown("#### Instalacja zadań w systemie cron")
                    
                    gr.Markdown(
                        """
                        **Uwaga:** Do instalacji zadań w crontab potrzebne są uprawnienia systemowe.
                        Upewnij się, że masz zainstalowany `cron` w systemie.
                        
                        ```bash
                        # Sprawdź czy cron działa
                        systemctl status cron
                        ```
                        """
                    )
                    
                    with gr.Row():
                        install_cron_btn = gr.Button("✅ Zainstaluj zadania do crontab", variant="primary")
                        uninstall_cron_btn = gr.Button("🗑️ Usuń zadania z crontab", variant="stop")
                    
                    cron_output = gr.Textbox(label="Status")
                    
                    refresh_jobs_btn = gr.Button("🔄 Odśwież listę zadań")
                    jobs_display = gr.Markdown(value=get_installed_jobs_as_text())
                    
                    install_cron_btn.click(
                        fn=install_cron_jobs,
                        inputs=[],
                        outputs=[cron_output, jobs_display]
                    )
                    
                    uninstall_cron_btn.click(
                        fn=uninstall_cron_jobs,
                        inputs=[],
                        outputs=[cron_output, jobs_display]
                    )
                    
                    refresh_jobs_btn.click(
                        fn=get_installed_jobs_as_text,
                        inputs=[],
                        outputs=[jobs_display]
                    )
        
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
            
            report_content = gr.Textbox(label="Podgląd raportu", lines=20, max_lines=30)
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
                """Ładuje zawartość raportu do podglądu (v2.0)."""
                from database_connection import get_summary_report_by_id
                import os
                
                if not report_id:
                    return "Wprowadź ID raportu", None
                
                try:
                    report = get_summary_report_by_id(int(report_id))
                    if not report:
                        return "Raport nie znaleziony", None
                    
                    file_path = report['file_path']
                    
                    if not os.path.exists(file_path):
                        return f"Plik nie istnieje: {file_path}", None
                    
                    # Wczytaj zawartość
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    return content, file_path
                except Exception as e:
                    return f"Błąd: {e}", None
            
            search_reports_btn.click(
                fn=search_summary_reports,
                inputs=[filter_company, filter_job],
                outputs=[reports_display]
            )
            
            download_report_btn.click(
                fn=load_report_content,
                inputs=[report_id_input],
                outputs=[report_content, download_file_output]
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
