#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML to CSV Parser for Forex Factory Economic Calendar Data
Extracts economic event data from embedded JSON in HTML files
"""

import pandas as pd
from datetime import datetime, timezone, timedelta
import re
import os

def extract_events_from_json(html_content, year, month):
    """
    Extract all event data from the embedded JSON in the HTML.
    Returns a list of event dictionaries.
    """
    events_list = []
    
    # Find the calendar component states JavaScript object
    pattern = r'window\.calendarComponentStates\[1\]\s*=\s*({.*?});'
    match = re.search(pattern, html_content, re.DOTALL)
    
    if not match:
        print("  Warning: Could not find calendarComponentStates in HTML")
        return events_list
    
    js_obj = match.group(1)
    
    # Extract the days array
    # Pattern to find each day's events
    day_pattern = r'"date":"[^"]*","dateline":(\d+),"add":"","events":\[([^\]]+(?:\][^\]]*\[)*[^\]]*)\]'
    day_matches = re.finditer(day_pattern, js_obj)
    
    for day_match in day_matches:
        dateline = int(day_match.group(1))
        events_block = day_match.group(2)
        
        # Parse individual events in this day
        # Each event is a JSON-like object: {"id":123,"name":"Event Name",...}
        event_pattern = r'\{"id":(\d+)[^}]*"name":"([^"]*)"[^}]*"currency":"([^"]*)"[^}]*"impactTitle":"([^"]*)"[^}]*"timeLabel":"([^"]*)"[^}]*"actual":"([^"]*)"[^}]*"previous":"([^"]*)"[^}]*"revision":"([^"]*)"[^}]*"forecast":"([^"]*)"'
        
        event_matches = re.finditer(event_pattern, events_block)
        
        for event_match in event_matches:
            event_id = event_match.group(1)
            name = event_match.group(2)
            currency = event_match.group(3)
            impact_title = event_match.group(4)
            time_label = event_match.group(5)
            actual = event_match.group(6)
            previous = event_match.group(7)
            revision = event_match.group(8)
            forecast = event_match.group(9)
            
            # Unescape HTML entities in name
            name = name.replace(r'\/', '/').replace(r'\\', '\\')
            
            events_list.append({
                'dateline': dateline,
                'event_id': event_id,
                'name': name,
                'currency': currency,
                'impact': impact_title,
                'time_label': time_label,
                'actual': actual,
                'previous': previous,
                'forecast': forecast
            })
    
    return events_list


def parse_time_label(time_label, base_date):
    """
    Parse time label like "5:00pm", "All Day", "Tentative" and return datetime.
    """
    pst = timezone(timedelta(hours=-8))
    
    if not time_label or time_label in ["All Day", "Tentative", "Day 1", "Day 2", "Day 3"]:
        # All day events or tentative times default to midnight
        return base_date.replace(hour=0, minute=0, second=0, tzinfo=pst)
    
    # Parse time like "5:00pm" or "12:30am"
    m = re.match(r"(\d{1,2}):(\d{2})(am|pm)", time_label.lower())
    if m:
        hh, mm, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
        if ampm == "pm" and hh < 12:
            hh += 12
        elif ampm == "am" and hh == 12:
            hh = 0
        return base_date.replace(hour=hh, minute=mm, second=0, tzinfo=pst)
    
    # Default to midnight if parsing fails
    return base_date.replace(hour=0, minute=0, second=0, tzinfo=pst)


def parse_calendar_html(html_path, year, month):
    """
    Parse a Forex Factory HTML calendar file and extract event data from JSON.
    
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
        print(f"  Failed to read file: {e}")
        return pd.DataFrame()
    
    # Extract events from JSON
    events_list = extract_events_from_json(html_content, year, month)
    print(f"  Extracted {len(events_list)} events from JSON")
    
    # Convert to DataFrame format
    data_list = []
    
    for event in events_list:
        # Convert Unix timestamp to datetime
        dateline = event['dateline']
        base_date = datetime.fromtimestamp(dateline)
        
        # Parse time label and create full datetime
        event_dt = parse_time_label(event['time_label'], base_date)
        
        data_list.append({
            "DateTime": event_dt.isoformat(),
            "Currency": event['currency'],
            "Impact": event['impact'],
            "Event": event['name'],
            "Actual": event['actual'],
            "Forecast": event['forecast'],
            "Previous": event['previous'],
            "Detail": ""  # Detail column is typically empty in the original CSV
        })
    
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
    
    # Use script directory as base path for finding HTML files
    script_dir = os.path.dirname(os.path.abspath(__file__)) if os.path.dirname(__file__) else os.getcwd()
    
    # Process each HTML file
    for month, filename in sorted(html_files.items()):
        filepath = os.path.join(script_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"Warning: File not found: {filepath}")
            continue
        
        df = parse_calendar_html(filepath, year, month)
        
        if not df.empty:
            all_dataframes.append(df)
    
    # Consolidate all data
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        # Remove duplicates
        print(f"\nTotal events before deduplication: {len(combined_df)}")
        combined_df = combined_df.drop_duplicates()
        print(f"Total events after deduplication: {len(combined_df)}")
        
        # Sort by datetime
        combined_df['DateTime_sort'] = pd.to_datetime(combined_df['DateTime'])
        combined_df = combined_df.sort_values('DateTime_sort')
        combined_df = combined_df.drop('DateTime_sort', axis=1)
        
        # Write to CSV in the script directory
        output_file = os.path.join(script_dir, "June01_2025_December31_2025_events.csv")
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
