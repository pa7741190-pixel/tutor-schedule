import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import quote

# --- SETTINGS ---
TELEGRAM_USERNAME = "apl450"  # <--- PUT YOUR USERNAME HERE (No @ symbol)
PAGE_TITLE = "English Lesson Slots"
PAGE_ICON = ""

# The Grid
TIME_SLOTS = [
    "10:15", "11:30", "12:45", 
    "14:00", "15:15", "16:30", 
    "17:45", "19:00", "20:15"
]

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")

# --- CUSTOM CSS (BEAUTIFICATION) ---
st.markdown("""
    <style>
    /* Modern Button Style */
    .stLinkButton a {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        text-align: center;
        border: 1px solid #4CAF50;
        color: #4CAF50 !important;
        background-color: white;
        transition: all 0.2s;
        text-decoration: none;
        display: block;
        padding: 0.5rem;
    }
    .stLinkButton a:hover {
        background-color: #4CAF50;
        color: white !important;
    }
    /* Disable "X" buttons */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #eee;
        color: #ccc;
        background-color: #f9f9f9;
        cursor: not-allowed;
    }
    /* Card Header */
    .day-header {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #333;
    }
    /* Status Labels */
    .status-closed { color: #d32f2f; font-weight: 600; font-size: 0.9rem; }
    .status-extra { color: #2e7d32; font-weight: 600; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# --- SMART DATA LOADER ---
@st.cache_data(ttl=60)
def load_data(url):
    try:
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv")
        csv_url = csv_url.replace("/edit#gid=", "/export?format=csv&gid=")
        
        # Read nicely with error skipping
        df = pd.read_csv(csv_url, engine='python', on_bad_lines='skip')
        
        # 1. AUTO-FIX: Split columns if they are stuck together
        if len(df.columns) == 1:
            col_name = df.columns[0]
            df_split = df[col_name].astype(str).str.split(',', expand=True)
            if "Date" in col_name:
                headers = col_name.split(',')
                if len(headers) == df_split.shape[1]:
                    df_split.columns = [h.strip() for h in headers]
            df = df_split

        # 2. Clean Headers
        df.columns = [c.strip() for c in df.columns]
        if 'Day_or_Date' in df.columns: df = df.rename(columns={'Day_or_Date': 'Date'})
        
        # 3. Clean Data & Status
        if 'Date' in df.columns: df['Date'] = df['Date'].astype(str).str.strip()
        if 'Time' in df.columns: df['Time'] = df['Time'].astype(str).str.strip()
            
        if 'Status' not in df.columns:
            if len(df.columns) >= 3:
                 df.rename(columns={df.columns[2]: "Status"}, inplace=True)
            else:
                 df['Status'] = "Busy"
        df['Status'] = df['Status'].astype(str).str.strip().str.upper()

        # 4. DATE CLEANER (This fixes the "Saturday 3rd" bug)
        # Google Sheets might send "1/3/2026", but we need "2026-01-03"
        def clean_date_format(val):
            val = str(val).strip()
            # If it looks like a date (has numbers), force format YYYY-MM-DD
            if any(char.isdigit() for char in val):
                try:
                    return pd.to_datetime(val, dayfirst=False).strftime("%Y-%m-%d")
                except:
                    # Try dayfirst if the above fails
                    try:
                         return pd.to_datetime(val, dayfirst=True).strftime("%Y-%m-%d")
                    except:
                         return val
            # If it's just "Monday", capitalize it and leave it
            return val.title()
            
        df['Date'] = df['Date'].apply(clean_date_format)

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

# Header
st.markdown(f"""
    <div style='text-align: center; padding: 20px 0;'>
        <div style='font-size: 3rem;'>{PAGE_ICON}</div>
        <h1 style='margin:0;'>{PAGE_TITLE}</h1>
        <p style='color: #666;'>Tap a green slot to book it on Telegram.</p>
    </div>
""", unsafe_allow_html=True)

today = datetime.now().date()

# Loop 14 Days
for i in range(14):
    current_date = today + timedelta(days=i)
    date_str = current_date.strftime("%Y-%m-%d") 
    day_name = current_date.strftime("%A")       
    display_date = current_date.strftime("%A, %d %B")
    
    # 1. FIND RULES
    specific_blocks = df_all[df_all['Date'] == date_str]
    recurring_blocks = df_all[df_all['Date'] == day_name]

    # 2. DETERMINE STATUS
    force_day_open = False
    is_day_blocked = False

    # Check for "ALL | OPEN" override
    specific_all = specific_blocks[specific_blocks['Time'] == 'ALL']
    if not specific_all.empty:
        if specific_all['Status'].str.contains("OPEN").any():
            force_day_open = True
        else:
            is_day_blocked = True
    
    # If no override, check recurring schedule
    if not force_day_open:
        if "ALL" in recurring_blocks['Time'].values:
            is_day_blocked = True

    # 3. DRAW CARD
    with st.container(border=True):
        col_head, col_status = st.columns([3, 1])
        col_head.markdown(f"<div class='day-header'>{display_date}</div>", unsafe_allow_html=True)
        
        if is_day_blocked and not force_day_open:
            col_status.markdown("<div class='status-closed'>⛔ Day Off</div>", unsafe_allow_html=True)
        else:
            if force_day_open:
                col_status.markdown("<div class='status-extra'>✨ Open</div>", unsafe_allow_html=True)
                
            # Show Slots
            cols = st.columns(3)
            for index, slot in enumerate(TIME_SLOTS):
                
                is_available = True 
                
                # Check Specific Slot (e.g. 14:00)
                slot_specific = specific_blocks[specific_blocks['Time'] == slot]
                
                if not slot_specific.empty:
                    if slot_specific['Status'].str.contains("OPEN").any():
                        is_available = True
                    else:
                        is_available = False
                elif force_day_open:
                    is_available = True
                else:
                    if slot in recurring_blocks['Time'].values:
                        is_available = False
                    if is_day_blocked:
                        is_available = False

                # RENDER BUTTON
                if is_available:
                    # THE FIX: Add ?text=... to the URL so it appears in the input box
                    msg = f"Hi! Is the {slot} slot on {display_date} available?"
                    safe_msg = quote(msg)
                    link = f"https://t.me/{TELEGRAM_USERNAME}?text={safe_msg}"
                    
                    cols[index % 3].link_button(f"{slot}", link, type="primary", use_container_width=True)
                else:
                    cols[index % 3].button(f"✕", key=f"{date_str}_{slot}", disabled=True, use_container_width=True)
