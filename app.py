import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- SETTINGS ---
TELEGRAM_USERNAME = "apl450"  # <--- REMEMBER TO PUT YOUR USERNAME HERE!
PAGE_TITLE = "Lesson Slots"

# The Grid
TIME_SLOTS = [
    "10:15", "11:30", "12:45", 
    "14:00", "15:15", "16:30", 
    "17:45", "19:00", "20:15"
]

st.set_page_config(page_title=PAGE_TITLE, page_icon="📅")

# --- DATA LOADER ---
@st.cache_data(ttl=60)
def load_data(url):
    try:
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv")
        csv_url = csv_url.replace("/edit#gid=", "/export?format=csv&gid=")
        
        # Robust loading to prevent crashes
        df = pd.read_csv(csv_url, engine='python', on_bad_lines='skip')
        
        # AUTO-FIX: If columns are stuck together (User didn't split text)
        if len(df.columns) == 1:
            col_name = df.columns[0]
            df_split = df[col_name].astype(str).str.split(',', expand=True)
            if "Date" in col_name:
                headers = col_name.split(',')
                if len(headers) == df_split.shape[1]:
                    df_split.columns = [h.strip() for h in headers]
            df = df_split

        # Clean headers
        df.columns = [c.strip() for c in df.columns]
        
        # Standardize Names
        if 'Day_or_Date' in df.columns:
            df = df.rename(columns={'Day_or_Date': 'Date'})
            
        # Clean Data
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str).str.strip()
        if 'Time' in df.columns:
            df['Time'] = df['Time'].astype(str).str.strip()
            
        # Ensure Status exists
        if 'Status' not in df.columns:
            if len(df.columns) >= 3:
                 df.rename(columns={df.columns[2]: "Status"}, inplace=True)
            else:
                 df['Status'] = "Busy"
        
        # Make Status UPPERCASE for easier matching (open -> OPEN)
        df['Status'] = df['Status'].astype(str).str.strip().str.upper()
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Time", "Status"])

# --- MAIN APP ---
if "public_sheet_url" in st.secrets:
    sheet_url = st.secrets["public_sheet_url"]
    df_all = load_data(sheet_url)
else:
    st.error("Please add your Google Sheet URL to Streamlit Secrets!")
    st.stop()

st.title(PAGE_TITLE)
st.write("Available slots for the next 2 weeks.")
st.info("Tap a green button to book via Telegram.")

today = datetime.now().date()

for i in range(14):
    current_date = today + timedelta(days=i)
    date_str = current_date.strftime("%Y-%m-%d") 
    day_name = current_date.strftime("%A")       
    display_date = current_date.strftime("%A, %d %B")
    
    # 1. Get rules for this specific Date (e.g. 2026-01-03)
    specific_blocks = df_all[df_all['Date'] == date_str]
    # 2. Get rules for this Day of Week (e.g. Saturday)
    recurring_blocks = df_all[df_all['Date'] == day_name]

    # --- LOGIC START ---
    
    # Check for "Whole Day" specific overrides (e.g. 2026-01-03, ALL, OPEN)
    specific_day_row = specific_blocks[specific_blocks['Time'] == 'ALL']
    is_forced_open_day = False
    is_day_blocked = False

    if not specific_day_row.empty:
        # If there is an ALL row, does it say OPEN?
        if "OPEN" in specific_day_row.iloc[0]['Status']:
            is_forced_open_day = True # MASTER KEY: Day is OPEN
        else:
            is_day_blocked = True # Day is explicitly BLOCKED
    else:
        # No specific override, check recurring (e.g. Saturdays usually blocked?)
        if "ALL" in recurring_blocks['Time'].values:
            is_day_blocked = True # Day is recursively BLOCKED (Weekend)
    
    # Draw the UI
    with st.expander(display_date, expanded=(i < 3)):
        # Only show Warning if blocked AND NOT forced open
        if is_day_blocked and not is_forced_open_day:
            st.warning("⛔ Day Off")
        else:
            cols = st.columns(3)
            for index, slot in enumerate(TIME_SLOTS):
                
                is_available = True 
                
                # A. Check Specific Slot Override (Best for "One-off" changes)
                slot_specific = specific_blocks[specific_blocks['Time'] == slot]
                
                if not slot_specific.empty:
                    # If a specific row exists (e.g. 14:00), trust it 100%
                    status = slot_specific.iloc[0]['Status']
                    is_available = "OPEN" in status
                
                elif is_forced_open_day:
                    # If "ALL" is OPEN, then every slot is available!
                    is_available = True
                    
                else:
                    # Fallback to Standard Rules
                    if slot in recurring_blocks['Time'].values:
                        is_available = False # Blocked by weekly schedule
                    if is_day_blocked:
                        is_available = False # Blocked by Weekend/Holiday

                # RENDER BUTTON
                if is_available:
                    msg = f"Hi! Is the {slot} slot on {display_date} available?"
                    link = f"https://t.me/{TELEGRAM_USERNAME}"
                    cols[index % 3].link_button(f"✅ {slot}", link, type="primary")
                else:
                    cols[index % 3].button(f"❌ {slot}", key=f"{date_str}_{slot}", disabled=True)

st.divider()
