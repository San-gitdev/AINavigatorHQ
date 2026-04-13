import os
import csv
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RUNS_DIR = "runs"

st.set_page_config(
    page_title="Model Zoo — scoring dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("Model Zoo — scoring dashboard")
st.caption(f"Reads CSVs from `{RUNS_DIR}/` · columns: Model, Final Score, Cost, Latency")

with st.expander("How is the score calculated?", expanded=False):
    st.markdown("""
**Final Score** is a composite metric that balances three dimensions:

| Dimension | Weight | What it measures |
|---|---|---|
| Task accuracy | 60% | Correctness of model outputs against ground-truth labels or rubric |
| Latency | 20% | Inverse of p50 response time — faster = higher contribution |
| Cost efficiency | 20% | Inverse of cost per call — cheaper = higher contribution |

The latency and cost components are min-max normalised across all models in a run before weighting,
so scores are always comparable within a run but should be interpreted with care across runs
where the model set differs.

> **Score = 0.6 × accuracy + 0.2 × norm(1/latency) + 0.2 × norm(1/cost)**

Scores range from 0 to 1. A score above **0.85** is considered strong for general-purpose tasks.
""")


# ── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data
def load_all_runs(runs_dir):
    data = []
    if not os.path.isdir(runs_dir):
        return pd.DataFrame()
    for file in sorted(os.listdir(runs_dir)):
        if file.endswith(".csv"):
            path = os.path.join(runs_dir, file)
            file_ts = datetime.fromtimestamp(
                os.path.getmtime(path)
            ).strftime("Run_%Y%m%d_%H%M%S")
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["Final Score"] = float(row["Final Score"])
                    row["Cost"] = float(row["Cost"])
                    row["Latency"] = float(row["Latency"])
                    row["Run"] = file_ts
                    data.append(row)
    return pd.DataFrame(data)


def pareto_frontier(df):
    pts = df[["Cost", "Final Score"]].values
    dominated = []
    for i, (ci, si) in enumerate(pts):
        for j, (cj, sj) in enumerate(pts):
            if i == j:
                continue
            if cj <= ci and sj >= si and (cj < ci or sj > si):
                dominated.append(i)
                break
    return df.drop(index=df.index[dominated]).sort_values("Cost")


# ── Sidebar: upload or point to folder ───────────────────────────────────────

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader(
        "Upload CSV files", type="csv", accept_multiple_files=True
    )
    st.caption("Or place CSVs in the `runs/` folder next to this script.")
    st.divider()
    st.header("Filters")

if uploaded:
    frames = []
    for f in uploaded:
        sub = pd.read_csv(f)
        ts = datetime.now().strftime("Run_%Y%m%d_%H%M%S")
        sub["Run"] = f.name.replace(".csv", "") + "_" + ts
        frames.append(sub)
    df_raw = pd.concat(frames, ignore_index=True)
    df_raw["Final Score"] = df_raw["Final Score"].astype(float)
    df_raw["Cost"] = df_raw["Cost"].astype(float)
    df_raw["Latency"] = df_raw["Latency"].astype(float)
else:
    df_raw = load_all_runs(RUNS_DIR)

if df_raw.empty:
    st.warning(
        f"No data found. Upload CSV files above or add them to `{RUNS_DIR}/`."
    )
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────

with st.sidebar:
    all_runs = sorted(df_raw["Run"].unique())
    selected_runs = st.multiselect("Runs", all_runs, default=all_runs)

    all_models = sorted(df_raw["Model"].unique())
    selected_models = st.multiselect("Models", all_models, default=all_models)

    score_range = st.slider(
        "Final score range",
        float(df_raw["Final Score"].min()),
        float(df_raw["Final Score"].max()),
        (float(df_raw["Final Score"].min()), float(df_raw["Final Score"].max())),
        step=0.01,
    )

df = df_raw[
    df_raw["Run"].isin(selected_runs)
    & df_raw["Model"].isin(selected_models)
    & df_raw["Final Score"].between(*score_range)
].copy()

if df.empty:
    st.warning("No rows match the current filters.")
    st.stop()

# ── Summary metric cards ──────────────────────────────────────────────────────

best = df.loc[df["Final Score"].idxmax()]
cheapest = df.loc[df["Cost"].idxmin()]
fastest = df.loc[df["Latency"].idxmin()]
avg_score = df["Final Score"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows loaded", len(df), f"{df['Run'].nunique()} run(s)")
c2.metric("Top scorer", f"{best['Final Score']:.3f}", best["Model"])
c3.metric("Lowest cost", f"${cheapest['Cost']:.4f}", cheapest["Model"])
c4.metric("Fastest", f"{fastest['Latency']:.2f}s", fastest["Model"])

st.divider()

# ── Tab layout ────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Score vs cost",
    "Score vs latency",
    "Score ranking",
    "Heatmap",
    "Raw data",
])

# Tab 1 — Score vs Cost + Pareto
with tab1:
    fig = px.scatter(
        df, x="Cost", y="Final Score",
        color="Run", text="Model",
        hover_data={"Model": True, "Cost": ":.4f",
                    "Final Score": ":.3f", "Latency": ":.2f"},
        title="Final score vs cost",
        labels={"Cost": "Cost (USD)", "Final Score": "Final score"},
    )
    fig.update_traces(
        textposition="top center",
        textfont=dict(size=10, color="#1a1a1a"),
        marker_size=10,
    )

    front = pareto_frontier(df)
    fig.add_trace(go.Scatter(
        x=front["Cost"], y=front["Final Score"],
        mode="lines",
        name="Pareto frontier",
        line=dict(color="rgba(150,150,150,0.5)", dash="dot", width=1.5),
        hoverinfo="skip",
    ))

    fig.update_layout(height=480, plot_bgcolor="white")
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    st.plotly_chart(fig, width=stretch)
    st.caption(
        "Points on the Pareto frontier are non-dominated — no other model is "
        "simultaneously cheaper and higher-scoring."
    )

# Tab 2 — Score vs Latency
with tab2:
    fig2 = px.scatter(
        df, x="Latency", y="Final Score",
        color="Run", text="Model",
        hover_data={"Model": True, "Latency": ":.2f",
                    "Final Score": ":.3f", "Cost": ":.4f"},
        title="Final score vs latency",
        labels={"Latency": "Latency (s)", "Final Score": "Final score"},
    )
    fig2.update_traces(
        textposition="top center",
        textfont=dict(size=10, color="#1a1a1a"),
        marker_size=10,
    )
    fig2.update_layout(height=480, plot_bgcolor="white")
    fig2.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
    fig2.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    st.plotly_chart(fig2, width=stretch)

# Tab 3 — Score ranking bar chart
with tab3:
    avg_model = (
        df.groupby("Model")["Final Score"]
        .mean()
        .reset_index()
        .rename(columns={"Final Score": "Avg Score"})
        .sort_values("Avg Score", ascending=True)
    )
    fig3 = go.Figure(go.Bar(
        x=avg_model["Avg Score"],
        y=avg_model["Model"],
        orientation="h",
        text=[f"{v:.3f}" for v in avg_model["Avg Score"]],
        textposition="outside",
        textfont=dict(size=11, color="#1a1a1a"),
        marker=dict(
            color=avg_model["Avg Score"],
            colorscale="Blues",
            showscale=False,
        ),
    ))
    x_min = avg_model["Avg Score"].min()
    x_pad = (1.0 - x_min) * 0.15
    fig3.update_layout(
        title="Average final score per model (all runs combined)",
        height=max(300, len(avg_model) * 44 + 100),
        plot_bgcolor="white",
        xaxis=dict(
            title="Avg final score",
            showgrid=True,
            gridcolor="#f0f0f0",
            range=[max(0, x_min - x_pad), min(1.05, 1.0 + x_pad)],
        ),
        yaxis=dict(title="", automargin=True),
        margin=dict(l=10, r=60, t=60, b=40),
    )
    st.plotly_chart(fig3, width=stretch)
    st.caption(
        "Each bar is the mean Final Score across all selected runs for that model. "
        "Colour intensity encodes score — darker = higher."
    )

# Tab 4 — Heatmap: model vs metrics
with tab4:
    agg = df.groupby("Model").agg(
        Avg_Score=("Final Score", "mean"),
        Avg_Cost=("Cost", "mean"),
        Avg_Latency=("Latency", "mean"),
    ).reset_index()

    def minmax_norm(s):
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else s * 0 + 0.5

    norm = agg.copy()
    norm["Score (higher = better)"]   = minmax_norm(agg["Avg_Score"])
    norm["Cost (lower = better)"]     = 1 - minmax_norm(agg["Avg_Cost"])
    norm["Latency (lower = better)"]  = 1 - minmax_norm(agg["Avg_Latency"])

    metrics = ["Score (higher = better)", "Cost (lower = better)", "Latency (lower = better)"]
    heat_vals = norm[metrics].values
    models_list = norm["Model"].tolist()

    raw_labels = []
    for _, row in agg.iterrows():
        raw_labels.append([
            f"{row['Avg_Score']:.3f}",
            f"${row['Avg_Cost']:.4f}",
            f"{row['Avg_Latency']:.2f}s",
        ])

    fig4 = go.Figure(go.Heatmap(
        z=heat_vals,
        x=metrics,
        y=models_list,
        text=raw_labels,
        texttemplate="%{text}",
        textfont=dict(size=11, color="#1a1a1a"),
        colorscale="Blues",
        showscale=True,
        colorbar=dict(title="Normalised<br>score", tickvals=[0, 0.5, 1],
                      ticktext=["worst", "mid", "best"]),
        hovertemplate=(
            "<b>%{y}</b><br>%{x}<br>"
            "Raw value: %{text}<br>"
            "Normalised: %{z:.2f}<extra></extra>"
        ),
    ))
    fig4.update_layout(
        title="Model comparison — score, cost and latency (normalised)",
        height=max(320, len(models_list) * 50 + 120),
        plot_bgcolor="white",
        xaxis=dict(side="top", tickfont=dict(size=12)),
        yaxis=dict(automargin=True),
        margin=dict(t=100, b=20, l=10, r=10),
    )
    st.plotly_chart(fig4, width=stretch)
    st.caption(
        "All three metrics are min-max normalised so they share the same 0–1 scale. "
        "Cost and latency are inverted (lower raw value → higher normalised score = darker cell). "
        "Cell labels show the actual raw averages across all selected runs."
    )

# Tab 5 — Raw data table
with tab5:
    sort_col = st.selectbox(
        "Sort by", ["Final Score", "Cost", "Latency", "Model", "Run"],
        index=0,
    )
    asc = st.checkbox("Ascending", value=False)
    st.dataframe(
        df.sort_values(sort_col, ascending=asc).reset_index(drop=True),
        width=stretch,
        hide_index=True,
    )
    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        "Download filtered data as CSV",
        csv_bytes,
        file_name=f"filtered_runs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )