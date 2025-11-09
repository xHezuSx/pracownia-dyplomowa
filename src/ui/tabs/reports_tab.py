"""
Reports Tab - Browse and download collective reports
"""

import gradio as gr
import os
import base64
from database_connection import get_summary_reports, get_summary_report_by_id


def search_summary_reports(company_filter, job_filter):
    """Search collective reports from database."""
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
    """
    Load report content for preview (returns HTML for PDF viewer and file path).
    """
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
            # PDF - embed as iframe with base64
            try:
                with open(file_path, 'rb') as f:
                    pdf_data = base64.b64encode(f.read()).decode('utf-8')

                # Create HTML with embedded PDF
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
            # Markdown/text - show as preformatted HTML
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


def create_reports_tab():
    """Create the Reports tab UI."""
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
        
        # Report preview - PDF (full width)
        report_pdf_viewer = gr.HTML(
            label="📋 Podgląd PDF",
            value="<p style='text-align: center; color: gray;'>PDF pojawi się tutaj...</p>"
        )

        download_file_output = gr.File(label="Pobierz plik")
        
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
        
        return {
            'reports_display': reports_display,
            'report_pdf_viewer': report_pdf_viewer,
        }
