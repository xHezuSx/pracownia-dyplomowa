"""
Scraping Tab - Manual report scraping and analysis
"""

import gradio as gr
import pandas as pd
from datetime import datetime
from scrape_script import scrape
from database_connection import get_search_history, get_all_companies
from ollama_manager import is_model_installed, pull_model


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
    """
    Wrapper for scrape function with automatic model downloading.
    Yields progress updates during execution.
    """
    # Validate company name
    if not company_name or company_name.strip() == "":
        yield (
            "❌ Błąd: Nie wybrano firmy!\nProszę wybrać firmę z listy.",
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
            "*Błąd: Brak nazwy firmy*",
            "*Błąd: Brak nazwy firmy*"
        )
        return
    
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
    
    # Extract model name (remove ✓ / ○ markers)
    model_name = selected_model.split(" (")[0].replace("✓ ", "").replace("○ ", "")
    
    # Check if model is installed
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
            "*Pobieranie modelu...*"
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
                "*Pobieranie nieudane*"
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
            "*Model gotowy...*"
        )
    
    # Execute scraping
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
    
    # Unpack result (handles multiple versions)
    if len(result) == 6:
        summary_text, df, summaries, summary_report_path, collective_summary, downloaded_files = result
        
        # Add collective report info to status
        if summary_report_path:
            summary_text += f"\n\n📄 **Zbiorczy raport zapisany:** `{summary_report_path}`"
        
        # Fallback if no collective summary
        if not collective_summary or collective_summary.strip() == "":
            collective_summary = "*Brak zbiorczego podsumowania (nie wygenerowano streszczeń)*"
        
        result = (summary_text, df, summaries, collective_summary)
    elif len(result) == 5:
        # Fallback for old version (5 elements)
        summary_text, df, summaries, summary_report_path, collective_summary = result
        if summary_report_path:
            summary_text += f"\n\n📄 **Zbiorczy raport zapisany:** `{summary_report_path}`"
        result = (summary_text, df, summaries, collective_summary)
    else:
        # Very old version (4 elements) - fallback
        summary_text, df, summaries, summary_report_path = result
        if summary_report_path:
            summary_text += f"\n\n📄 **Zbiorczy raport zapisany:** `{summary_report_path}`"
        result = (summary_text, df, summaries, "*Brak zbiorczego podsumowania*")
    
    yield result


def refresh_companies_dropdown():
    """Fetch company list from database"""
    companies = get_all_companies()
    company_names = sorted([c.get('name', c) if isinstance(c, dict) else str(c) for c in companies])
    return gr.update(choices=company_names)


def refresh_search_history():
    """Refresh search history from database (last 2 searches)"""
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
    
    # Get search history from database (last 2 searches only)
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


def create_scraping_tab(model_dropdown, refresh_model_btn):
    """
    Create the Scraping tab UI.
    
    Args:
        model_dropdown: Shared model dropdown component (created externally)
        refresh_model_btn: Shared refresh button for models
    
    Returns:
        dict: Dictionary of components for external references
    """
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
                
                refresh_companies_scraping.click(
                    fn=refresh_companies_dropdown,
                    inputs=[],
                    outputs=[company_name]
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
                
                # Model selection (shared components from parent)
                # Make them visible in this tab
                model_dropdown.visible = True
                refresh_model_btn.visible = True
                
                with gr.Row():
                    model_dropdown
                    refresh_model_btn
            
            with gr.Column():
                # Search history
                gr.Markdown("### 📜 Historia wyszukiwań (ostatnie 2)")
                
                history = gr.Markdown(
                    value=refresh_search_history(),
                    label="SEARCH HISTORY",
                )
                
                # Refresh history button
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
        
        # Collective LLM report
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
        
        return {
            'company_name': company_name,
            'refresh_companies': refresh_companies_scraping,
        }
