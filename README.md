# **amedia-core: The backbone package of analyses in Amedia Annonse**

Amedia Annonse is dependent on a wide variety of datadriven analyses. For the purpose of a reproducible, well-documented, efficient, and AI-ready analysis environment, this package has been built to accommodate: 

1. Provide an efficient starting point for new analyses with main dependencies already available 
2. Provide generic, but Amedia-custom utility functions
3. Simplify and standardise the data extraction from Amedias data warehouse (BigQuery)
4. Standardize visualisations using the Amedia color- and font themes

The package is built and intended to work well with Jupyter notebook analyses.

### Installation

**Using uv:**

```bash
uv add "amedia-core @ git+https://github.com/evasahlholdtamedia/amedia-core.git@main"
```

### Getting started

In any notebook, regardless of where it sits in the project:

```python
from core.nb_import import *
```

This imports the core utilities, plotting theme and query helpers, applies the Amedia visual style, and loads the standard analysis libraries (pandas, numpy, matplotlib, seaborn, statsmodels, scikit-learn, etc). It also sets `ROOT` to the project root, found by walking up from the working directory to the nearest `pyproject.toml`. **It is recommended to use uv for your virtual environment and dependency management.**

To fetch data:

```python
df = run_sql(query = query)
```

Where the query is a standard SQL query, for example: 

query = """SELECT * FROM `amedia-adp-marts.dataset.table` LIMIT 10"""

### Modules

| Module | Contents |
|---|---|
| `core.get_client` | BigQuery client (`get_client`), billing project default |
| `core.util` | Query execution (`run_sql`), date helpers, data cleaning |
| `core.theme` | Amedia colour palette, fonts, `apply_style()` |
| `core.nb_import` | Notebook bootstrap — imports everything above plus standard libraries |

All of these are imported by running `from core.nb_import import *` in a notebook cell or Python script.

### Plotting conventions

`apply_style()` runs automatically on import and sets the Amedia fonts, colours and figure defaults. 

Plot functions follow the signature `def plot_name(df, w, h)`, where `w` and `h` are the figure width and height in inches, and return `(fig, axes)`.

### Updating

To pull the latest version of core into a project:

```bash
uv lock --upgrade-package amedia-core && uv sync
```

## **Important**

To extract data from BigQuery, the default billing project is **"amedia-analytics-eu"**. This is correct for most use cases in analyses in Amedia Annonse. 

If a different billing project is required, point to it (str) use parameter billing_project in the run_sql function: 

```python
df = run_sql(query = query, billing_project = "your_billing_proj")
```