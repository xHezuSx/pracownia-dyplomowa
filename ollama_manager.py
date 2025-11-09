"""Backward compatibility wrapper for src.utils.ollama_utils"""
from src.utils.ollama_utils import (
    is_ollama_available, get_installed_models, get_available_models,
    is_model_installed, pull_model, get_model_display_name
)
__all__ = ['is_ollama_available', 'get_installed_models', 'get_available_models', 
           'is_model_installed', 'pull_model', 'get_model_display_name']
