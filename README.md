# HR Analytics – Streamlit Report

Interactive dashboard on `data/HR_Analytics.xlsx` (sheet `HR_Analytics`).

## Run
```bash
python -m venv venv
venv\Scripts\activate        # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
Or double-click `run.bat` (Windows) / run `./run.sh` (Mac/Linux).

## Files
- `app.py` – the Streamlit report (8 tabs, sidebar filters, CSV/Excel export)
- `data_cleaning.py` – cleaning pipeline (also usable standalone)
- `data/HR_Analytics.xlsx` – source data
- `requirements.txt`, `.streamlit/config.toml`

## Cleaning applied
7 duplicate rows removed · `TravelRarely` → `Travel_Rarely` · 57 missing `YearsWithCurrManager` filled with median ·
constant columns dropped (`EmployeeCount`, `StandardHours`, `Over18`) · survey scores mapped to labels ·
features added (`AttritionFlag`, `TenureBand`, `CommuteBand`).
"# hr_analytics" 
