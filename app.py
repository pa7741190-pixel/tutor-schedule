import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- SETTINGS ---
# 1. Your Telegram username (without the @)
TELEGRAM_USERNAME = "YourUsernameHere" 
PAGE_TITLE = "🇬🇧 English Lesson Slots"

# 2. Your Time Grid (10:15 start, 20:15 last slot)
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
        # Convert Google Sheet URL to CSV export URL
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv")
        csv_url = csv_url.replace("/edit#gid=", "/export?format=csv&gid=")
        
        # Load the CSV
        df = pd.read_csv(csv_url)
        
        # PRIVACY: Keep only Date/Time columns. Drop the Names column immediately.
        # We rename columns to be standard just in case
        df.columns = [c.strip() for c in df.columns]
        if 'Day_or_Date' in df.columns:
            df = df.rename(columns={'Day_or_Date': 'Date'})
            
        # Ensure data is string format for matching
        df['Date'] = df['Date'].astype(str).str.strip()
        df['Time'] = df['Time'].astype(str).str.strip()
        
        return df[['Date', 'Time']] # Return only what we need
    except Exception:
        return pd.DataFrame(columns=["Date", "Time"])

# Load Secrets
if "public_sheet_url" in st.secrets:
    sheet_url = st.secrets["public_sheet_url"]
    df_blocked = load_data(sheet_url)
else:
    st.error("Please add your Google Sheet URL to Streamlit Secrets!")
    st.stop()

# --- DISPLAY ---
st.title(PAGE_TITLE)
st.write("Here are my available slots for the next 2 weeks.")
st.info("Tap a green button to book via Telegram.")

today = datetime.now().date()

# Show next 14 days
for i in range(14):
    current_date = today + timedelta(days=i)
    date_str = current_date.strftime("%Y-%m-%d")      # e.g., "2025-01-01"
    day_name = current_date.strftime("%A")            # e.g., "Monday"
    display_date = current_date.strftime("%A, %d %B") 
    
    # FILTER: Find blocks that match this DATE or this DAY OF WEEK
    # This enables your "Recurring" schedule to work alongside "Specific" blocks.
    day_blocks = df_blocked[
        (df_blocked['Date'] == date_str) | 
        (df_blocked['Date'] == day_name)
    ]
    
    blocked_times = day_blocks['Time'].values
    is_fully_booked = "ALL" in blocked_times

    # Visuals: Expand first 3 days
    with st.expander(display_date, expanded=(i < 3)):
        if is_fully_booked:
            st.warning("⛔ Fully Booked / Day Off")
        else:
            cols = st.columns(3)
            for index, slot in enumerate(TIME_SLOTS):
                # If slot is in the list -> Grey Button
                if slot in blocked_times:
                    cols[index % 3].button(f"❌ {slot}", key=f"{date_str}_{slot}", disabled=True)
                else:
                    # Available -> Green Button
                    msg = f"Hi! Is the {slot} slot on {display_date} available?"
                    link = f"https://t.me/{TELEGRAM_USERNAME}"
                    cols[index % 3].link_button(f"✅ {slot}", link, type="primary")

st.divider()
st.caption("Times are shown in your local time.")
