import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- SETTINGS ---
TELEGRAM_USERNAME = "apl450" # <--- PUT YOUR USERNAME HERE
PAGE_TITLE = "Lesson Slots"

# The Grid
TIME_SLOTS = [
    "10:15", "11:30", "12:45", 
    "14:00", "15:15", "16:30", 
    "17:45", "19:00", "20:15"
]

st.set_page_config(page_title=PAGE_TITLE, page_icon="📅")

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_data(url):
    try:
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv")
        csv_url = csv_url.replace("/edit#gid=", "/export?format=csv&gid=")
        df = pd.read_csv(csv_url)
        
        # Clean columns
        df.columns = [c.strip() for c in df.columns]
        if 'Day_or_Date' in df.columns:
            df = df.rename(columns={'Day_or_Date': 'Date'})
            
        # Standardize text
        df['Date'] = df['Date'].astype(str).str.strip()
        df['Time'] = df['Time'].astype(str).str.strip()
        
        # Handle the 3rd column (Student/Status)
        # We rename it to 'Status' for code clarity
        if len(df.columns) >= 3:
            df.columns.values[2] = "Status"
            df['Status'] = df['Status'].astype(str).str.strip()
        else:
            df['Status'] = "Busy"
        
        return df
    except Exception:
        return pd.DataFrame(columns=["Date", "Time", "Status"])

# Load from Secrets
if "public_sheet_url" in st.secrets:
    sheet_url = st.secrets["public_sheet_url"]
    df_all = load_data(sheet_url)
else:
    st.error("Missing Google Sheet URL in Secrets.")
    st.stop()

# --- DISPLAY ---
st.title(PAGE_TITLE)
st.write("Available slots for the next 2 weeks.")
st.info("Tap a green button to book via Telegram.")

today = datetime.now().date()

for i in range(14):
    current_date = today + timedelta(days=i)
    date_str = current_date.strftime("%Y-%m-%d") # e.g. 2026-01-01
    day_name = current_date.strftime("%A")       # e.g. Monday
    display_date = current_date.strftime("%A, %d %B")
    
    # 1. Check for Specific Date Overrides (e.g., "2026-01-01")
    specific_blocks = df_all[df_all['Date'] == date_str]
    
    # 2. Check for Recurring Day Blocks (e.g., "Monday")
    recurring_blocks = df_all[df_all['Date'] == day_name]

    # Check if the WHOLE DAY is blocked (Time="ALL")
    # But specific "OPEN" overrides "ALL"
    day_is_off_recurring = "ALL" in recurring_blocks['Time'].values
    day_is_off_specific = "ALL" in specific_blocks['Time'].values
    
    # Logic: Only warn "Day Off" if there are no explicit "OPEN" slots for today
    has_forced_opens = specific_blocks['Status'].str.upper().str.contains("OPEN").any()
    
    with st.expander(display_date, expanded=(i < 3)):
        if (day_is_off_specific or day_is_off_recurring) and not has_forced_opens:
            st.warning("⛔ Day Off")
        else:
            cols = st.columns(3)
            for index, slot in enumerate(TIME_SLOTS):
                
                # STATUS CHECK ALGORITHM
                is_available = True 
                
                # A. Check Specific Date Override first (Best for "One-off" changes)
                slot_specific = specific_blocks[specific_blocks['Time'] == slot]
                
                if not slot_specific.empty:
                    # If row exists, check if it says "OPEN"
                    status = slot_specific.iloc[0]['Status'].upper()
                    if "OPEN" in status:
                        is_available = True
                    else:
                        is_available = False # Blocked by name or "Busy"
                
                # B. If no specific override, check Recurring & Weekend Rules
                else:
                    if slot in recurring_blocks['Time'].values:
                        is_available = False # Blocked by weekly schedule
                    if day_is_off_recurring or day_is_off_specific:
                        is_available = False # Weekend or Holiday

                # RENDER BUTTON
                if is_available:
                    msg = f"Hi! Is the {slot} slot on {display_date} available?"
                    link = f"https://t.me/{TELEGRAM_USERNAME}"
                    cols[index % 3].link_button(f"✅ {slot}", link, type="primary")
                else:
                    cols[index % 3].button(f"❌ {slot}", key=f"{date_str}_{slot}", disabled=True)

st.divider()
