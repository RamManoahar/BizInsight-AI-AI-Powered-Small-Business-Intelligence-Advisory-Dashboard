import os
import io
import json
import pandas as pd
import streamlit as st
import plotly.express as px
from google import genai

st.set_page_config(page_title="Small Business Intelligence & Advisory", page_icon="📊", layout="wide")

st.markdown("""
<style>
.main-header {font-size: 2.1rem; font-weight: 800; margin-bottom: 0.1rem;}
.sub-header {color: #64748b; margin-bottom: 1.3rem;}
div[data-testid="stMetric"] {background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 Small Business Intelligence & Advisory Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Turn business data into measurable insights and AI-assisted decisions.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Workspace")
    uploaded = st.file_uploader("Upload business data (CSV or Excel)", type=["csv", "xlsx"])
    st.caption("Expected columns can include Date, Product, Category, Region, Sales, Cost, Quantity, Customer.")
    st.divider()
    api_key_input = st.text_input("Gemini API key (optional)", type="password", help="Alternatively set GEMINI_API_KEY in your environment.")
    model_name = st.selectbox("Gemini model", ["gemini-2.5-flash", "gemini-2.0-flash"], index=0)
    st.caption("Your API key is used only for this app session. Never commit it to GitHub.")

@st.cache_data
def load_sample():
    return pd.read_csv(Path(__file__).parent / "data" / "sample_business_data.csv")

def load_uploaded(file):
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)

def normalise_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    lookup = {c.lower().replace(" ", "_"): c for c in df.columns}
    aliases = {
        "date": ["date", "order_date", "transaction_date"],
        "sales": ["sales", "revenue", "amount", "total_sales"],
        "cost": ["cost", "expenses", "expense", "total_cost"],
        "quantity": ["quantity", "qty", "units", "units_sold"],
        "product": ["product", "item", "product_name"],
        "category": ["category", "product_category"],
        "region": ["region", "location", "city", "area"],
        "customer": ["customer", "customer_name", "client"],
    }
    rename = {}
    for standard, options in aliases.items():
        for option in options:
            if option in lookup:
                rename[lookup[option]] = standard.title() if standard in ["date", "product", "category", "region", "customer"] else standard.title()
                break
    return df.rename(columns=rename)

if uploaded:
    try:
        raw_df = load_uploaded(uploaded)
        data_source = f"Uploaded: {uploaded.name}"
    except Exception as e:
        st.error(f"Could not read uploaded file: {e}")
        st.stop()
else:
    raw_df = load_sample()
    data_source = "Built-in demo dataset"

df = normalise_columns(raw_df)
original_rows = len(df)
duplicate_rows = int(df.duplicated().sum())
missing_cells = int(df.isna().sum().sum())

# Clean data safely: remove fully duplicated rows, parse dates, coerce numeric business columns.
df = df.drop_duplicates().copy()
if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
for col in ["Sales", "Cost", "Quantity"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
numeric_cols = df.select_dtypes(include="number").columns.tolist()
for col in numeric_cols:
    df[col] = df[col].fillna(df[col].median() if df[col].notna().any() else 0)
for col in df.select_dtypes(include="object").columns:
    df[col] = df[col].fillna("Unknown")

if "Sales" not in df.columns:
    st.error("A sales/revenue column is required. Rename one column to Sales or Revenue and upload again.")
    st.stop()
if "Cost" not in df.columns:
    df["Cost"] = 0.0
if "Quantity" not in df.columns:
    df["Quantity"] = 1
df["Profit"] = df["Sales"] - df["Cost"]
df["Profit Margin %"] = (df["Profit"] / df["Sales"].replace(0, pd.NA) * 100).fillna(0)

st.caption(f"Data source: **{data_source}** · {len(df):,} cleaned rows · {len(df.columns)} columns")

# Filters
with st.expander("🔎 Filter the data", expanded=True):
    f1, f2, f3 = st.columns(3)
    filtered = df.copy()
    if "Region" in df.columns:
        regions = sorted(df["Region"].astype(str).unique())
        selected_regions = f1.multiselect("Region", regions, default=regions)
        filtered = filtered[filtered["Region"].astype(str).isin(selected_regions)]
    if "Category" in df.columns:
        categories = sorted(df["Category"].astype(str).unique())
        selected_categories = f2.multiselect("Category", categories, default=categories)
        filtered = filtered[filtered["Category"].astype(str).isin(selected_categories)]
    if "Product" in df.columns:
        products = sorted(df["Product"].astype(str).unique())
        selected_products = f3.multiselect("Product", products, default=products)
        filtered = filtered[filtered["Product"].astype(str).isin(selected_products)]

if filtered.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

revenue = float(filtered["Sales"].sum())
cost = float(filtered["Cost"].sum())
profit = float(filtered["Profit"].sum())
margin = (profit / revenue * 100) if revenue else 0
quantity = float(filtered["Quantity"].sum())

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Revenue", f"₹{revenue:,.0f}")
m2.metric("Estimated profit", f"₹{profit:,.0f}")
m3.metric("Costs", f"₹{cost:,.0f}")
m4.metric("Profit margin", f"{margin:.1f}%")
m5.metric("Units sold", f"{quantity:,.0f}")

overview, insights_tab, data_tab, ai_tab, chat_tab = st.tabs(
    ["📈 Overview", "🧭 Business insights", "🧹 Data quality & explorer", "✨ Gemini AI advisor", "💬 Ask your business"]
)

def summary_for_ai(data):
    result = {
        "row_count": int(len(data)),
        "total_revenue": round(float(data["Sales"].sum()), 2),
        "total_cost": round(float(data["Cost"].sum()), 2),
        "estimated_profit": round(float(data["Profit"].sum()), 2),
        "profit_margin_percent": round(float((data["Profit"].sum() / data["Sales"].sum() * 100) if data["Sales"].sum() else 0), 2),
        "total_quantity": round(float(data["Quantity"].sum()), 2),
    }
    for col in ["Product", "Category", "Region"]:
        if col in data.columns:
            group = data.groupby(col, dropna=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).sort_values("Sales", ascending=False).head(8)
            result[f"top_by_{col.lower()}"] = group.round(2).reset_index().to_dict(orient="records")
    if "Date" in data.columns and data["Date"].notna().any():
        monthly = data.dropna(subset=["Date"]).assign(Month=lambda x: x["Date"].dt.to_period("M").astype(str)).groupby("Month").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).tail(12)
        result["monthly_trend"] = monthly.round(2).reset_index().to_dict(orient="records")
    return result

with overview:
    left, right = st.columns(2)
    if "Date" in filtered.columns and filtered["Date"].notna().any():
        trend = filtered.dropna(subset=["Date"]).assign(Month=lambda x: x["Date"].dt.to_period("M").astype(str)).groupby("Month", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).sort_values("Month")
        left.plotly_chart(px.line(trend, x="Month", y=["Sales", "Profit"], markers=True, title="Monthly revenue vs profit"), use_container_width=True)
    else:
        left.info("Add a Date column to see monthly trends.")
    if "Product" in filtered.columns:
        product_perf = filtered.groupby("Product", as_index=False).agg(Sales=("Sales", "sum")).sort_values("Sales", ascending=False).head(10)
        right.plotly_chart(px.bar(product_perf, x="Product", y="Sales", title="Top products by revenue"), use_container_width=True)
    elif "Category" in filtered.columns:
        category_perf = filtered.groupby("Category", as_index=False).agg(Sales=("Sales", "sum"))
        right.plotly_chart(px.pie(category_perf, names="Category", values="Sales", title="Revenue by category"), use_container_width=True)
    st.plotly_chart(px.scatter(filtered, x="Cost", y="Sales", color="Category" if "Category" in filtered.columns else None,
                               hover_data=[c for c in ["Product", "Region", "Quantity"] if c in filtered.columns],
                               title="Sales vs costs"), use_container_width=True)

with insights_tab:
    st.subheader("Rule-based findings from the selected data")
    findings = []
    if margin < 10:
        findings.append(("⚠️ Low profit margin", f"Current overall margin is {margin:.1f}%. Review costs, pricing, discounts, and product mix."))
    else:
        findings.append(("✅ Profit margin snapshot", f"Current overall margin is {margin:.1f}%. Compare it against your target margin and historical performance."))
    if "Product" in filtered.columns:
        pp = filtered.groupby("Product").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).sort_values("Sales", ascending=False)
        if len(pp):
            findings.append(("🏆 Top revenue product", f"{pp.index[0]} contributes the highest revenue in the current selection (₹{pp.iloc[0]['Sales']:,.0f})."))
            low_profit = pp.sort_values("Profit").head(1)
            findings.append(("🔍 Product to review", f"{low_profit.index[0]} has the lowest total profit in the current selection (₹{low_profit.iloc[0]['Profit']:,.0f}); check unit costs and discounts."))
    if "Date" in filtered.columns and filtered["Date"].notna().any():
        monthly = filtered.dropna(subset=["Date"]).assign(Month=lambda x: x["Date"].dt.to_period("M").astype(str)).groupby("Month")["Sales"].sum().sort_index()
        if len(monthly) >= 2:
            change = ((monthly.iloc[-1] - monthly.iloc[-2]) / abs(monthly.iloc[-2]) * 100) if monthly.iloc[-2] else 0
            findings.append(("📅 Latest monthly movement", f"Revenue changed by {change:+.1f}% from the previous available month. Check seasonality and transaction volume before concluding why."))
    for title, body in findings:
        st.markdown(f"**{title}**  \n{body}")
        st.divider()
    st.caption("These are deterministic, rule-based observations. Gemini AI can provide contextual interpretation in the AI Advisor tab.")

with data_tab:
    st.subheader("Data quality")
    q1, q2, q3 = st.columns(3)
    q1.metric("Original rows", f"{original_rows:,}")
    q2.metric("Duplicate rows removed", f"{duplicate_rows:,}")
    q3.metric("Missing cells detected before cleaning", f"{missing_cells:,}")
    st.write("Cleaned data preview")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download filtered cleaned CSV", filtered.to_csv(index=False).encode("utf-8"), "cleaned_business_data.csv", "text/csv")
    st.write("Column types")
    st.dataframe(pd.DataFrame({"Column": df.columns, "Data type": [str(t) for t in df.dtypes]}), use_container_width=True, hide_index=True)

def get_gemini_client():
    key = api_key_input.strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    return genai.Client(api_key=key)

def ask_gemini(prompt, data_summary):
    client = get_gemini_client()
    if client is None:
        raise ValueError("Gemini API key is missing. Enter it in the sidebar or set GEMINI_API_KEY, then rerun the app.")
    instruction = """You are a careful business intelligence advisor for small businesses and startups.
Use only the supplied computed business summary. Do not invent data or claim causation from correlation.
Clearly distinguish observed facts from hypotheses. Give practical, prioritized actions. If a metric is absent, say so.
Avoid guaranteeing outcomes. Mention that financial decisions should be checked by the business owner.
Respond in clear, student-demo-friendly English."""
    response = client.models.generate_content(
        model=model_name,
        contents=instruction + "\n\nCOMPUTED DATA SUMMARY:\n" + json.dumps(data_summary, ensure_ascii=False) + "\n\nUSER REQUEST:\n" + prompt
    )
    return response.text or "Gemini returned an empty response."

summary = summary_for_ai(filtered)
with ai_tab:
    st.subheader("Gemini AI business analysis")
    st.write("Gemini receives aggregated metrics and grouped summaries—not the entire raw dataset—and generates recommendations grounded in those calculations.")
    if st.button("✨ Generate AI recommendations", type="primary"):
        with st.spinner("Gemini is analyzing the computed business summary..."):
            try:
                st.session_state["ai_report"] = ask_gemini(
                    "Analyze the business performance. Provide: (1) executive summary, (2) key findings, (3) risks or data limitations, (4) five prioritized actions, and (5) metrics to monitor next month.",
                    summary
                )
            except Exception as e:
                st.error(f"Could not generate AI analysis: {e}")
    if st.session_state.get("ai_report"):
        st.markdown(st.session_state["ai_report"])

with chat_tab:
    st.subheader("Ask questions about your business data")
    st.caption("Example: Which product should I investigate first? Why might profit margin be low? What should I monitor next month?")
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    question = st.chat_input("Ask a question about the selected business data...")
    if question:
        st.session_state["chat_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Checking the data summary and asking Gemini..."):
                try:
                    answer = ask_gemini(question, summary)
                except Exception as e:
                    answer = f"Gemini request failed: {e}"
                st.markdown(answer)
        st.session_state["chat_history"].append({"role": "assistant", "content": answer})

st.divider()
st.caption("Academic prototype • Use business data you are authorized to process • AI outputs are advisory and should be verified.")
