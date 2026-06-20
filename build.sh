# --- build.sh ---
#!/bin/bash
# Build script for Render - avoids Rust compilation

echo "🚀 Building Nexus Proxy Manager..."

# Install Python dependencies
cd proxy_manager
pip install --no-cache-dir --prefer-binary -r requirements.txt

# Verify installation
python -c "import fastapi; print('✅ FastAPI installed')"
python -c "import pydantic; print(f'✅ Pydantic {pydantic.__version__} installed')"

echo "✅ Build complete"
