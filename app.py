import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- SETTINGS ---
TELEGRAM_USERNAME = "apl450"  # <--- REMEMBER TO PUT YOUR USERNAME HERE!
PAGE_TITLE = "Lesson Slots"
PAGE_ICON = ""

# The Grid
TIME_SLOTS = [
    "10:15", "11:30", "12:45", 
    "14:00", "15:15", "16:30", 
    "17:45", "19:00", "20:15"
]

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")

# --- CUSTOM CSS FOR BEAUTIFICATION ---
st.markdown("""
    <style>
    /* Make buttons look like modern pills */
    .stButton button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        font-weight: 600;
        border: 1px solid #e0e0e0;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        border-color: #00D26A;
        color: #00D26A;
        background-color: #e8f5e9;
        transform: scale(1.02);
    }
    /* Card Header */
    .day-header {
        font-size: 1.2rem;
        font-weight: 700;
        color: #333;
        margin-bottom: 8px;
        border-bottom: 2px solid #f0f2f6;
        padding-bottom: 5px;
    }
    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .badge-closed { background-color: #ffebee; color: #c62828; }
    .badge-open { background-color: #e8f5e9; color: #2e7d32; }
    </style>
""", unsafe_allow_html=True)

# --- ROBUST DATA LOADER ---
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
        
        # 3. Clean Data
        if 'Date' in df.columns: df['Date'] = df['Date'].astype(str).str.strip()
        if 'Time' in df.columns: df['Time'] = df['Time'].astype(str).str.strip()
            
        # 4. Ensure Status exists & is Uppercase
        if 'Status' not in df.columns:
            if len(df.columns) >= 3:
                 df.rename(columns={df.columns[2]: "Status"}, inplace=True)
            else:
                 df['Status'] = "Busy"
        
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

# Header
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown(f"<h1 style='text-align: center; font-size: 3rem;'>{PAGE_ICON}</h1>", unsafe_allow_html=True)
with col2:
    st.title(PAGE_TITLE)
    st.caption("Book your next lesson instantly on Telegram.")

st.divider()

today = datetime.now().date()

# Loop 14 Days
for i in range(14):
    current_date = today + timedelta(days=i)
    date_str = current_date.strftime("%Y-%m-%d") 
    day_name = current_date.strftime("%A")       
    display_date = current_date.strftime("%A, %d %B")
    
    # 1. FILTER: Find all rules for this Date AND this Day-of-Week
    specific_blocks = df_all[df_all['Date'] == date_str]
    recurring_blocks = df_all[df_all['Date'] == day_name]

    # 2. LOGIC: Determine Day Status
    # CRITICAL FIX: We look for "ALL" rows and check if ANY of them say "OPEN".
    # This ensures "OPEN" overrides any "Blocked" rows.
    
    specific_all_rows = specific_blocks[specific_blocks['Time'] == 'ALL']
    
    force_day_open = False
    is_day_blocked = False

    # Check Specific Date Rules First
    if not specific_all_rows.empty:
        if specific_all_rows['Status'].str.contains("OPEN").any():
            force_day_open = True  # Found a "Master Key" -> Day is OPEN!
        else:
            is_day_blocked = True  # Found a specific block (like Holiday)
    
    # If no specific "Open" command, check if it's a recurring weekend
    if not force_day_open:
        if "ALL" in recurring_blocks['Time'].values:
            is_day_blocked = True

    # 3. DRAW UI (Using Cards)
    # We use st.container with border=True to create the "Card" look
    with st.container(border=True):
        st.markdown(f"<div class='day-header'>{display_date}</div>", unsafe_allow_html=True)
        
        # If blocked and NOT forced open -> Show Red Badge
        if is_day_blocked and not force_day_open:
            st.markdown(f"<div class='status-badge badge-closed'>⛔ Day Off</div>", unsafe_allow_html=True)
        else:
            # Show Slots
            cols = st.columns(3)
            for index, slot in enumerate(TIME_SLOTS):
                
                is_available = True 
                
                # Check Specific Slot Override (e.g. 14:00)
                slot_specific = specific_blocks[specific_blocks['Time'] == slot]
                
                if not slot_specific.empty:
                    # If ANY row for this slot says OPEN, it is available.
                    if slot_specific['Status'].str.contains("OPEN").any():
                        is_available = True
                    else:
                        is_available = False
                
                # If day is forced open, everything is available (unless blocked above)
                elif force_day_open:
                    is_available = True
                    
                else:
                    # Apply Recurring Rules
                    if slot in recurring_blocks['Time'].values:
                        is_available = False
                    if is_day_blocked:
                        is_available = False

                # Render Button
                if is_available:
                    msg = f"Hi! Is the {slot} slot on {display_date} available?"
                    link = f"https://t.me/{TELEGRAM_USERNAME}"
                    cols[index % 3].link_button(f"{slot}", link, type="primary", use_container_width=True)
                else:
                    # Greyed out button
                    cols[index % 3].button(f"✕", key=f"{date_str}_{slot}", disabled=True, use_container_width=True)
