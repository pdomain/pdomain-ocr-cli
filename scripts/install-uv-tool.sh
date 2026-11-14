#!/usr/bin/env bash
# install-uv-tool.sh — install pdomain-ocr as a uv tool, auto-detecting CUDA.
#
# Mirrors the original inline `install` recipe behavior: detects an NVIDIA
# GPU + CUDA version via nvidia-smi and passes `--torch-backend auto`, so uv
# picks the matching PyTorch CUDA build. Falls back to a friendly Apple
# Silicon note, otherwise installs CPU-only PyTorch. Log messages go to
# stdout to match prior behavior.
#
# Not the download.pytorch.org/whl/cuXXX index: it also serves old copies of
# common packages (packaging 24.1 at most), which breaks the resolve.
#
# Usage: scripts/install-uv-tool.sh

set -eu

TORCH_BACKEND=""
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    CUDA_VER=$(nvidia-smi 2>/dev/null | sed -n 's/.*CUDA \(UMD \)\{0,1\}Version: \([0-9]*\.[0-9]*\).*/\2/p' | head -1)
    if [ -n "$CUDA_VER" ]; then
        TORCH_BACKEND="auto"
        echo "🟢 Detected CUDA $CUDA_VER — uv will pick the matching PyTorch CUDA build."
    else
        echo "⚠️  nvidia-smi found but could not detect CUDA version — falling back to CPU."
    fi
elif [ "$(uname)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
    echo "🍎 Detected Apple Silicon — MPS acceleration will be used automatically."
else
    echo "💻 No GPU detected — installing CPU-only PyTorch."
fi

echo "📦 Installing pdomain-ocr from local source..."
if [ -n "$TORCH_BACKEND" ]; then
    uv tool install --reinstall . --torch-backend "$TORCH_BACKEND"
else
    uv tool install --reinstall .
fi
echo "✅ pdomain-ocr installed. Run: pdomain-ocr --version"
