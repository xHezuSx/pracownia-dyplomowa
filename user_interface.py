import gradio as gr
from scrape_script import scrape
from database_connection import pokaz_historie
from datetime import datetime
from ollama_manager import (
    get_available_models,
    get_installed_models,
    is_model_installed,
    pull_model,
    get_model_display_name,
)
import pandas as pd


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
    """Wrapper for the scrape function that converts Gradio DatePicker output
    to the dd-mm-yyyy string format expected by scrape(). If no date is
    selected, an empty string is passed (meaning 'all dates').
    
    Also checks if the selected Ollama model is installed; if not, downloads it first.
    """
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
            # If parsing fails, fallback to empty (treat as unspecified)
            date_str = ""
    
    # Extract actual model name (remove display markers like ✓ or ○)
    model_name = selected_model.split(" (")[0].replace("✓ ", "").replace("○ ", "")
    
    # Check if model is installed; if not, pull it
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
    
    # Now run the actual scrape function
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
    
    yield result


def get_model_choices():
    """Generate dropdown choices with installation status."""
    available = get_available_models()
    installed = get_installed_models()
    choices = []
    for model in available:
        is_installed = model in installed
        choices.append(get_model_display_name(model, is_installed))
    return choices


with gr.Blocks(title="GPW Scraping tool") as demo:
    """INTERFACE"""
    with gr.Row():
        with gr.Column():
            company_name = gr.Textbox(
                label="Company Name",
                info="What company report you would like to check?",
            )
            report_amount = gr.Slider(
                1,
                25,
                label="Report amount",
                info="How many reports would you like to take?",
                value=5,
                step=1,
            )
            with gr.Column():
                download_checkbox = gr.Checkbox(
                    value=True,
                    interactive=True,
                    label="Download the CSV report?",
                )
            with gr.Column():
                download_types_file = gr.Checkboxgroup(
                    ["PDF", "HTML"],
                    label="Download",
                    info="Some reports files may be heavy so downloading may take a while",
                )
        with gr.Column():
            date = gr.DateTime(
                include_time=False,
                type="string",
                label="Date (optional)",
                info="From which day you would like to check reports? If empty all dates will be taken.",
            )
            report_types = gr.Checkboxgroup(
                ["current", "semi-annual", "quarterly", "interim", "annual"],
                label="Report type",
                info="What type of report would you like to take?",
                value=["current", "semi-annual", "quarterly", "interim", "annual"],
            )
            categories = gr.Checkboxgroup(
                ["EBI", "ESPI"],
                label="Report category",
                info="What category of report would you like to take?",
                value=["EBI", "ESPI"],
            )
            
            # Model selection dropdown
            with gr.Row():
                model_dropdown = gr.Dropdown(
                    choices=get_model_choices(),
                    value=get_model_choices()[0] if get_model_choices() else "llama3.2:latest",
                    label="Ollama Model",
                    info="✓ = installed, ○ = will be downloaded automatically",
                    interactive=True,
                )
                refresh_btn = gr.Button("🔄", scale=0, size="sm")
            
            # Refresh button updates the dropdown choices
            refresh_btn.click(
                fn=lambda: gr.Dropdown(choices=get_model_choices()),
                inputs=[],
                outputs=[model_dropdown],
            )
        
        with gr.Column():
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
            historia_z_bazy = pokaz_historie()
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
            label="Scraped data",
            scale=5,
        )
    with gr.Row():
        submit_btn = gr.Button(
            value="Run",
            scale=1,
        )
    with gr.Row():
        output_text = gr.Textbox(label="Output", scale=1)
    with gr.Row():
        output_summaries = gr.Markdown(
            label="Summaries",
        )

        # Związanie funkcji z interfejsem - używamy wrappera który konwertuje
        # datę z DatePicker do formatu dd-mm-yyyy wymaganym przez scrape().
        # Generator function allows showing progress during model download.
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
            outputs=[output_text, output_dataframe, output_summaries],
        )

demo.launch()
