"""HR Analytics - interactive Streamlit report.   Run:  streamlit run app.py"""
import io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_cleaning import load_clean, AGE_ORDER, SLAB_ORDER, ORDERS

st.set_page_config(page_title="HR Analytics Report", page_icon="📊", layout="wide")

PAL = {"No": "#4F46E5", "Yes": "#F97316"}
SEQ = ["#E0E7FF", "#818CF8", "#4F46E5", "#312E81"]
ACCENT, MUTED = "#4F46E5", "#94A3B8"

st.markdown("""
<style>
.block-container{padding-top:1.4rem;max-width:1300px}
.hero{background:linear-gradient(120deg,#312E81,#4F46E5 60%,#818CF8);color:#fff;padding:1.6rem 2rem;border-radius:16px;margin-bottom:1rem}
.hero h1{margin:0;font-size:2rem;color:#fff}.hero p{margin:.3rem 0 0;opacity:.9}
div[data-testid="stMetric"]{background:#F3F4F8;border-radius:12px;padding:.8rem 1rem;border-left:5px solid #4F46E5}
.insight{background:#EEF2FF;border-left:4px solid #4F46E5;padding:.7rem 1rem;border-radius:8px;margin:.4rem 0 1rem;color:#1F2937}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading & cleaning data…")
def get_data():
    raw, df, log = load_clean()
    return raw, df, log


raw, df_all, clean_log = get_data()


def style(fig, h=380):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=50, b=10), template="plotly_white",
                      legend_title_text="", font=dict(size=13))
    return fig


def insight(txt):
    st.markdown(f"<div class='insight'>💡 {txt}</div>", unsafe_allow_html=True)


def rate_by(d, col):
    g = d.groupby(col, observed=True)["AttritionFlag"].agg(["mean", "sum", "count"]).reset_index()
    g.columns = [col, "AttritionRate", "Leavers", "Employees"]
    g["AttritionRate"] *= 100
    return g


def rate_bar(d, col, title=None, orient="v", h=360):
    g = rate_by(d, col)
    if orient == "h":
        g = g.sort_values("AttritionRate")
    fig = px.bar(g, x="AttritionRate" if orient == "h" else col, y=col if orient == "h" else "AttritionRate",
                 orientation=orient, color="AttritionRate", color_continuous_scale=SEQ,
                 hover_data={"Leavers": True, "Employees": True, "AttritionRate": ":.1f"},
                 text=g["AttritionRate"].round(1).astype(str) + "%",
                 title=title or f"Attrition rate by {col}")
    fig.update_traces(textposition="outside")
    fig.update_coloraxes(showscale=False)
    fig.update_yaxes(title="Attrition %" if orient == "v" else "")
    fig.update_xaxes(title="Attrition %" if orient == "h" else "")
    return style(fig, h)


# ───────────────────────── Sidebar filters ─────────────────────────
st.sidebar.title("🔎 Filters")
def multi(label, col, order=None):
    opts = order or sorted(df_all[col].dropna().astype(str).unique())
    return st.sidebar.multiselect(label, opts, default=opts)

dept = multi("Department", "Department")
role = multi("Job role", "JobRole")
gender = multi("Gender", "Gender")
age = multi("Age group", "AgeGroup", AGE_ORDER)
slab = multi("Salary slab", "SalarySlab", SLAB_ORDER)
ot = multi("Over time", "OverTime")
travel = multi("Business travel", "BusinessTravel")
inc_lo, inc_hi = int(df_all.MonthlyIncome.min()), int(df_all.MonthlyIncome.max())
inc = st.sidebar.slider("Monthly income", inc_lo, inc_hi, (inc_lo, inc_hi))

mask = (df_all.Department.astype(str).isin(dept) & df_all.JobRole.astype(str).isin(role)
        & df_all.Gender.astype(str).isin(gender) & df_all.AgeGroup.astype(str).isin(age)
        & df_all.SalarySlab.astype(str).isin(slab) & df_all.OverTime.astype(str).isin(ot)
        & df_all.BusinessTravel.astype(str).isin(travel) & df_all.MonthlyIncome.between(*inc))
df = df_all[mask]

st.sidebar.markdown("---")
st.sidebar.caption(f"Showing **{len(df):,}** of {len(df_all):,} employees")
st.sidebar.download_button("⬇️ Download filtered data (CSV)", df.to_csv(index=False).encode(),
                           "hr_filtered.csv", "text/csv")

st.markdown("<div class='hero'><h1>📊 HR Analytics Report</h1>"
            "<p>Workforce profile, attrition drivers, compensation and satisfaction — fully interactive.</p></div>",
            unsafe_allow_html=True)

if df.empty:
    st.warning("No employees match the current filters. Loosen them in the sidebar.")
    st.stop()

tabs = st.tabs(["🏠 Overview", "🚪 Attrition drivers", "👥 Demographics", "💰 Compensation",
                "😊 Satisfaction & work", "🔗 Correlations", "🤖 Risk model", "🧹 Data & cleaning"])

# ───────────────────────── Overview ─────────────────────────
with tabs[0]:
    leavers = int(df.AttritionFlag.sum())
    c = st.columns(5)
    c[0].metric("Employees", f"{len(df):,}")
    c[1].metric("Attrition rate", f"{df.AttritionFlag.mean()*100:.1f}%",
                f"{(df.AttritionFlag.mean()-df_all.AttritionFlag.mean())*100:+.1f} pp vs all")
    c[2].metric("Leavers", f"{leavers:,}")
    c[3].metric("Avg monthly income", f"${df.MonthlyIncome.mean():,.0f}")
    c[4].metric("Avg tenure", f"{df.YearsAtCompany.mean():.1f} yrs")

    a, b = st.columns(2)
    with a:
        g = df.Attrition.value_counts().reset_index()
        g.columns = ["Attrition", "Count"]
        fig = px.pie(g, names="Attrition", values="Count", hole=.6, color="Attrition",
                     color_discrete_map=PAL, title="Attrition split")
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(style(fig), use_container_width=True)
    with b:
        g = df.groupby(["Department", "Attrition"], observed=True).size().reset_index(name="Count")
        fig = px.bar(g, x="Department", y="Count", color="Attrition", barmode="group",
                     color_discrete_map=PAL, title="Headcount by department")
        st.plotly_chart(style(fig), use_container_width=True)

    a, b = st.columns(2)
    with a:
        st.plotly_chart(rate_bar(df, "JobRole", "Attrition rate by job role", "h", 420), use_container_width=True)
    with b:
        st.plotly_chart(rate_bar(df, "OverTime", "Attrition rate: over time vs not"), use_container_width=True)

    top = rate_by(df, "JobRole").query("Employees >= 20").sort_values("AttritionRate").iloc[-1]
    ot_g = rate_by(df, "OverTime").set_index("OverTime")["AttritionRate"]
    msg = f"Highest-risk role (≥20 staff): <b>{top.JobRole}</b> at {top.AttritionRate:.1f}%."
    if {"Yes", "No"} <= set(ot_g.index):
        msg += f" Employees working over time leave at <b>{ot_g['Yes']:.1f}%</b> vs {ot_g['No']:.1f}% for those who don't."
    insight(msg)

# ───────────────────────── Attrition drivers ─────────────────────────
with tabs[1]:
    st.subheader("What is associated with leaving?")
    cats = ["Department", "BusinessTravel", "MaritalStatus", "EducationField", "Gender", "AgeGroup",
            "SalarySlab", "TenureBand", "CommuteBand", "StockOptionLevel", "JobLevel", "NumCompaniesWorked"]
    pick = st.selectbox("Choose a factor", cats, index=0)
    d2 = df.copy()
    d2[pick] = d2[pick].astype(str) if pick in ("StockOptionLevel", "JobLevel", "NumCompaniesWorked") else d2[pick]
    a, b = st.columns(2)
    with a:
        st.plotly_chart(rate_bar(d2, pick), use_container_width=True)
    with b:
        g = d2.groupby([pick, "Attrition"], observed=True).size().reset_index(name="Count")
        fig = px.bar(g, x=pick, y="Count", color="Attrition", barmode="stack",
                     color_discrete_map=PAL, title=f"Headcount by {pick}")
        st.plotly_chart(style(fig), use_container_width=True)

    st.markdown("#### Heatmap: attrition % across two factors")
    h1, h2 = st.columns(2)
    xa = h1.selectbox("Rows", ["JobRole", "Department", "AgeGroup", "SalarySlab", "MaritalStatus"], 0)
    ya = h2.selectbox("Columns", ["OverTime", "BusinessTravel", "Gender", "TenureBand", "CommuteBand"], 0)
    pv = df.pivot_table(index=xa, columns=ya, values="AttritionFlag", aggfunc="mean", observed=True) * 100
    fig = px.imshow(pv.round(1), text_auto=".1f", aspect="auto", color_continuous_scale=SEQ,
                    title=f"Attrition % — {xa} × {ya}")
    st.plotly_chart(style(fig, 440), use_container_width=True)

    st.markdown("#### Numeric profile: leavers vs stayers")
    num = st.selectbox("Metric", ["Age", "MonthlyIncome", "YearsAtCompany", "TotalWorkingYears",
                                  "DistanceFromHome", "YearsSinceLastPromotion", "PercentSalaryHike",
                                  "YearsInCurrentRole", "YearsWithCurrManager"])
    a, b = st.columns(2)
    with a:
        fig = px.box(df, x="Attrition", y=num, color="Attrition", color_discrete_map=PAL, points="outliers",
                     title=f"{num} distribution")
        st.plotly_chart(style(fig), use_container_width=True)
    with b:
        fig = px.histogram(df, x=num, color="Attrition", barmode="overlay", opacity=.65, nbins=30,
                           color_discrete_map=PAL, title=f"{num} histogram")
        st.plotly_chart(style(fig), use_container_width=True)

# ───────────────────────── Demographics ─────────────────────────
with tabs[2]:
    a, b = st.columns(2)
    with a:
        fig = px.histogram(df, x="Age", nbins=25, color="Gender", barmode="overlay", opacity=.7,
                           color_discrete_sequence=[ACCENT, "#F97316"], title="Age distribution by gender")
        st.plotly_chart(style(fig), use_container_width=True)
    with b:
        g = df.groupby(["AgeGroup", "Gender"], observed=True).size().reset_index(name="Count")
        fig = px.bar(g, x="AgeGroup", y="Count", color="Gender", barmode="group",
                     color_discrete_sequence=[ACCENT, "#F97316"], title="Age group × gender",
                     category_orders={"AgeGroup": AGE_ORDER})
        st.plotly_chart(style(fig), use_container_width=True)
    a, b = st.columns(2)
    with a:
        fig = px.sunburst(df.astype({"Department": str, "JobRole": str}), path=["Department", "JobRole"], title="Department → job role",
                          color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(style(fig, 450), use_container_width=True)
    with b:
        g = df.astype({"Education": str, "EducationField": str}).groupby(["Education", "EducationField"]).size().reset_index(name="Count")
        fig = px.treemap(g, path=["EducationField", "Education"], values="Count", title="Education field → level",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(style(fig, 450), use_container_width=True)
    a, b = st.columns(2)
    with a:
        g = df.MaritalStatus.value_counts().reset_index(); g.columns = ["MaritalStatus", "Count"]
        fig = px.pie(g, names="MaritalStatus", values="Count", hole=.5, title="Marital status",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(style(fig), use_container_width=True)
    with b:
        g = df.BusinessTravel.value_counts().reset_index(); g.columns = ["BusinessTravel", "Count"]
        fig = px.bar(g, x="BusinessTravel", y="Count", color="BusinessTravel", title="Business travel",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(showlegend=False)
        st.plotly_chart(style(fig), use_container_width=True)

# ───────────────────────── Compensation ─────────────────────────
with tabs[3]:
    a, b = st.columns(2)
    with a:
        fig = px.box(df, x="JobRole", y="MonthlyIncome", color="Department",
                     title="Monthly income by job role", color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(style(fig, 450), use_container_width=True)
    with b:
        fig = px.scatter(df, x="TotalWorkingYears", y="MonthlyIncome", color="Attrition",
                         color_discrete_map=PAL, opacity=.6, trendline=None, hover_data=["JobRole", "Age"],
                         title="Income vs total experience")
        st.plotly_chart(style(fig, 450), use_container_width=True)
    a, b = st.columns(2)
    with a:
        g = df.groupby(["JobLevel", "Gender"], observed=True)["MonthlyIncome"].mean().reset_index()
        fig = px.bar(g, x="JobLevel", y="MonthlyIncome", color="Gender", barmode="group",
                     color_discrete_sequence=[ACCENT, "#F97316"], title="Avg income by job level & gender")
        st.plotly_chart(style(fig), use_container_width=True)
    with b:
        st.plotly_chart(rate_bar(df, "SalarySlab", "Attrition rate by salary slab"), use_container_width=True)
    a, b = st.columns(2)
    with a:
        g = df.groupby("PercentSalaryHike", observed=True)["AttritionFlag"].mean().mul(100).reset_index()
        fig = px.line(g, x="PercentSalaryHike", y="AttritionFlag", markers=True,
                      title="Attrition % by salary hike %", labels={"AttritionFlag": "Attrition %"})
        fig.update_traces(line_color=ACCENT)
        st.plotly_chart(style(fig), use_container_width=True)
    with b:
        g = df.groupby("StockOptionLevel", observed=True).agg(Attr=("AttritionFlag", "mean"),
                                                              Inc=("MonthlyIncome", "mean")).reset_index()
        g["Attr"] *= 100
        fig = go.Figure()
        fig.add_bar(x=g.StockOptionLevel, y=g.Inc, name="Avg income", marker_color="#C7D2FE")
        fig.add_scatter(x=g.StockOptionLevel, y=g.Attr, name="Attrition %", yaxis="y2",
                        mode="lines+markers", line=dict(color="#F97316"))
        fig.update_layout(title="Stock option level: income vs attrition",
                          yaxis2=dict(overlaying="y", side="right", title="Attrition %"),
                          xaxis_title="Stock option level", yaxis_title="Avg income")
        st.plotly_chart(style(fig), use_container_width=True)
    gm = df.groupby("Gender")["MonthlyIncome"].mean()
    if {"Male", "Female"} <= set(gm.index):
        insight(f"Average monthly income — Male: <b>${gm['Male']:,.0f}</b>, Female: <b>${gm['Female']:,.0f}</b> "
                f"(gap {((gm['Male']/gm['Female'])-1)*100:+.1f}%, not adjusted for role or level).")

# ───────────────────────── Satisfaction ─────────────────────────
with tabs[4]:
    sat = ["JobSatisfaction", "EnvironmentSatisfaction", "RelationshipSatisfaction",
           "WorkLifeBalance", "JobInvolvement"]
    col = st.selectbox("Survey measure", sat)
    a, b = st.columns(2)
    with a:
        st.plotly_chart(rate_bar(df, col, f"Attrition % by {col}"), use_container_width=True)
    with b:
        g = df.groupby([col, "Attrition"], observed=True).size().reset_index(name="Count")
        fig = px.bar(g, x=col, y="Count", color="Attrition", barmode="stack", color_discrete_map=PAL,
                     category_orders={col: ORDERS[col]}, title=f"Responses: {col}")
        st.plotly_chart(style(fig), use_container_width=True)

    st.markdown("#### Average satisfaction score by department")
    num_cols = [c + "_Num" for c in sat]
    g = df.groupby("Department", observed=True)[num_cols].mean()
    g.columns = sat
    fig = px.imshow(g.round(2), text_auto=".2f", aspect="auto", color_continuous_scale=SEQ,
                    title="Mean score (1 = low, 4 = high)")
    st.plotly_chart(style(fig, 300), use_container_width=True)

    a, b = st.columns(2)
    with a:
        g = df.groupby("JobRole", observed=True)[num_cols].mean()
        cats = ["Job sat.", "Env. sat.", "Relationship", "Work-life", "Involvement"]
        r = st.selectbox("Radar: job role", sorted(g.index))
        fig = go.Figure()
        fig.add_scatterpolar(r=g.loc[r].tolist() + [g.loc[r].iloc[0]], theta=cats + [cats[0]], fill="toself",
                             name=r, line_color=ACCENT)
        fig.add_scatterpolar(r=df[num_cols].mean().tolist() + [df[num_cols].mean().iloc[0]],
                             theta=cats + [cats[0]], name="All employees", line=dict(color="#F97316", dash="dot"))
        fig.update_layout(polar=dict(radialaxis=dict(range=[1, 4])), title="Role vs company average")
        st.plotly_chart(style(fig, 400), use_container_width=True)
    with b:
        g = df.groupby(["OverTime", "WorkLifeBalance"], observed=True).size().reset_index(name="Count")
        fig = px.bar(g, x="WorkLifeBalance", y="Count", color="OverTime", barmode="group",
                     category_orders={"WorkLifeBalance": ORDERS["WorkLifeBalance"]},
                     color_discrete_sequence=[ACCENT, "#F97316"], title="Work-life balance vs over time")
        st.plotly_chart(style(fig, 400), use_container_width=True)

    a, b = st.columns(2)
    with a:
        g = df.groupby("YearsSinceLastPromotion")["AttritionFlag"].mean().mul(100).reset_index()
        fig = px.area(g, x="YearsSinceLastPromotion", y="AttritionFlag",
                      title="Attrition % by years since last promotion", labels={"AttritionFlag": "Attrition %"})
        fig.update_traces(line_color=ACCENT)
        st.plotly_chart(style(fig), use_container_width=True)
    with b:
        g = df.groupby("TrainingTimesLastYear")["AttritionFlag"].mean().mul(100).reset_index()
        fig = px.bar(g, x="TrainingTimesLastYear", y="AttritionFlag", title="Attrition % by trainings last year",
                     labels={"AttritionFlag": "Attrition %"}, color_discrete_sequence=[ACCENT])
        st.plotly_chart(style(fig), use_container_width=True)

# ───────────────────────── Correlations ─────────────────────────
with tabs[5]:
    numeric = ["Age", "DailyRate", "DistanceFromHome", "HourlyRate", "JobLevel", "MonthlyIncome", "MonthlyRate",
               "NumCompaniesWorked", "PercentSalaryHike", "StockOptionLevel", "TotalWorkingYears",
               "TrainingTimesLastYear", "YearsAtCompany", "YearsInCurrentRole", "YearsSinceLastPromotion",
               "YearsWithCurrManager"] + [c + "_Num" for c in ["Education", "EnvironmentSatisfaction",
               "JobSatisfaction", "RelationshipSatisfaction", "JobInvolvement", "WorkLifeBalance",
               "PerformanceRating"]] + ["AttritionFlag"]
    method = st.radio("Method", ["pearson", "spearman"], horizontal=True)
    corr = df[numeric].corr(method=method)
    corr.columns = corr.index = [c.replace("_Num", "") for c in corr.columns]
    fig = px.imshow(corr.round(2), color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto",
                    title=f"{method.title()} correlation matrix")
    st.plotly_chart(style(fig, 700), use_container_width=True)

    s = corr["AttritionFlag"].drop("AttritionFlag").sort_values()
    s = pd.concat([s.head(6), s.tail(6)])
    sd = s.rename_axis("Feature").reset_index(name="r")
    fig = px.bar(sd, x="r", y="Feature", orientation="h", color="r", color_continuous_scale="RdBu_r",
                 title="Strongest correlations with attrition")
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(style(fig, 400), use_container_width=True)
    insight("Correlation ≠ causation. Negative values mean higher values go with <i>lower</i> attrition "
            "(e.g. more experience, higher income).")

    st.markdown("#### Scatter explorer")
    s1, s2, s3 = st.columns(3)
    x = s1.selectbox("X", numeric[:16], 0); y = s2.selectbox("Y", numeric[:16], 5)
    cc = s3.selectbox("Colour", ["Attrition", "Department", "Gender", "OverTime"])
    fig = px.scatter(df, x=x, y=y, color=cc, opacity=.6, hover_data=["EmpID", "JobRole"],
                     color_discrete_map=PAL if cc == "Attrition" else None)
    st.plotly_chart(style(fig, 450), use_container_width=True)

# ───────────────────────── Risk model ─────────────────────────
with tabs[6]:
    st.subheader("Attrition risk model (logistic regression)")
    st.caption("Explanatory model on the full cleaned dataset (not filtered) — shows which factors move risk most.")
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler

        @st.cache_resource(show_spinner="Training model…")
        def train():
            nums = ["Age", "DistanceFromHome", "MonthlyIncome", "NumCompaniesWorked", "PercentSalaryHike",
                    "StockOptionLevel", "TotalWorkingYears", "TrainingTimesLastYear", "YearsAtCompany",
                    "YearsInCurrentRole", "YearsSinceLastPromotion", "YearsWithCurrManager", "JobLevel",
                    "EnvironmentSatisfaction_Num", "JobSatisfaction_Num", "WorkLifeBalance_Num",
                    "JobInvolvement_Num", "RelationshipSatisfaction_Num"]
            cats = ["OverTime", "BusinessTravel", "MaritalStatus", "Department", "Gender", "JobRole"]
            X = df_all[nums + cats].copy()
            for c in cats:
                X[c] = X[c].astype(str)
            y = df_all["AttritionFlag"]
            Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.25, stratify=y, random_state=42)
            pre = ColumnTransformer([("n", StandardScaler(), nums),
                                     ("c", OneHotEncoder(handle_unknown="ignore"), cats)])
            pipe = Pipeline([("p", pre), ("m", LogisticRegression(max_iter=2000, class_weight="balanced"))])
            pipe.fit(Xtr, ytr)
            proba = pipe.predict_proba(Xte)[:, 1]
            names = pipe.named_steps["p"].get_feature_names_out()
            coef = pd.Series(pipe.named_steps["m"].coef_[0], index=[n.split("__")[1] for n in names])
            return pipe, nums, cats, roc_auc_score(yte, proba), confusion_matrix(yte, proba > .5), coef

        pipe, nums, cats, auc, cm, coef = train()
        m1, m2 = st.columns(2)
        m1.metric("ROC-AUC (hold-out 25%)", f"{auc:.3f}")
        m2.metric("Recall of leavers @0.5", f"{cm[1,1]/cm[1].sum()*100:.0f}%")

        a, b = st.columns(2)
        with a:
            top = pd.concat([coef.sort_values().head(8), coef.sort_values().tail(8)])
            td = top.rename_axis("Feature").reset_index(name="Effect")
            fig = px.bar(td, x="Effect", y="Feature", orientation="h", color="Effect",
                         color_continuous_scale="RdBu_r", title="Top drivers (standardised coefficients)")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(style(fig, 480), use_container_width=True)
        with b:
            fig = px.imshow(cm, text_auto=True, x=["Pred Stay", "Pred Leave"], y=["Actual Stay", "Actual Leave"],
                            color_continuous_scale=SEQ, title="Confusion matrix (hold-out)")
            st.plotly_chart(style(fig, 480), use_container_width=True)

        st.markdown("#### 🎯 Score an employee")
        r1 = st.columns(4)
        inp = {}
        inp["Age"] = r1[0].slider("Age", 18, 60, 32)
        inp["MonthlyIncome"] = r1[1].slider("Monthly income", 1000, 20000, 5000, 100)
        inp["YearsAtCompany"] = r1[2].slider("Years at company", 0, 40, 4)
        inp["DistanceFromHome"] = r1[3].slider("Distance (km)", 1, 29, 8)
        r2 = st.columns(4)
        inp["OverTime"] = r2[0].selectbox("Over time", ["No", "Yes"])
        inp["BusinessTravel"] = r2[1].selectbox("Travel", sorted(df_all.BusinessTravel.astype(str).unique()))
        inp["MaritalStatus"] = r2[2].selectbox("Marital", sorted(df_all.MaritalStatus.astype(str).unique()))
        inp["JobRole"] = r2[3].selectbox("Role", sorted(df_all.JobRole.astype(str).unique()))
        r3 = st.columns(3)
        inp["JobSatisfaction_Num"] = r3[0].slider("Job satisfaction", 1, 4, 3)
        inp["WorkLifeBalance_Num"] = r3[1].slider("Work-life balance", 1, 4, 3)
        inp["EnvironmentSatisfaction_Num"] = r3[2].slider("Environment satisfaction", 1, 4, 3)
        # fill the rest with dataset medians / modes
        row = {c: df_all[c].median() for c in nums}
        row.update({c: df_all[c].astype(str).mode()[0] for c in cats})
        row.update(inp)
        if "YearsAtCompany" in inp:
            row["YearsInCurrentRole"] = min(df_all.YearsInCurrentRole.median(), inp["YearsAtCompany"])
            row["YearsWithCurrManager"] = min(df_all.YearsWithCurrManager.median(), inp["YearsAtCompany"])
            row["TotalWorkingYears"] = max(df_all.TotalWorkingYears.median(), inp["YearsAtCompany"])
        p = float(pipe.predict_proba(pd.DataFrame([row])[nums + cats])[0, 1])
        gauge = go.Figure(go.Indicator(mode="gauge+number", value=p * 100, number={"suffix": "%"},
                          title={"text": "Estimated attrition risk"},
                          gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#F97316"},
                                 "steps": [{"range": [0, 33], "color": "#E0E7FF"},
                                           {"range": [33, 66], "color": "#C7D2FE"},
                                           {"range": [66, 100], "color": "#A5B4FC"}]}))
        st.plotly_chart(style(gauge, 300), use_container_width=True)
        st.caption("Class-balanced model, so probabilities run higher than the 16% base rate. Use for ranking, not as an absolute forecast.")
    except ImportError:
        st.info("Install scikit-learn (`pip install scikit-learn`) to enable the risk model.")

# ───────────────────────── Data & cleaning ─────────────────────────
with tabs[7]:
    st.subheader("Cleaning steps applied")
    st.table(pd.DataFrame(clean_log, columns=["Step", "What was done"]))
    a, b, c = st.columns(3)
    a.metric("Raw rows", f"{len(raw):,}")
    b.metric("Clean rows", f"{len(df_all):,}")
    c.metric("Columns (raw → clean)", f"{raw.shape[1]} → {df_all.shape[1]}")
    st.subheader("Data preview")
    st.dataframe(df, use_container_width=True, height=380)
    st.subheader("Summary statistics")
    st.dataframe(df.describe().T.round(2), use_container_width=True)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df_all.to_excel(xw, sheet_name="Clean_Data", index=False)
        pd.DataFrame(clean_log, columns=["Step", "Detail"]).to_excel(xw, sheet_name="Cleaning_Log", index=False)
    st.download_button("⬇️ Download full cleaned data (Excel)", buf.getvalue(), "HR_Analytics_clean.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
