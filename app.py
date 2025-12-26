import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- SETTINGS ---
# Replace this with your actual Telegram username so students can message you!
TELEGRAM_USERNAME = "apl450" 
PAGE_TITLE = "🇬🇧 English Lesson Slots"

# Your specific time grid (60m lesson + 15m break)
# Starts 10:15, Ends with the 20:15 slot
TIME_SLOTS = [
    "10:15", "11:30", "12:45", 
    "14:00", "15:15", "16:30", 
    "17:45", "19:00", "20:15"
]

st.set_page_config(page_title=PAGE_TITLE, page_icon="📅")

# --- LOAD DATA FROM GOOGLE SHEET ---
@st.cache_data(ttl=60) # Updates every 60 seconds
def load_data(url):
    try:
        # Convert standard Google Sheet URL to a CSV export URL
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv")
        csv_url = csv_url.replace("/edit#gid=", "/export?format=csv&gid=")
        return pd.read_csv(csv_url)
    except Exception:
        return pd.DataFrame(columns=["Date", "Time"])

# Get the secret URL from Streamlit settings
sheet_url = st.secrets["public_sheet_url"]
df_blocked = load_data(sheet_url)

# --- APP INTERFACE ---
st.title(PAGE_TITLE)
st.write("Here are my available slots for the next 2 weeks.")
st.write("Click a time to book it via Telegram.")
st.divider()

# Get today's date
today = datetime.now().date()

# Loop through the next 14 days
for i in range(14):
    current_date = today + timedelta(days=i)
    date_str = current_date.strftime("%Y-%m-%d") # Format for code: 2024-01-01
    display_date = current_date.strftime("%A, %d %B") # Format for humans: Monday, 01 January
    
    # Check your Google Sheet for blocks on this day
    day_blocks = df_blocked[df_blocked['Date'] == date_str]
    is_whole_day_blocked = "ALL" in day_blocks['Time'].values

    # Draw the day
    # We expand the first 3 days so they are visible, collapse the rest
    with st.expander(display_date, expanded=(i < 3)):
        if is_whole_day_blocked:
            st.warning("⛔ Fully Booked / Day Off")
        else:
            # Create a grid of buttons (3 per row)
            cols = st.columns(3)
            for index, slot in enumerate(TIME_SLOTS):
                # Check if this specific slot is blocked in the sheet
                is_slot_blocked = slot in day_blocks['Time'].values
                
                col = cols[index % 3]
                
                if is_slot_blocked:
                    # Show a grey button that does nothing
                    col.button(f"❌ {slot}", key=f"btn_{date_str}_{slot}", disabled=True)
                else:
                    # Show a GREEN button that opens Telegram
                    msg = f"Hi! Is the {slot} slot on {display_date} available?"
                    # This creates a link to open Telegram with the message pre-filled
                    link = f"https://t.me/{TELEGRAM_USERNAME}?start={msg}"
                    # Note: Direct deep linking with text varies by device, 
                    # simple link is safer:
                    link = f"https://t.me/{TELEGRAM_USERNAME}"
                    
                    col.link_button(f"✅ {slot}", link, type="primary")

st.divider()
st.caption("Updates automatically from Tutor's Schedule")
