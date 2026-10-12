# Small Business Intelligence & Advisory Dashboard (Gemini AI)

A runnable academic prototype for small businesses and startups. It combines deterministic Python/Pandas calculations with Gemini-generated interpretation and a data-aware chat interface.

## Features
- Upload CSV or Excel business data
- Basic cleaning: duplicate rows removed, numeric/date columns parsed, missing values handled
- Revenue, estimated profit, costs, margin and units KPIs
- Filters, charts, data explorer, cleaned CSV download
- Rule-based observations calculated from the selected dataset
- Gemini AI report with prioritized recommendations
- Gemini chatbot that receives computed aggregates and grouped summaries
- Built-in sample dataset, so the dashboard opens without an external file

## Requirements
- Python 3.10+
- Internet connection for Gemini AI features
- A Gemini API key from Google AI Studio: https://aistudio.google.com/app/apikey

## Run on Windows
1. Extract the ZIP.
2. Open the extracted folder in VS Code.
3. Open Terminal in that folder and run:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

4. Open the local URL printed in the terminal, usually `http://localhost:8501`.

## Run on macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Enable Gemini AI
Option A (simplest for a demo): start the app, paste your API key into the password field in the sidebar, then click **Generate AI recommendations** or use the chat tab.

Option B: set an environment variable before launching Streamlit.

Windows PowerShell:
```powershell
$env:GEMINI_API_KEY="YOUR_KEY_HERE"
streamlit run app.py
```

macOS/Linux:
```bash
export GEMINI_API_KEY="YOUR_KEY_HERE"
streamlit run app.py
```

Get a key from Google AI Studio. API availability, quotas, model access and pricing/free-tier conditions depend on Google's current account and region policies. Never upload a real key to GitHub or include it in the ZIP.

## Expected data columns
Required: `Sales` or `Revenue`.
Recommended: `Date`, `Product`, `Category`, `Region`, `Cost` or `Expenses`, `Quantity`, `Customer`.
Column names such as `order_date`, `revenue`, `amount`, `qty`, `item`, `location`, and `expenses` are normalised where recognised.

If Cost is absent, the app uses 0 for cost and profit will equal sales; do not interpret that as actual profit. Replace demo data with authorized business data for real analysis.

## Important limitations
- This is an academic prototype, not a production SaaS product.
- Gemini uses aggregated metrics and grouped summaries, not the entire raw dataset. This reduces exposure but summaries may still contain business-sensitive information.
- Rule-based calculations are performed by Python; Gemini interprets those computed values and suggests actions. AI can make mistakes; verify recommendations.
- No user login, database persistence, role-based access or multi-tenant isolation is included.
- Excel upload requires `openpyxl`.
