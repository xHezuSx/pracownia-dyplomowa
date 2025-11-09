"""
Info Tab - Documentation and project information
"""

import gradio as gr


def create_info_tab():
    """Create the Info tab UI."""
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
            ├── src/                  # Kod źródłowy (refactored)
            │   ├── core/             # Business logic
            │   ├── database/         # Database layer
            │   ├── automation/       # CRON management
            │   ├── ui/               # Gradio interface
            │   └── utils/            # Utilities
            └── ...
            ```
            
            ## 📚 Więcej informacji
            
            - [docs/CRON_AUTOMATION.md](./docs/CRON_AUTOMATION.md) - Pełna dokumentacja automatyzacji
            - [docs/DATABASE_DIAGRAM.md](./docs/DATABASE_DIAGRAM.md) - Schemat bazy danych
            - [README.md](./README.md) - Ogólny opis projektu
            
            ## 🛠️ Technologie
            
            - **Backend:** Python 3.12, BeautifulSoup4, PyMySQL, Pandas
            - **AI:** Ollama, LangChain, HuggingFace Embeddings
            - **Frontend:** Gradio 5.12.0
            - **Automatyzacja:** Cron, JSON configs
            - **GPU:** CUDA (optional, dla przyspieszenia)
            
            ---
            
            **Wersja:** 2.0 (Refactored)  
            **Data:** 09.11.2025  
            **Autor:** GPW Scraper Team
            """
        )
