#!/usr/bin/env python3
"""
Main Entry Point for GPW Scraper
Modern entry point using refactored architecture.
"""

import sys
from src.ui.app import launch

def main():
    """Launch the GPW Scraper application."""
    print("🚀 Starting GPW Scraper...")
    print("   Using refactored architecture (src/)")
    launch()

if __name__ == "__main__":
    main()
