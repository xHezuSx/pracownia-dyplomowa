#!/usr/bin/env bash
set -euo pipefail

# install_ollama.sh
# Purpose: attempt to install Ollama on Linux using the official install script.
# Note: This script calls the upstream installer. Review before running.

print_usage() {
  cat <<EOF
Usage: install_ollama.sh

This script downloads and runs the official Ollama installer. It will:
 - detect if curl is available
 - download the official install script and run it (may require sudo)

If you prefer manual installation, visit https://ollama.com/
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

# If ollama is already installed, skip installation.
if command -v ollama >/dev/null 2>&1; then
  echo "Ollama is already installed at: $(command -v ollama). Skipping installation."
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not installed. Please install curl and re-run."
  exit 1
fi

TMP_SCRIPT=$(mktemp)
trap 'rm -f "$TMP_SCRIPT"' EXIT

echo "Downloading Ollama installer..."
# Official installer URL used by Ollama website. Review before running.
curl -fsSL https://ollama.com/install.sh -o "$TMP_SCRIPT"

echo "Installer downloaded to $TMP_SCRIPT"

read -p "Run the installer now? (requires sudo) [y/N]: " yn
case "$yn" in
  [Yy]* ) ;;
  * ) echo "Aborted by user."; exit 1 ;;
esac

chmod +x "$TMP_SCRIPT"

# Run installer with sudo if not root
if [[ "$EUID" -ne 0 ]]; then
  sudo "$TMP_SCRIPT"
else
  "$TMP_SCRIPT"
fi

echo "If the installer completed, verify by running: ollama --version"

exit 0
