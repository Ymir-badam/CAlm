import csv
import json
from pathlib import Path


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

CA_COLORS = [
    {"bg": "rgba(24,95,165,0.85)",  "border": "#185FA5"},   # blue
    {"bg": "rgba(15,110,86,0.82)",  "border": "#0F6E56"},   # teal
    {"bg": "rgba(186,117,23,0.80)", "border": "#BA7517"},   # amber
    {"bg": "rgba(162,45,45,0.80)",  "border": "#A32D2D"},   # red
    {"bg": "rgba(136,135,128,0.75)","border": "#888780"},   # gray
]

TIME_KEYWORDS = {"month","quarter","year","date","period","week","fy","q1","q2","q3","q4","jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"}
VARIANCE_KEYWORDS = {"variance","movement","change","delta","diff","actual","budget","forecast"}


def clean_numeric(val: str) -> float:
    cleaned = str(val).replace(",", "").replace("£", "").replace("$", "").replace("€", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def detect_column_types(rows: list[dict], headers: list[str]) -> dict:
    types = {}
    for h in headers:
        numeric_count = sum(
            1 for row in rows
            if clean_numeric(row.get(h, "")) is not None
        )
        types[h] = "numeric" if numeric_count >= len(rows) * 0.7 else "text"
    return types


def suggest_chart_type(headers, col_types, rows) -> str:
    numeric_cols = [h for h, t in col_types.items() if t == "numeric"]
    text_cols    = [h for h, t in col_types.items() if t == "text"]

    first_col = headers[0].lower() if headers else ""
    is_time   = any(kw in first_col for kw in TIME_KEYWORDS)
    has_var   = any(any(kw in h.lower() for kw in VARIANCE_KEYWORDS) for h in headers)

    if has_var and len(numeric_cols) >= 2:
        return "variance"
    if is_time and numeric_cols:
        return "line"
    if text_cols and len(rows) > 8 and numeric_cols:
        return "horizontal_bar"
    if text_cols and len(numeric_cols) == 1 and len(rows) <= 7:
        return "doughnut"
    return "bar"


def build_summary(rows, value_cols) -> dict:
    summary = {}
    for col in value_cols:
        vals = [v for v in (clean_numeric(r.get(col, "")) for r in rows) if v is not None]
        if not vals:
            continue
        total = sum(vals)
        summary[col] = {
            "total":   round(total, 2),
            "average": round(total / len(vals), 2),
            "max":     round(max(vals), 2),
            "min":     round(min(vals), 2),
            "count":   len(vals),
        }
    return summary


# ─────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────

def generate_chart_config(file_path: str) -> dict:
    """
    Read a CSV and return a Chart.js-compatible config dict
    optimised for chartered accountants.

    Returns:
        {
            "chart_type"  : str,
            "config"      : dict,       # pass to new Chart(ctx, config)
            "label_col"   : str,
            "value_cols"  : list[str],
            "summary"     : dict,       # totals / averages for KPI cards
            "raw_labels"  : list[str],  # x-axis labels
            "raw_datasets": list[dict], # {col, data: [float]}
        }
    """
    file_path = str(file_path)

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader  = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows    = list(reader)

    if not rows or not headers:
        raise ValueError("CSV is empty or has no headers.")

    col_types    = detect_column_types(rows, headers)
    chart_type   = suggest_chart_type(headers, col_types, rows)
    numeric_cols = [h for h, t in col_types.items() if t == "numeric"]
    text_cols    = [h for h, t in col_types.items() if t == "text"]

    label_col  = text_cols[0] if text_cols else headers[0]
    value_cols = [c for c in numeric_cols if c != label_col][:4]

    if not value_cols:
        raise ValueError("No numeric columns found in CSV.")

    labels = [row[label_col] for row in rows]

    # ── Build datasets ───────────────────────────────────────────────
    datasets     = []
    raw_datasets = []

    if chart_type == "variance":
        # Two-series: actual vs budget → show variance bars
        actual_col = value_cols[0]
        budget_col = value_cols[1] if len(value_cols) > 1 else value_cols[0]
        actuals  = [clean_numeric(r.get(actual_col, 0)) or 0 for r in rows]
        budgets  = [clean_numeric(r.get(budget_col, 0)) or 0 for r in rows]
        variances = [round(a - b, 2) for a, b in zip(actuals, budgets)]
        colors   = ["rgba(15,110,86,0.85)" if v >= 0 else "rgba(162,45,45,0.80)" for v in variances]
        datasets = [{
            "label": "Variance (Actual vs Budget)",
            "data":  variances,
            "backgroundColor": colors,
            "borderColor": colors,
            "borderWidth": 1,
            "borderRadius": 3,
        }]
        raw_datasets = [
            {"col": actual_col, "data": actuals},
            {"col": budget_col, "data": budgets},
            {"col": "Variance", "data": variances},
        ]
        chart_type = "bar"

    else:
        for i, col in enumerate(value_cols):
            data = [round(clean_numeric(r.get(col, 0)) or 0, 2) for r in rows]
            c    = CA_COLORS[i % len(CA_COLORS)]
            ds   = {
                "label": col,
                "data":  data,
                "backgroundColor": c["bg"],
                "borderColor": c["border"],
                "borderWidth": 1.5,
                "borderRadius": 3,
            }
            if chart_type == "line":
                ds.update({"fill": False, "tension": 0.35, "pointRadius": 3, "pointHoverRadius": 5})
            datasets.append(ds)
            raw_datasets.append({"col": col, "data": data})

    # ── Scales ───────────────────────────────────────────────────────
    x_scale = {
        "grid": {"display": False},
        "ticks": {"font": {"size": 11}, "autoSkip": False, "maxRotation": 40 if len(labels) > 8 else 0},
    }
    y_scale = {
        "beginAtZero": True,
        "grid": {"color": "rgba(128,128,128,0.08)", "lineWidth": 0.5},
        "ticks": {"font": {"size": 11}, "callback": "__CURRENCY_FORMATTER__"},
    }

    is_horiz = chart_type == "horizontal_bar"
    scales   = {"x": y_scale, "y": x_scale} if is_horiz else {"x": x_scale, "y": y_scale}

    # ── Full config ──────────────────────────────────────────────────
    config = {
        "type": "bar" if is_horiz else chart_type,
        "data": {"labels": labels, "datasets": datasets},
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "indexAxis": "y" if is_horiz else "x",
            "plugins": {
                "legend": {"display": len(value_cols) > 1 and chart_type not in ("doughnut",)},
                "tooltip": {"callbacks": {"label": "__TOOLTIP_FORMATTER__"}},
            },
            "scales": scales,
        },
    }

    if chart_type == "doughnut":
        config["options"]["cutout"] = "65%"
        del config["options"]["scales"]

    return {
        "chart_type":   chart_type,
        "config":       config,
        "label_col":    label_col,
        "value_cols":   value_cols,
        "summary":      build_summary(rows, value_cols),
        "raw_labels":   labels,
        "raw_datasets": raw_datasets,
    }


# ─────────────────────────────────────────────
# Waterfall helper  (P&L bridge)
# ─────────────────────────────────────────────

def generate_waterfall_config(items: list[tuple[str, float]]) -> dict:
    """
    items = [("Revenue", 1840), ("Cost of sales", -948), ...]
    Subtotal/total rows (label contains 'profit', 'total', 'ebitda')
    are rendered in blue; positive flows teal, negative red.
    """
    SUBTOTAL_KEYWORDS = {"profit","total","ebitda","net","gross","subtotal","balance"}

    labels = [i[0] for i in items]
    values = [i[1] for i in items]

    colors = []
    for label, val in items:
        lower = label.lower()
        if any(kw in lower for kw in SUBTOTAL_KEYWORDS):
            colors.append("rgba(24,95,165,0.88)")
        elif val >= 0:
            colors.append("rgba(15,110,86,0.85)")
        else:
            colors.append("rgba(162,45,45,0.82)")

    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "£k",
                "data":  values,
                "backgroundColor": colors,
                "borderColor":     colors,
                "borderWidth": 0,
                "borderRadius": 3,
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": False},
                "tooltip": {"callbacks": {"label": "__WATERFALL_FORMATTER__"}},
            },
            "scales": {
                "x": {
                    "grid": {"display": False},
                    "ticks": {"font": {"size": 10}, "autoSkip": False, "maxRotation": 30},
                },
                "y": {
                    "grid": {"color": "rgba(128,128,128,0.08)", "lineWidth": 0.5},
                    "ticks": {"font": {"size": 11}, "callback": "__CURRENCY_FORMATTER__"},
                },
            },
        },
    }


# ─────────────────────────────────────────────
# Variance-only helper
# ─────────────────────────────────────────────

def generate_variance_config(labels: list[str], actuals: list[float], budgets: list[float]) -> dict:
    variances = [round(a - b, 2) for a, b in zip(actuals, budgets)]
    colors    = ["rgba(15,110,86,0.85)" if v >= 0 else "rgba(162,45,45,0.80)" for v in variances]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Variance",
                "data":  variances,
                "backgroundColor": colors,
                "borderColor":     colors,
                "borderWidth": 1,
                "borderRadius": 3,
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": False},
                "tooltip": {"callbacks": {"label": "__VARIANCE_FORMATTER__"}},
            },
            "scales": {
                "x": {"grid": {"display": False}, "ticks": {"font": {"size": 11}, "autoSkip": False, "maxRotation": 40}},
                "y": {"grid": {"color": "rgba(128,128,128,0.08)", "lineWidth": 0.5},
                      "ticks": {"font": {"size": 11}, "callback": "__CURRENCY_FORMATTER__"}},
            },
        },
        "meta": {
            "favourable": sum(1 for v in variances if v >= 0),
            "adverse":    sum(1 for v in variances if v < 0),
            "net":        round(sum(variances), 2),
        },
    }