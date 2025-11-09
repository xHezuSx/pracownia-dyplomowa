#!/usr/bin/env python3
"""
GPW Scraper - Main Gradio Interface (Refactored)
=================================================

Main application file that assembles all UI tabs into a single Gradio interface.

Features:
- 🔍 Manual scraping and analysis
- ⏰ Job automation with cron scheduling
- 📊 Active schedules monitoring
- 📚 Collective reports browser
- ℹ️ Documentation and info

Usage:
    python -m src.ui.app
    # or from root after creating wrapper:
    python app.py
"""

import gradio as gr
from .shared_utils import get_model_choices
from .tabs import (
    create_scraping_tab,
    create_automation_tab,
    create_schedules_tab,
    create_reports_tab,
    create_info_tab,
    refresh_companies_dropdown,
)


def create_demo():
    """
    Create and configure the main Gradio demo interface.
    
    Returns:
        gr.Blocks: Configured Gradio application
    """
    with gr.Blocks(title="GPW Scraper") as demo:
        gr.Markdown("# 📊 GPW Scraper - Narzędzie do analizy raportów giełdowych")
        gr.Markdown(
            "Scraping raportów z GPW + automatyczne podsumowania AI + harmonogram cron"
        )
        
        # Create shared components OUTSIDE of Blocks context
        # These will be placed in specific tabs but need to be created first
        model_dropdown = gr.Dropdown(
            choices=get_model_choices(),
            value=get_model_choices()[0] if get_model_choices() else "llama3.2:latest",
            label="Model Ollama",
            info="✓ = zainstalowany, ○ = zostanie pobrany automatycznie",
            interactive=True,
            visible=False  # Will be made visible in scraping tab
        )
        refresh_model_btn = gr.Button("🔄", scale=0, size="sm", visible=False)
        
        # Refresh model dropdown callback
        refresh_model_btn.click(
            fn=lambda: get_model_choices(),
            inputs=[],
            outputs=[model_dropdown],
        )
        
        with gr.Tabs():
            # Tab 1: Scraping
            scraping_components = create_scraping_tab(model_dropdown, refresh_model_btn)
            
            # Tab 2: Automation
            automation_components = create_automation_tab()
            
            # Tab 3: Active Schedules
            schedules_components = create_schedules_tab()
            
            # Tab 4: Reports Browser
            reports_components = create_reports_tab()
            
            # Tab 5: Info
            create_info_tab()
        
        # Auto-load on startup
        demo.load(
            fn=refresh_companies_dropdown,
            outputs=[scraping_components['company_name']]
        )
    
    return demo


def launch(server_name="127.0.0.1", server_port=7860, share=False, **kwargs):
    """
    Launch the Gradio application.
    
    Args:
        server_name: Host address (default: localhost)
        server_port: Port number (default: 7860)
        share: Create public link (default: False)
        **kwargs: Additional Gradio launch arguments
    """
    demo = create_demo()
    demo.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        show_error=True,
        show_api=False,  # Workaround for Gradio 5.12.0 DataFrame bug
        **kwargs
    )


if __name__ == "__main__":
    launch()
