#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML to CSV Parser for Forex Factory Economic Calendar Data
Extracts economic event data from local HTML files and outputs to CSV format
"""

from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timezone, timedelta
import re
import glob
import os

def extract_json_data(html_content):
    """
    Extract the calendar JSON data embedded in the HTML.
    Returns a mapping of event_id -> impact_title
    """
    impact_map = {}
    
    # Find the calendar component states JavaScript object
    pattern = r'window\.calendarComponentStates\[1\]\s*=\s*({.*?});'
    match = re.search(pattern, html_content, re.DOTALL)
    
    if match:
        js_obj = match.group(1)
        
        # Extract event data using regex since it's JavaScript object notation
        # Pattern: "id":12345 ... "impactTitle":"High Impact Expected"
        events = re.findall(
            r'"id":(\d+)[^}]*?"impactTitle":"([^"]+)"',
            js_obj
        )
        
        for event_id, impact_title in events:
            impact_map[event_id] = impact_title
    
    return impact_map


def parse_calendar_html(html_path, year, month):
    """
    Parse a Forex Factory HTML calendar file and extract event data.
    
    Args:
        html_path: Path to the HTML file
        year: Year of the calendar (e.g., 2025)
        month: Month number (1-12)
    
    Returns:
        pandas DataFrame with columns: DateTime, Currency, Impact, Event, Actual, Forecast, Previous, Detail
    """
    print(f"Parsing file: {html_path}")
    
    try:
        with open(html_path, "r", encoding="cp1252") as f:
            html_content = f.read()
    except Exception as e:
        print(f"Failed to read file: {e}")
        return pd.DataFrame()
    
    # Extract impact mapping from JSON data
    impact_map = extract_json_data(html_content)
    print(f"  Extracted impact data for {len(impact_map)} events")
    
    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr", class_="calendar__row")
    print(f"  Found {len(rows)} calendar rows")
    
    data_list = []
    current_day = None
    last_clock_time = None
    
    month_str = datetime(year, month, 1).strftime("%b")  # e.g., "Jun"
    
    for i, row in enumerate(rows):
        row_classes = row.get("class", [])
        
        # Detect day-breaker rows
        if "calendar__row--day-breaker" in row_classes:
            # Extract date from the day-breaker row
            row_text = row.get_text(separator=" ").strip()
            day_match = re.search(rf"{month_str}\s+(\d{{1,2}})", row_text)
            
            if day_match:
                try:
                    day_num = int(day_match.group(1))
                    current_day = datetime(year, month, day_num)
                    last_clock_time = None
                except Exception as e:
                    print(f"  Warning: Failed to parse day at row {i}: {e}")
                    current_day = None
            continue
        
        if current_day is None:
            continue
        
        # Parse event data from row
        try:
            cells = row.find_all("td")
            
            # Skip blank rows (2 cells with blank content)
            if len(cells) < 5:
                continue
            
            # Extract event ID for impact lookup
            event_id = row.get("data-event-id", "")
            impact = impact_map.get(event_id, "Low Impact Expected")  # Default to Low
            
            # Determine if this is a "new day" row (has date column) or regular row
            # New day rows have 11 cells, regular rows have 10 cells
            # Cell structure for new-day rows (11 cells):
            #   0: Date, 1: Time, 2: Currency, 3: Impact, 4: Event, 5: Sub, 6: Detail, 7: Actual, 8: Forecast, 9: Previous, 10: Graph
            # Cell structure for regular rows (10 cells):
            #   0: Time, 1: Currency, 2: Impact, 3: Event, 4: Sub, 5: Detail, 6: Actual, 7: Forecast, 8: Previous, 9: Graph
            
            has_date_col = len(cells) == 11 or "calendar__row--new-day" in row.get("class", [])
            
            if has_date_col:
                # New day row with date column
                time_text = cells[1].text.strip()
                currency_text = cells[2].text.strip()
                event_text = cells[4].text.strip()
                detail_text = cells[6].text.strip()
                actual_text = cells[7].text.strip()
                forecast_text = cells[8].text.strip()
                previous_text = cells[9].text.strip()
            else:
                # Regular row without date column
                time_text = cells[0].text.strip()
                currency_text = cells[1].text.strip()
                event_text = cells[3].text.strip()
                detail_text = cells[5].text.strip()
                actual_text = cells[6].text.strip()
                forecast_text = cells[7].text.strip()
                previous_text = cells[8].text.strip()
            
            # Skip rows with no event name
            if not event_text:
                continue
            
        except Exception as e:
            continue
        
        # Parse time and create datetime
        event_dt = current_day
        
        # Default to last known time if no time specified
        if last_clock_time is None:
            last_clock_time = (0, 0)
        
        if time_text and time_text not in ["All Day", "Tentative"]:
            # Parse time like "5:00pm" or "12:30am"
            m = re.match(r"(\d{1,2}):(\d{2})(am|pm)", time_text.lower())
            if m:
                hh, mm, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
                if ampm == "pm" and hh < 12:
                    hh += 12
                elif ampm == "am" and hh == 12:
                    hh = 0
                event_dt = event_dt.replace(hour=hh, minute=mm, second=0)
                last_clock_time = (hh, mm)
            else:
                # Use last known time
                hh, mm = last_clock_time
                event_dt = event_dt.replace(hour=hh, minute=mm, second=0)
        elif time_text == "All Day":
            # All day events get time 00:00:00
            event_dt = event_dt.replace(hour=0, minute=0, second=0)
            last_clock_time = (0, 0)
        else:
            # No time specified, use last known time
            hh, mm = last_clock_time
            event_dt = event_dt.replace(hour=hh, minute=mm, second=0)
        
        # Apply PST timezone offset (-08:00)
        # Create timezone-aware datetime
        pst = timezone(timedelta(hours=-8))
        event_dt = event_dt.replace(tzinfo=pst)
        
        data_list.append({
            "DateTime": event_dt.isoformat(),
            "Currency": currency_text,
            "Impact": impact,
            "Event": event_text,
            "Actual": actual_text,
            "Forecast": forecast_text,
            "Previous": previous_text,
            "Detail": detail_text
        })
    
    print(f"  Extracted {len(data_list)} events")
    return pd.DataFrame(data_list)


def main():
    """
    Main function to process all HTML files and generate consolidated CSV.
    """
    # Define the months available as HTML files (June-December 2025)
    html_files = {
        6: "June 2025.html",
        7: "July 2025.html",
        8: "Aug 2025.html",
        9: "Sept 2025.html",
        10: "Oct 2025.html",
        11: "Nov 2025.html",
        12: "Dec 2025.html"
    }
    
    year = 2025
    all_dataframes = []
    
    # Process each HTML file
    for month, filename in sorted(html_files.items()):
        filepath = os.path.join(os.getcwd(), filename)
        
        if not os.path.exists(filepath):
            print(f"Warning: File not found: {filepath}")
            continue
        
        df = parse_calendar_html(filepath, year, month)
        
        if not df.empty:
            all_dataframes.append(df)
    
    # Consolidate all data
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        # Sort by datetime
        combined_df['DateTime_sort'] = pd.to_datetime(combined_df['DateTime'])
        combined_df = combined_df.sort_values('DateTime_sort')
        combined_df = combined_df.drop('DateTime_sort', axis=1)
        
        # Write to CSV
        output_file = "June01_2025_December31_2025_events.csv"
        combined_df.to_csv(output_file, index=False)
        
        print(f"\n{'='*60}")
        print(f"Success! Generated {output_file}")
        print(f"Total events: {len(combined_df)}")
        print(f"Date range: {combined_df['DateTime'].min()} to {combined_df['DateTime'].max()}")
        print(f"{'='*60}")
        
        # Show sample
        print("\nSample of first 10 rows:")
        print(combined_df.head(10).to_string())
    else:
        print("Error: No data was extracted from any files")


if __name__ == "__main__":
    main()
