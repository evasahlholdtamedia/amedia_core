## This script contain general utility functions useful in any project.
## It is called in nb_import.py, no need for additional imports.

import os
import re
import pandas as pd
from core.get_client import get_client, BILLING_PROJECT
from google.cloud import bigquery
from google.api_core import exceptions
from pathlib import Path
from datetime import datetime, date
import sys
import inspect

## TO BE ADDED: 

# "Skeleton" for SQL queries

def get_functions():
    """Lists all utility functions available in this module with their signatures and docstrings."""
    current_module = sys.modules[__name__]

    for name, func in sorted(inspect.getmembers(current_module, inspect.isfunction)):
        if name.startswith("_") or name == "get_functions":
            continue
        if func.__module__ != current_module.__name__:
            continue

        signature = inspect.signature(func)
        docstring = inspect.getdoc(func) or "No docstring."
        print(f"{name}{signature}")
        print(f"    {docstring}")
        print()

def run_sql(query: str, billing_project: str = BILLING_PROJECT):
    '''
    Query GCP and return a dataframe. 
    
    Args:
        query: SQL query
        billing_project: Custom billing project; defaults to "amedia-analytics-eu"
    
    Returns:
        pd.DataFrame: Dataframe with queryed data.    
    '''
    client = get_client(billing_project)

    dry_run = client.query(
        query,
        job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
    )
    gb = dry_run.total_bytes_processed / 1e9
    cost_usd = dry_run.total_bytes_processed / 2**40 * 6.25
    print(f"Estimated scan: {gb:.2f} GB")
    print(f"Estimated cost: ~${cost_usd:.3f}")

    print("Running query...")
    return client.query(query).to_dataframe()

def save(df, filename):
    """
    Saves a DataFrame as a CSV in the 'data' folder within the cwd.
    
    Args:
        df (pd.DataFrame): The DataFrame to export.
        filename (str): The desired name of the file.
    """
    target_dir = os.path.join(os.getcwd(), "data")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    if filename.endswith(".csv"):
        pass
    else:
        filename = f"{filename}.csv"
    export_path = os.path.join(target_dir, filename)
    df.to_csv(export_path, index=False)

def save_xlsx(df, filename):
    """
    Saves a DataFrame as .xlsx with frozen header panes in the 'data' folder within the cwd.

    Args:
        df (pd.DataFrame): The DataFrame to export.
        filename (str): The desired name of the file.
    """
    df_export = df.copy()

    for col in df_export.columns:
        if pd.api.types.is_datetime64_any_dtype(df_export[col]) or df_export[col].dtype == "object":
            try:
                df_export[col] = pd.to_datetime(df_export[col]).dt.tz_localize(None).dt.date
            except (ValueError, TypeError):
                pass

    target_dir = Path.cwd() / "data"
    target_dir.mkdir(parents=True, exist_ok=True)

    export_path = target_dir / f"{Path(filename).stem}.xlsx"

    with pd.ExcelWriter(export_path, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False)
        writer.sheets["Sheet1"].freeze_panes = "A2"

def save_fig(fig, name, folder=None, dpi=200):
    """
    Saves a plot figure in data/plots in the cwd.

    Args:
        fig: The figure element 
        name: A suitable figure name
        folder: Defaults to data/plots, but can be overwritten.
        dpi: Pixel resolutions, defaults to 200.
    """
    folder = Path.cwd() / "data" / "plots" if folder is None else Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    slug = name.lower().translate(str.maketrans({"æ": "ae", "ø": "o", "å": "a"}))
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    path = folder / f"{slug}.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight")

def load(filename, parent_folder=None):
    """
    Loads a CSV file from the 'data' folder within the CWD.
    
    Args:
        filename (str): The name of the CSV file to load.
        parent_folder (str): Optional name of a parent folder to search upward for. If provided, looks for 'data' folder inside that parent instead of CWD.
    
    Returns:
        pd.DataFrame: The loaded DataFrame.
    """
    if not filename.endswith(".csv"): filename = f"{filename}.csv"
    if parent_folder:
        base = next((p for p in Path.cwd().parents if p.name == parent_folder), None)
        if base is None: raise FileNotFoundError(f"Parent folder '{parent_folder}' not found in path hierarchy.")
    else:
        base = Path.cwd()
    return pd.read_csv(base / "data" / filename)

def _clean_columns(df):
    """
    Internal function. 

    Normalises column names: lowercase, strip, collapse whitespace and repeated underscores. 
    
    Handles non-string names, MultiIndex and duplicates.
    """
    df = df.copy()

    def clean(name):
        if isinstance(name, tuple):
            parts = [clean(p) for p in name if p is not None]
            return "_".join(p for p in parts if p) or "column"
        text = re.sub(r"[\s_]+", "_", str(name).strip().lower()).strip("_")
        return text or "column"

    seen, names = {}, []
    for raw in df.columns:
        name = clean(raw)
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        names.append(name)

    df.columns = names
    return df

def _trim_strings(df):
    """
    Internal function.
    
    Strip leading and trailing whitespace from string values.
    """
    df = df.copy()
    for i, dtype in enumerate(df.dtypes):
        s = df.iloc[:, i]
        if isinstance(dtype, pd.StringDtype):
            df.isetitem(i, s.str.strip())
        elif dtype == object:
            df.isetitem(i, s.map(lambda x: x.strip() if isinstance(x, str) else x))
    return df

def _blank_to_na(df):
    """
    Internal function.
    
    Convert empty and whitespace-only strings to NA.
    """
    df = df.copy()
    for i, dtype in enumerate(df.dtypes):
        if not (dtype == object or isinstance(dtype, pd.StringDtype)):
            continue
        s = df.iloc[:, i]
        blank = s.map(lambda x: isinstance(x, str) and x.strip() == "")
        blank = blank.fillna(False).astype(bool)
        if blank.any():
            df.isetitem(i, s.mask(blank, pd.NA))
    return df

def _drop_empty(df, axis=1):
    """
    Internal function.
    
    Drop all-null columns (axis=1) or rows (axis=0).
    """
    if df.shape[1 - axis] == 0:
        return df.copy()
    return df.dropna(axis=axis, how="all")

def _coerce_numeric_columns(df, integers=True):
    """
    Internal function.
    
    Convert string columns whose values are all numeric into Int64 or Float64.

    Float: Columns with at least one decimal number
    Int: Columns with whole numbers only

    Columns with any non-numeric value, ambiguous commas, or leading zeros areleft untouched.
    """
    plain = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
    grouped = re.compile(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?$")
    df = df.copy()
    for i in range(df.shape[1]):
        dtype = df.dtypes.iloc[i]
        if not (dtype == object or isinstance(dtype, pd.StringDtype)): continue
        values = df.iloc[:, i]
        non_null = values.dropna()
        if non_null.empty or not all(isinstance(v, str) for v in non_null): continue
        stripped = non_null.str.strip()
        if not stripped.map(lambda v: bool(plain.match(v) or grouped.match(v))).all(): continue
        if stripped.str.match(r"^[+-]?0\d").any(): continue
        numbers = pd.to_numeric(values.str.strip().str.replace(",", "", regex=False), errors="coerce")
        if integers and numbers.dropna().mod(1).eq(0).all() and numbers.abs().max() < 2**53: df.isetitem(i, numbers.astype("Int64"))
        else: df.isetitem(i, numbers.astype("Float64"))
    return df

def _round_numerics(df, decimals):
    """
    Internal function.
    
    Round float columns to a given number of decimals.
    """
    df = df.copy()
    if decimals is None:
        return df
    for i, dtype in enumerate(df.dtypes):
        if pd.api.types.is_float_dtype(dtype):
            df.isetitem(i, df.iloc[:, i].round(decimals))
    return df

def format_dataframe(df, decimals=2):
    """
    Format a pd.DataFrame to custom standards:
    - Normalises column names: lowercase, strip, collapse whitespace and repeated underscores. 
    - Trims strings and convert blanks to NA.
    - Drops all-null columns.
    - Rounds float columns to default 2 decimals.
    
    Args: 
        decimals: Int. Number of decimals to round to.

    Returns:
        df: Formatted dataframe.
    """
    df = _clean_columns(df)
    df = _trim_strings(df)
    df = _blank_to_na(df)
    df = _drop_empty(df)
    df = _coerce_numeric_columns(df)
    df = _round_numerics(df, decimals)
    return df

_unit_scale = {
    None: (1, None),
    "tusen": (1e3, "tusen"),
    "T": (1e3, "tusinn"),
    "1000": (1e3, "tusinn"),
    "mill": (1e6, "M"),
    "M": (1e6, "M"),
    "mil": (1e6, "M"),
    "million": (1e6, "M"),
    "millioner": (1e6, "M"),
    "1000000": (1e6, "M"),
}

def format_numbers(value, scale=None, decimals=2, unit=None):
    '''
    Formats a number using Norwegian conventions: Space as thousands separator
    and comma as decimal separator. Mainly intended for visualisations.

    Args:
        value (float | int): The number to format.
        scale (str, optional): Scale to divide by. None (default) leaves the value unscaled.
        decimals (int): Number of decimals. Defaults to 2.
        unit (str, optional): String appended after the number, e.g. 'kr' or '%'. Defaults to None (nothing appended).

    Returns:
        str: The formatted number.
    '''
    if scale not in _unit_scale:
        valid = ", ".join(repr(k) for k in _unit_scale)
        raise ValueError(f"scale must be one of {valid}, got {scale!r}")

    if value is None or pd.isna(value):
        return "–"

    divisor, scale_label = _unit_scale[scale]
    text = f"{value / divisor:,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")

    parts = [text]
    if scale_label:
        parts.append(scale_label)
    if unit:
        parts.append(unit)

    return "\u00a0".join(parts)

def filter_timeframe(df, date_field=None, years=None, current_year=False, yoy=False, full_years=False, start_date=None, end_date=None):
    """
    Utility function to filter for a specific period in a dataframe. 

    Defaults to full date range if nothing is defined.
    
    Args: 
        df: Dataframe
        date_field: The date columm to utilise
        years: Specific years provided as a list, e.g. [2025, 2026]
        current_year: If True, includes only data from the current year
        yoy: If True, gets data from current year and same period in previous year
        full_years: If True, gets data from all completed years in the dataset
        start_date: None, if given sets a start date. Format: "2026-12-31" (year-month-day)
        end_date: None, if givens sets an end date. Format: "2026-12-31" (year-month-day)
        
    Returns:
        df: Dataframe filtered according to parameters
    """
    months = ["januar", "februar", "mars", "april", "mai", "juni", "juli",
                "august", "september", "oktober", "november", "desember"]
    
    if date_field is None:
        if "revenue_date" in df.columns:
            date_field = "revenue_date"
            print("Setting revenue_date as default date field.")
        elif "campaign_start_ts" in df.columns:
            date_field = "campaign_start_ts"
            print("Setting campaign_start_ts as default date field.")
        else:
            candidates = [c for c in df.columns if "date" in c.lower()]
            if candidates:
                date_field = candidates[0]
                print(f"Setting {date_field} as default date field.")
            else:
                raise ValueError("Provide date_field.")

    if sum([bool(years), current_year, yoy, full_years]) > 1:
        raise ValueError("Specify only one of years (specific years defined in a list), current_year (bool), yoy (bool), or full_years (bool).")

    if (start_date is not None or end_date is not None) and sum([bool(years), current_year, yoy, full_years]) > 0:
        raise ValueError("Specify either start/end date OR year-based parameter.")

    d = df.copy()
    d[date_field] = pd.to_datetime(d[date_field])

    today_year = date.today().year

    if start_date is not None or end_date is not None:
        result = d
        if start_date is not None:
            result = result[result[date_field] >= pd.to_datetime(start_date)]
            start, end = result[date_field].min(), result[date_field].max()
            period_label = f"{start.date()} til {end.date()}"
        if end_date is not None:
            result = result[result[date_field] <= pd.to_datetime(end_date)]
            start, end = result[date_field].min(), result[date_field].max()
            period_label = f"{start.date()} til {end.date()}"
        if result.empty:
            raise ValueError(f"No data in the window {start_date} to {end_date}.")

    elif years:
        result = d[d[date_field].dt.year.isin(years)]
        missing = sorted(set(years) - set(result[date_field].dt.year.unique()))
        if missing:
            raise ValueError(f"No data for year(s): {missing}.")
        start, end = result[date_field].min(), result[date_field].max()
        period_label = f"{months[start.month - 1]} {start.year} til {months[end.month - 1]} {end.year}"
        print(f"Filtered data to include {years}")

    elif current_year:
        result = d[d[date_field].dt.year == today_year]
        if result.empty:
            raise ValueError(f"No data for year {today_year}.")
        start, end = result[date_field].min(), result[date_field].max()
        period_label = f"{months[start.month - 1]} {start.year} til {months[end.month - 1]} {end.year}"
        print(f"Filtered data to include {today_year}")

    elif yoy:
        cur = d[d[date_field].dt.year == today_year]
        if cur.empty:
            raise ValueError(f"No data for year {today_year}.")
        months_present = sorted(cur[date_field].dt.month.unique())
        prev = d[(d[date_field].dt.year == today_year - 1) & (d[date_field].dt.month.isin(months_present))]
        result = pd.concat([prev, cur]).sort_values(date_field)
        start, end = result[date_field].min(), result[date_field].max()
        period_label = f"{months[start.month - 1]} til {months[end.month - 1]} i {start.year} og {end.year}"
        print(f"Filtered data to include data from {months[start.month - 1]} to {months[end.month - 1]} in {start.year} and {end.year}")

    elif full_years:
        result = d[d[date_field].dt.year < today_year]
        if result.empty:
            raise ValueError("No completed years in the dataset.")
        start, end = result[date_field].min(), result[date_field].max()
        period_label = f"{months[start.month - 1]} {start.year} til {months[end.month - 1]} {end.year}"
        print(f"Filtered data to include {start.year} to {end.year}")

    else:
        print("No period filters applied")
        result = d
        start, end = result[date_field].min(), result[date_field].max()
        period_label = f"{months[start.month - 1]} {start.year} til {months[end.month - 1]} {end.year}"

    return result, period_label

def _validate_timeseries(df, date_field=None, cycle="yearly", granularity="monthly", group_field=None):
    """
    Internal function. 

    Validates if there is sufficient data for time series analyses.

    Prints missing granularity periods within each cycle period, for the dataset as
    a whole or separately for each group. Weekly granularity uses ISO week numbers
    (Monday-start).

    Args:
        df: Dataframe
        date_field: The date column to utilise
        cycle: The larger period to check completeness within. One of:
            "yearly", "quarterly", "monthly", "weekly", "daily"
        granularity: The smaller period that should be present within each cycle.
            One of: "quarterly", "monthly", "weekly", "daily", "hourly"
        group_field: Optional column to check completeness separately per group
    """
    freq_map = {
        "yearly": "Y", "quarterly": "Q", "monthly": "M",
        "weekly": "W", "daily": "D", "hourly": "h"}
    
    order = ["yearly", "quarterly", "monthly", "weekly", "daily", "hourly"]

    if date_field is None:
        if "revenue_date" in df.columns:
            date_field = "revenue_date"
            print("Setting revenue_date as default date field.")
        elif "campaign_start_ts" in df.columns:
            date_field = "campaign_start_ts"
            print("Setting campaign_start_ts as default date field.")
        else:
            candidates = [c for c in df.columns if "date" in c.lower()]
            if candidates:
                date_field = candidates[0]
                print(f"Setting {date_field} as default date field.")
            else:
                raise ValueError("Provide date_field.")

    if cycle not in ["yearly", "quarterly", "monthly", "weekly", "daily"]:
        raise ValueError("cycle must be in: yearly, quarterly, monthly, weekly, daily.")

    if granularity not in ["quarterly", "monthly", "weekly", "daily", "hourly"]:
        raise ValueError("granularity must be in: quarterly, monthly, weekly, daily, hourly.")

    if order.index(granularity) <= order.index(cycle):
        raise ValueError(f"granularity ({granularity}) must be finer than cycle ({cycle}).")

    d = df.copy()
    d[date_field] = pd.to_datetime(d[date_field])
    d["_cycle"] = d[date_field].dt.to_period(freq_map[cycle])

    if granularity == "weekly":
        iso = d[date_field].dt.isocalendar()
        d["_gran"] = list(zip(iso["year"].astype(int), iso["week"].astype(int)))
    else:
        d["_gran"] = d[date_field].dt.to_period(freq_map[granularity])

    groups = d[group_field].unique() if group_field else [None]

    for group in groups:
        sub = d[d[group_field] == group] if group_field else d
        for cycle_val in sorted(sub["_cycle"].unique()):
            cycle_rows = sub[sub["_cycle"] == cycle_val]
            actual = set(cycle_rows["_gran"].unique())

            if granularity == "weekly":
                days = pd.date_range(cycle_val.start_time, cycle_val.end_time, freq="D")
                mondays_iso = days[days.dayofweek == 0].isocalendar()
                expected = set(zip(mondays_iso["year"].astype(int), mondays_iso["week"].astype(int)))
                missing = sorted(set(expected) - actual)
                missing_labels = [f"week {w} {y}" for y, w in missing]
            else:
                expected = pd.period_range(start=cycle_val.start_time, end=cycle_val.end_time, freq=freq_map[granularity])
                missing = sorted(set(expected) - actual)
                missing_labels = [str(m) for m in missing]

            if missing:
                group_label = f" for class {group}" if group_field else ""
                print(f"Warning: Missing data{group_label} in {cycle_val}. Missing periods ({granularity}): {missing_labels}")

def get_timeseries_periods(df, date_field=None, cycle="yearly", granularity="monthly", group_field=None):
    """
    
    Get data and labels periodized after granularity.
        Get data periodized after granularity (e.g. by month) 
        Get period time_labels for plots (e.g. labels like jan, feb, ...)
        Validate data completeness in the cycle

    Args: 
        df: Dataframe
        date_field: Date field to base period time_labels on
        cycle: What constitutes a cycle; usually default (yearly) is relevant.
        granularity: Period intervals. Takes "yearly", "quarterly", "monthly", "weekly", "daily", "hourly".

    Returns:
        time_labels: List of formatted period label strings, sorted chronologically.
        """
    if date_field is None:
        if "revenue_date" in df.columns:
            date_field = "revenue_date"
            print("Setting revenue_date as default date field.")
        elif "campaign_start_ts" in df.columns:
            date_field = "campaign_start_ts"
            print("Setting campaign_start_ts as default date field.")
        else:
            candidates = [c for c in df.columns if "date" in c.lower()]
            if candidates:
                date_field = candidates[0]
                print(f"Setting {date_field} as default date field.")
            else:
                raise ValueError("Provide date_field.")

    if granularity not in ["yearly", "quarterly", "monthly", "weekly", "daily", "hourly"]:
        raise ValueError("granularity must be in: yearly, quarterly, monthly, weekly, daily, hourly.")

    freq_map = {
        "yearly": "Y", "quarterly": "Q", "monthly": "M",
        "weekly": "W", "daily": "D", "hourly": "h"}

    # time_labels
    months = ["jan", "feb", "mar", "apr", "mai", "jun", "jul", "aug", "sep", "okt", "nov", "des"]

    d = pd.to_datetime(df[date_field])
    multi_year = d.dt.year.nunique() > 1

    if granularity == "yearly":
        period_label = "År"
        time_labels = [str(y) for y in sorted(d.dt.year.unique())]

    elif granularity == "quarterly":
        period_label = "Kvartal"
        periods = sorted(d.dt.to_period("Q").unique())
        time_labels = []
        prev_year = None
        for p in periods:
            quarter_label = f"Q{p.quarter}"
            if multi_year and p.year != prev_year:
                quarter_label = f"{quarter_label}\n{p.year}"
            time_labels.append(quarter_label)
            prev_year = p.year

    elif granularity == "monthly":
        period_label = "Måned"
        periods = sorted(d.dt.to_period("M").unique())
        time_labels = []
        prev_year = None
        for p in periods:
            month_label = months[p.month - 1]
            if multi_year and p.year != prev_year:
                month_label = f"{month_label}\n{p.year}"
            time_labels.append(month_label)
            prev_year = p.year

    elif granularity == "weekly":
        period_label = "Uke"
        iso = d.dt.isocalendar()
        weeks = sorted(set(zip(iso["year"], iso["week"])))
        time_labels = []
        for y, w in weeks:
            mask = (iso["year"] == y) & (iso["week"] == w)
            month = d[mask].iloc[0].month
            time_labels.append(f"Uke {w}\n({months[month - 1]})")

    elif granularity == "daily":
        period_label = "Dato"
        days = sorted(d.dt.normalize().unique())
        fmt = "%d/%m/%Y" if multi_year else "%d/%m"
        time_labels = [pd.Timestamp(day).strftime(fmt) for day in days]

    elif granularity == "hourly":
        period_label = "Time"
        hours = sorted(d.dt.hour.unique())
        time_labels = [f"{h:02d}.00" for h in hours]

    # Period/frequency
    d = df.copy()
    d[date_field] = pd.to_datetime(d[date_field])
    d[period_label] = d[date_field].dt.to_period(freq_map[granularity]).dt.to_timestamp()
    print(f"Added period label by {granularity}. Label: {period_label}")

    # Validate
    _validate_timeseries(df, date_field=date_field, cycle=cycle, granularity=granularity, group_field=group_field)

    return d, period_label, time_labels