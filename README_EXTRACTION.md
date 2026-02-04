# Forex Factory HTML to CSV Extractor

This repository contains tools to extract economic event data from Forex Factory HTML calendar files and output them to CSV format.

## Files

- `extract_html_to_csv.py` - Main script to extract data from HTML files to CSV
- `loc_scraper.py` - Original baseline scraper (for reference)
- `Jan01_2025_June24_2025_events.csv` - Source data for Jan 1 - June 24, 2025
- `June01_2025_December31_2025_events.csv` - Extracted data for June 1 - Dec 31, 2025
- `Jan01_2025_December31_2025_events.csv` - **Final combined output** with all 2025 data

## HTML Files

The following HTML files contain the raw data:
- `June 2025.html`
- `July 2025.html`
- `Aug 2025.html`
- `Sept 2025.html`
- `Oct 2025.html`
- `Nov 2025.html`
- `Dec 2025.html`

## Usage

### Extract data from HTML files:

```bash
python3 extract_html_to_csv.py
```

This will:
1. Parse all HTML files (June-December 2025)
2. Extract economic event data from embedded JSON
3. Generate `June01_2025_December31_2025_events.csv`

### Create combined full-year CSV:

To create a combined CSV with all 2025 data (Jan-Dec), run:

```python
import pandas as pd

# Read both CSV files
df_jan_jun = pd.read_csv("Jan01_2025_June24_2025_events.csv")
df_jun_dec = pd.read_csv("June01_2025_December31_2025_events.csv")

# Filter June-Dec to only include events after June 24
df_jun_dec['DateTime_dt'] = pd.to_datetime(df_jun_dec['DateTime'], utc=True)
june_24_end = pd.to_datetime("2025-06-24T23:59:59-08:00", utc=True)
df_jun25_dec = df_jun_dec[df_jun_dec['DateTime_dt'] > june_24_end].copy()
df_jun25_dec = df_jun25_dec.drop('DateTime_dt', axis=1)

# Combine and sort
combined = pd.concat([df_jan_jun, df_jun25_dec], ignore_index=True)
combined['DateTime_sort'] = pd.to_datetime(combined['DateTime'], utc=True)
combined = combined.sort_values('DateTime_sort')
combined = combined.drop('DateTime_sort', axis=1)
combined = combined.drop_duplicates()

# Save
combined.to_csv("Jan01_2025_December31_2025_events.csv", index=False)
```

## CSV Format

The output CSV files have the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| DateTime | ISO 8601 timestamp with PST timezone | `2025-01-01T00:00:00-08:00` |
| Currency | 3-letter currency code | `USD`, `EUR`, `GBP` |
| Impact | Event impact level | `High Impact Expected`, `Low Impact Expected`, `Medium Impact Expected`, `Non-Economic` |
| Event | Event name | `Unemployment Claims`, `GDP q/q` |
| Actual | Actual value reported | `5.2%`, `230K` |
| Forecast | Forecasted value | `5.0%`, `225K` |
| Previous | Previous value | `5.1%`, `228K` |
| Detail | Additional details (usually empty) | |

## Data Statistics

**Jan01_2025_December31_2025_events.csv:**
- Total events: 4,568
- Date range: January 1, 2025 - December 31, 2025
- Impact distribution:
  - Low Impact Expected: 3,065 events
  - High Impact Expected: 802 events
  - Medium Impact Expected: 575 events
  - Non-Economic: 126 events

## Requirements

```bash
pip install beautifulsoup4 pandas
```

## How It Works

The script extracts data from the embedded JSON (`window.calendarComponentStates[1]`) in the HTML files rather than parsing the HTML table structure. This is more reliable as the HTML table may have hidden or collapsed rows for days beyond the first few days.

Key features:
- Extracts impact levels from JSON data
- Handles time parsing (12-hour format to 24-hour)
- Applies PST timezone offset (-08:00)
- Removes duplicate entries
- Sorts events chronologically
