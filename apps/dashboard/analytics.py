"""
Pandas-based analytics module for the Finance Dashboard.

Design rationale:
- Django ORM handles base aggregations (SUM, COUNT, GROUP BY) at the DB level.
- Pandas takes over for derived metrics that SQL/ORM handles poorly:
    * Month-over-month % change  (df.pct_change)
    * Rolling averages           (df.rolling(3).mean)
    * Cost center % composition  (group / total * 100)
    * Runway estimation          (balance / avg_monthly_burn)
    * Pivot tables               (df.pivot_table)

Every public function in this module accepts a list/queryset of dicts
and returns a plain Python list/dict — suitable for JSON serialisation.
"""
import pandas as pd
from decimal import Decimal


# ---------------------------------------------------------------------------
# Cost-centre grouping — maps individual categories → executive groups
# ---------------------------------------------------------------------------

COST_CENTER_MAP = {
    'People':      ['SALARIES', 'CONTRACTOR_FEES', 'EMPLOYEE_BENEFITS', 'RECRUITMENT'],
    'Technology':  ['SOFTWARE_TOOLS', 'AI_TOOLS', 'CLOUD_INFRASTRUCTURE', 'EQUIPMENT_HARDWARE'],
    'Operations':  ['OFFICE_RENT', 'UTILITIES_INTERNET'],
    'Growth':      ['ADVERTISING_MARKETING'],
    'Culture':     ['FOOD_BEVERAGES', 'TRAVEL_TRANSPORT'],
    'Compliance':  ['LEGAL_COMPLIANCE'],
    'Other':       ['OTHER_EXPENSE'],
}

# Reverse map: category → cost centre
CATEGORY_TO_COST_CENTER = {
    cat: center
    for center, cats in COST_CENTER_MAP.items()
    for cat in cats
}


def _to_decimal(value):
    """Safely convert any numeric type to Decimal for consistent output."""
    if value is None:
        return Decimal('0.00')
    return Decimal(str(value)).quantize(Decimal('0.01'))


# ---------------------------------------------------------------------------
# 1. Cost-centre breakdown (expense side)
# ---------------------------------------------------------------------------

def compute_cost_center_breakdown(category_rows: list) -> list:
    """
    Roll up granular expense categories into executive cost centres.

    Input: list of dicts — each {category, record_type, total, count}
           (raw output from Django ORM annotate query)
    Output: list of dicts — each {cost_center, total, count, pct_of_total_expense}

    Example output row:
        {"cost_center": "People", "total": "120000.00",
         "count": 48, "pct_of_total_expense": 54.32}
    """
    expense_rows = [r for r in category_rows if r.get('record_type') == 'EXPENSE']
    if not expense_rows:
        return []

    df = pd.DataFrame(expense_rows)
    df['total'] = df['total'].apply(float)

    # Map each category to its cost centre
    df['cost_center'] = df['category'].map(CATEGORY_TO_COST_CENTER).fillna('Other')

    # Aggregate by cost centre
    grouped = df.groupby('cost_center').agg(
        total=('total', 'sum'),
        count=('count', 'sum'),
    ).reset_index()

    total_expense = grouped['total'].sum()
    grouped['pct_of_total_expense'] = (
        (grouped['total'] / total_expense * 100).round(2)
        if total_expense > 0 else 0
    )

    # Sort by total descending (biggest cost centre first)
    grouped = grouped.sort_values('total', ascending=False)

    return [
        {
            'cost_center': row['cost_center'],
            'total': _to_decimal(row['total']),
            'count': int(row['count']),
            'pct_of_total_expense': float(row['pct_of_total_expense']),
        }
        for _, row in grouped.iterrows()
    ]


# ---------------------------------------------------------------------------
# 2. Revenue breakdown (income side)
# ---------------------------------------------------------------------------

def compute_revenue_breakdown(category_rows: list) -> list:
    """
    Break down income records by category with percentage of total revenue.

    Output: list of {category, total, count, pct_of_total_income}
    """
    income_rows = [r for r in category_rows if r.get('record_type') == 'INCOME']
    if not income_rows:
        return []

    df = pd.DataFrame(income_rows)
    df['total'] = df['total'].apply(float)

    total_income = df['total'].sum()
    df['pct_of_total_income'] = (
        (df['total'] / total_income * 100).round(2)
        if total_income > 0 else 0
    )
    df = df.sort_values('total', ascending=False)

    return [
        {
            'category': row['category'],
            'total': _to_decimal(row['total']),
            'count': int(row['count']),
            'pct_of_total_income': float(row['pct_of_total_income']),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# 3. Burn rate — rolling 3-month average monthly expenses
# ---------------------------------------------------------------------------

def compute_burn_rate(monthly_rows: list) -> dict:
    """
    Compute the rolling 3-month average monthly burn (expenses).

    Input: list of {month, month_label, record_type, total, count}
           (raw output from get_monthly_trends)
    Output: {
        "current_month_expense": "150000.00",
        "rolling_3m_avg_burn":   "140000.00",
        "months_analysed":       6,
        "trend": [{"month_label": "2025-01", "expense": "..."},  ...]
    }
    """
    expense_rows = [r for r in monthly_rows if r.get('record_type') == 'EXPENSE']
    if not expense_rows:
        return {
            'current_month_expense': Decimal('0.00'),
            'rolling_3m_avg_burn': Decimal('0.00'),
            'months_analysed': 0,
            'trend': [],
        }

    df = pd.DataFrame(expense_rows)
    df['total'] = df['total'].apply(float)
    df = df.sort_values('month')

    # Rolling 3-month average
    df['rolling_3m_avg'] = df['total'].rolling(window=3, min_periods=1).mean().round(2)

    trend = [
        {
            'month_label': row['month_label'],
            'expense': _to_decimal(row['total']),
            'rolling_3m_avg': _to_decimal(row['rolling_3m_avg']),
        }
        for _, row in df.iterrows()
    ]

    current = df.iloc[-1]
    return {
        'current_month_expense': _to_decimal(current['total']),
        'rolling_3m_avg_burn': _to_decimal(current['rolling_3m_avg']),
        'months_analysed': len(df),
        'trend': trend,
    }


# ---------------------------------------------------------------------------
# 4. Runway estimate
# ---------------------------------------------------------------------------

def compute_runway(summary: dict, monthly_rows: list) -> dict:
    """
    Estimate months of runway remaining.

    Formula: net_balance / rolling_3m_avg_burn

    Output: {
        "net_balance":           "500000.00",
        "avg_monthly_burn":      "140000.00",
        "estimated_runway_months": 3.57,
        "runway_status":         "healthy" | "warning" | "critical"
    }
    """
    burn = compute_burn_rate(monthly_rows)
    avg_burn = float(burn['rolling_3m_avg_burn'])
    net_balance = float(summary.get('net_balance', 0))

    if avg_burn <= 0:
        return {
            'net_balance': _to_decimal(net_balance),
            'avg_monthly_burn': Decimal('0.00'),
            'estimated_runway_months': None,
            'runway_status': 'unknown',
            'note': 'Cannot estimate runway — no expense data yet.',
        }

    runway_months = round(net_balance / avg_burn, 2) if net_balance > 0 else 0.0

    if runway_months >= 12:
        status = 'healthy'
    elif runway_months >= 6:
        status = 'warning'
    else:
        status = 'critical'

    return {
        'net_balance': _to_decimal(net_balance),
        'avg_monthly_burn': _to_decimal(avg_burn),
        'estimated_runway_months': runway_months,
        'runway_status': status,
    }


# ---------------------------------------------------------------------------
# 5. Month-over-month % change per cost centre
# ---------------------------------------------------------------------------

def compute_mom_change(monthly_rows: list) -> list:
    """
    Compute month-over-month % change in spending per cost centre.

    Output: list of {
        "month_label": "2025-03",
        "cost_center": "People",
        "total":       "120000.00",
        "mom_change_pct": 5.26    # positive = more spend vs prev month
    }
    """
    expense_rows = [r for r in monthly_rows if r.get('record_type') == 'EXPENSE']
    if not expense_rows:
        return []

    df = pd.DataFrame(expense_rows)
    df['total'] = df['total'].apply(float)

    # Map categories to cost centres
    df['cost_center'] = df['category'].map(CATEGORY_TO_COST_CENTER).fillna('Other') \
        if 'category' in df.columns else 'Other'

    # If we only have month + record_type (aggregated), group by month
    if 'cost_center' not in df.columns or df['cost_center'].nunique() <= 1:
        df['cost_center'] = 'Total'

    grouped = df.groupby(['month_label', 'cost_center'])['total'].sum().reset_index()
    grouped = grouped.sort_values(['cost_center', 'month_label'])

    # pct_change per cost centre group
    grouped['mom_change_pct'] = (
        grouped.groupby('cost_center')['total']
        .pct_change()
        .mul(100)
        .round(2)
    )

    return [
        {
            'month_label': row['month_label'],
            'cost_center': row['cost_center'],
            'total': _to_decimal(row['total']),
            'mom_change_pct': None if pd.isna(row['mom_change_pct'])
                              else float(row['mom_change_pct']),
        }
        for _, row in grouped.iterrows()
    ]


# ---------------------------------------------------------------------------
# 6. People cost ratio (board-level metric)
# ---------------------------------------------------------------------------

def compute_people_cost_ratio(category_rows: list) -> dict:
    """
    Compute people costs (Salaries + Contractor + Benefits + Recruitment)
    as a % of total expenses.

    This is a standard board/investor metric.

    Output: {
        "people_cost_total":       "120000.00",
        "total_expense":           "220000.00",
        "people_cost_ratio_pct":   54.55,
        "breakdown": {
            "SALARIES": "80000.00",
            "CONTRACTOR_FEES": "30000.00",
            "EMPLOYEE_BENEFITS": "8000.00",
            "RECRUITMENT": "2000.00"
        }
    }
    """
    people_categories = COST_CENTER_MAP['People']
    expense_rows = [r for r in category_rows if r.get('record_type') == 'EXPENSE']
    if not expense_rows:
        return {
            'people_cost_total': Decimal('0.00'),
            'total_expense': Decimal('0.00'),
            'people_cost_ratio_pct': 0.0,
            'breakdown': {},
        }

    df = pd.DataFrame(expense_rows)
    df['total'] = df['total'].apply(float)

    total_expense = df['total'].sum()
    people_df = df[df['category'].isin(people_categories)]
    people_total = people_df['total'].sum()

    breakdown = {
        row['category']: _to_decimal(row['total'])
        for _, row in people_df.iterrows()
    }

    ratio = round(people_total / total_expense * 100, 2) if total_expense > 0 else 0.0

    return {
        'people_cost_total': _to_decimal(people_total),
        'total_expense': _to_decimal(total_expense),
        'people_cost_ratio_pct': ratio,
        'breakdown': breakdown,
    }
