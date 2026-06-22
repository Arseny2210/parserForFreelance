#!/bin/bash
python -m playwright install chromium 2>&1 &
streamlit run streamlit_app.py --server.port="${PORT:-10000}" --server.address=0.0.0.0