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

# --- SMART DATA LOADER ---
@st.cache_data(ttl=60)
def load_data(url):
    try:
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv")
        csv_url = csv_url.replace("/edit#gid=", "/export?format=csv&gid=")
        
        # engine='python' prevents the Segmentation Fault crash
        # on_bad_lines='skip' prevents crashes if a row is messy
        df = pd.read_csv(csv_url, engine='python', on_bad_lines='skip')
        
        # AUTO-FIX: If data is stuck in one column (User didn't split text)
        if len(df.columns) == 1:
            col_name = df.columns[0]
            # Split by comma
            df_split = df[col_name].astype(str).str.split(',', expand=True)
            
            # Try to fix headers if they are trapped in the first row
            if "Date" in col_name:
                headers = col_name.split(',')
                if len(headers) == df_split.shape[1]:
                    df_split.columns = [h.strip() for h in headers]
            
            df = df_split

        # Clean column names (remove spaces)
        df.columns = [c.strip() for c in df.columns]
        
        # Rename old "Day_or_Date" to "Date" if present
        if 'Day_or_Date' in df.columns:
            df = df.rename(columns={'Day_or_Date': 'Date'})
            
        # Standardize Text
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str).str.strip()
        if 'Time' in df.columns:
            df['Time'] = df['Time'].astype(str).str.strip()
            
        # Ensure 'Status' column exists
        if 'Status' not in df.columns:
            if len(df.columns) >= 3:
                 # Assume 3rd column is Status if it exists
                 df.rename(columns={df.columns[2]: "Status"}, inplace=True)
            else:
                 df['Status'] = "Busy"
        
        # Clean Status text
        df['Status'] = df['Status'].astype(str).str.strip()

        return df
    except Exception:
        # Return empty table instead of crashing
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

# Loop 14 days
for i in range(14):
    current_date = today + timedelta(days=i)
    date_str = current_date.strftime("%Y-%m-%d") 
    day_name = current_date.strftime("%A")       
    display_date = current_date.strftime("%A, %d %B")
    
    # 1. Get rules for this specific Date
    specific_blocks = df_all[df_all['Date'] == date_str]
    # 2. Get rules for this Day of Week
    recurring_blocks = df_all[df_all['Date'] == day_name]

    # Check if Day is globally blocked
    day_off_recurring = "ALL" in recurring_blocks['Time'].values
    day_off_specific = "ALL" in specific_blocks['Time'].values
    
    # Check if we have a forced "OPEN" override
    has_forced_open = False
    if 'Status' in specific_blocks.columns:
        has_forced_open = specific_blocks['Status'].str.upper().str.contains("OPEN").any()
    
    with st.expander(display_date, expanded=(i < 3)):
        # If day is blocked AND no manual "OPEN" overrides exist -> Warning
        if (day_off_specific or day_off_recurring) and not has_forced_open:
            st.warning("⛔ Day Off")
        else:
            cols = st.columns(3)
            for index, slot in enumerate(TIME_SLOTS):
                
                is_available = True 
                
                # Check Specific Date Override
                slot_specific = specific_blocks[specific_blocks['Time'] == slot]
                
                if not slot_specific.empty:
                    status = slot_specific.iloc[0]['Status'].upper()
                    if "OPEN" in status:
                        is_available = True
                    else:
                        is_available = False
                
                # Check Recurring Rules
                else:
                    if slot in recurring_blocks['Time'].values:
                        is_available = False
                    if day_off_recurring or day_off_specific:
                        is_available = False

                if is_available:
                    msg = f"Hi! Is the {slot} slot on {display_date} available?"
                    link = f"https://t.me/{TELEGRAM_USERNAME}"
                    cols[index % 3].link_button(f"✅ {slot}", link, type="primary")
                else:
                    cols[index % 3].button(f"❌ {slot}", key=f"{date_str}_{slot}", disabled=True)

st.divider()
