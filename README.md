# DataLens — Streamlit Auto Data Visualizer

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Push `app.py` and `requirements.txt` to a GitHub repository.
2. Sign in to Streamlit Community Cloud.
3. Create an app, select the repository and branch, and set the main file to `app.py`.
4. Deploy.

## Supported uploads
CSV, XLSX, XLS, and JSON.

## Current MVP
Automatic dataset profiling, missing-value and duplicate checks, descriptive statistics,
categorical summaries, single-column charts, correlations, scatter plots, date trends,
basic filtering, and CSV/Markdown exports.

## Important
This MVP runs analysis in memory. Do not upload confidential or personally identifiable
data to a public deployment unless you have appropriate access controls and a data policy.
Large files may exceed available memory or deployment limits.
