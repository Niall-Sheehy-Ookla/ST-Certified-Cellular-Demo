#!/bin/bash
# Skip Streamlit email prompt and start app

cd "/Users/niallsheehy/Documents/Cellular Scoring csv metric builder and scoring UI"
source venv/bin/activate

# Create config directory and disable analytics
mkdir -p ~/.streamlit

cat > ~/.streamlit/config.toml <<EOF
[browser]
gatherUsageStats = false

[client]
toolbarMode = "minimal"
showErrorDetails = true

[logger]
level = "info"
EOF

# Run Streamlit with email input disabled (just press enter/send empty)
echo "" | timeout 5 streamlit run app.py --server.headless=false 2>&1 || true

# If timeout occurs, that's fine - the server is running in background
# Start it again in proper mode
STREAMLIT_CLIENT_TOOLBARMODE=minimal STREAMLIT_BROWSER_GATHERUSAGESTATS=false streamlit run app.py --server.port=8501
