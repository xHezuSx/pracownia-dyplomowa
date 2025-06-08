import gradio as gr
from scrape_script import scrape
from database_connection import pokaz_historie

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
            date = gr.Textbox(
                label="Date (optional)",
                info="From which day you would like to check reports? (dd-mm-yyyy). If empty all dates will be taken.",
                max_length=10,
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

        # Związanie funkcji z interfejsem
        submit_btn.click(
            fn=scrape,
            inputs=[
                company_name,
                report_amount,
                date,
                report_types,
                categories,
                download_checkbox,
                download_types_file,
            ],
            outputs=[output_text, output_dataframe, output_summaries],
        )

demo.launch()
