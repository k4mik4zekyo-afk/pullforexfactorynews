#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  4 12:47:44 2026

@author: kylesuico
"""

from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re

def parse_calendar_month_from_html_debug(html_path, year, month):
    print(f"Opening file: {html_path}")
    try:
        with open(html_path, "r", encoding="cp1252") as f:
            html_content = f.read()
    except Exception as e:
        print(f"Failed to read file: {e}")
        return pd.DataFrame()
    
    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr")
    print(f"Total <tr> rows found: {len(rows)}")
    
    data_list = []
    current_day = None
    last_clock_time = None
    
    month_str = datetime(year, month, 1).strftime("%b")  # e.g., "Jun"
    
    for i, row in enumerate(rows):
        row_classes = row.get("class", [])
        # Detect day-breaker based on class OR text pattern "Month Day"
        row_text = row.get_text(separator=" ").strip()
        day_match = re.search(rf"{month_str}\s+(\d{{1,2}})", row_text)
        if "day-breaker" in "".join(row_classes) or day_match:
            try:
                if day_match:
                    day_num = int(day_match.group(1))
                else:
                    # fallback: try last number in text
                    day_num = int(re.findall(r"\d+", row_text)[-1])
                current_day = datetime(year, month, day_num)
                print(f"Detected new day: {current_day.date()} at row {i}")
                last_clock_time = None
            except Exception as e:
                print(f"Failed to parse day at row {i}: {e}")
                current_day = None
            continue
    
        if current_day is None:
            print(f"Skipping row {i} because current_day not set")
            continue
    
        # Try to parse event cells
        try:
            cells = row.find_all("td")
            if len(cells) < 5:
                print(f"Skipping row {i}, not enough cells")
                continue
    
            # Time, Currency, Event, Actual, Forecast, Previous
            time_text = cells[0].text.strip()
            currency_text = cells[1].text.strip()
            event_text = cells[2].text.strip()
            actual_text = cells[3].text.strip()
            forecast_text = cells[4].text.strip()
            previous_text = cells[5].text.strip() if len(cells) > 5 else ""
    
        except Exception as e:
            print(f"Skipping row {i} due to parsing error: {e}")
            continue
    
        # Compute datetime
        event_dt = current_day
        last_clock_time = last_clock_time or (0, 0)
    
        if time_text:
            m = re.match(r"(\d{1,2}):(\d{2})(am|pm)", time_text.lower())
            if m:
                hh, mm, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
                if ampm == "pm" and hh < 12:
                    hh += 12
                if ampm == "am" and hh == 12:
                    hh = 0
                event_dt = event_dt.replace(hour=hh, minute=mm)
                last_clock_time = (hh, mm)
            else:
                hh, mm = last_clock_time
                event_dt = event_dt.replace(hour=hh, minute=mm)
        else:
            hh, mm = last_clock_time
            event_dt = event_dt.replace(hour=hh, minute=mm)
    
        data_list.append({
            "DateTime": event_dt.isoformat(),
            "Currency": currency_text,
            "Event": event_text,
            "Actual": actual_text,
            "Forecast": forecast_text,
            "Previous": previous_text
        })
    
        print(f"Row {i} event: {currency_text} {event_text} at {event_dt}")
    
    print(f"Total events parsed: {len(data_list)}")
    return pd.DataFrame(data_list)

if __name__ == "__main__":
    import os
    print("Current WD:", os.getcwd())
    df = parse_calendar_month_from_html_debug("src/forexfactory/June 2025.html", 2025, 6)
    print(df.head())
    df.to_csv("forex_jun2025_from_html.csv", index=False)

