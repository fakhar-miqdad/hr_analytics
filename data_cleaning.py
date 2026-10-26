"""Data loading + cleaning pipeline for the HR Analytics dataset."""
from pathlib import Path
import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).parent / "data" / "HR_Analytics.xlsx"
SHEET = "HR_Analytics"

# Numeric 1-4/1-5 survey codes -> readable labels
LABELS = {
    "Education": {1: "Below College", 2: "College", 3: "Bachelor", 4: "Master", 5: "Doctor"},
    "EnvironmentSatisfaction": {1: "Low", 2: "Medium", 3: "High", 4: "Very High"},
    "JobSatisfaction": {1: "Low", 2: "Medium", 3: "High", 4: "Very High"},
    "RelationshipSatisfaction": {1: "Low", 2: "Medium", 3: "High", 4: "Very High"},
    "JobInvolvement": {1: "Low", 2: "Medium", 3: "High", 4: "Very High"},
    "WorkLifeBalance": {1: "Bad", 2: "Good", 3: "Better", 4: "Best"},
    "PerformanceRating": {1: "Low", 2: "Good", 3: "Excellent", 4: "Outstanding"},
}
ORDERS = {k: list(v.values()) for k, v in LABELS.items()}
AGE_ORDER = ["18-25", "26-35", "36-45", "46-55", "55+"]
SLAB_ORDER = ["Upto 5k", "5k-10k", "10k-15k", "15k+"]
DROP_CONSTANT = ["EmployeeCount", "StandardHours", "Over18"]


def clean(df: pd.DataFrame):
    """Return (clean_df, log). `log` is a list of (step, detail) tuples."""
    log = []
    df = df.copy()
    n0 = len(df)

    # 1. strip whitespace in text columns
    for c in df.select_dtypes(exclude="number").columns:
        df[c] = df[c].astype("string").str.strip()
    log.append(("Whitespace", "Trimmed leading/trailing spaces in text columns"))

    # 2. exact duplicate rows
    dups = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)
    log.append(("Duplicate rows", f"Removed {dups} exact duplicate rows ({n0} -> {len(df)})"))

    # 3. inconsistent category spelling
    fixed = int((df["BusinessTravel"] == "TravelRarely").sum())
    df["BusinessTravel"] = df["BusinessTravel"].replace({"TravelRarely": "Travel_Rarely"})
    log.append(("Category typo", f"Standardised 'TravelRarely' -> 'Travel_Rarely' ({fixed} rows)"))

    # 4. missing YearsWithCurrManager
    miss = int(df["YearsWithCurrManager"].isna().sum())
    med = df["YearsWithCurrManager"].median()
    df["YearsWithCurrManager"] = df["YearsWithCurrManager"].fillna(med).round().astype(int)
    log.append(("Missing values", f"Filled {miss} missing YearsWithCurrManager with the median ({med:g})"))

    # 5. constant / useless columns
    present = [c for c in DROP_CONSTANT if c in df.columns]
    df = df.drop(columns=present)
    log.append(("Constant columns", f"Dropped zero-variance columns: {', '.join(present)}"))

    # 6. remaining duplicated EmpID (same id, different data) - flag only
    dup_ids = int(df["EmpID"].duplicated().sum())
    log.append(("Duplicate EmpID", f"{dup_ids} EmpID values still repeat with different data; kept (flagged only)"))

    # 7. engineered features
    df["AttritionFlag"] = (df["Attrition"] == "Yes").astype(int)
    df["AgeGroup"] = pd.Categorical(df["AgeGroup"], AGE_ORDER, ordered=True)
    df["SalarySlab"] = pd.Categorical(df["SalarySlab"], SLAB_ORDER, ordered=True)
    df["TenureBand"] = pd.cut(df["YearsAtCompany"], [-1, 1, 3, 5, 10, 100],
                              labels=["0-1 yr", "2-3 yrs", "4-5 yrs", "6-10 yrs", "10+ yrs"])
    df["CommuteBand"] = pd.cut(df["DistanceFromHome"], [0, 5, 10, 20, 100],
                               labels=["1-5 km", "6-10 km", "11-20 km", "20+ km"])
    df["PromotionGap"] = df["YearsSinceLastPromotion"].clip(upper=15)
    log.append(("Feature engineering", "Added AttritionFlag, TenureBand, CommuteBand"))

    # 8. readable labels (keep numeric originals as *_Num)
    for col, mp in LABELS.items():
        df[col + "_Num"] = df[col]
        df[col] = pd.Categorical(df[col].map(mp), ORDERS[col], ordered=True)
    log.append(("Labels", "Mapped survey scores (1-4/1-5) to readable labels; numeric kept as *_Num"))

    # 9. dtypes
    for c in ["Attrition", "BusinessTravel", "Department", "EducationField", "Gender",
              "JobRole", "MaritalStatus", "OverTime"]:
        df[c] = df[c].astype("category")
    return df, log


def load_clean(path=DATA_PATH):
    raw = pd.read_excel(path, sheet_name=SHEET)
    return raw, *clean(raw)
