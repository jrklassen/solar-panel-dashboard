import streamlit as st
import socket
import time
from datetime import datetime

# --- CONFIG ---
# This looks for a secret called 'ECU_IP', otherwise defaults to 192.168.86.100
ECU_IP = st.secrets.get("ECU_IP", "192.168.86.100")
PORT = int(st.secrets.get("PORT", 8899))
DATA_COMMAND = b'APS1100160001END\n'
REFRESH_RATE = 120

# --- DATA LOGIC ---
@st.cache_data(ttl=REFRESH_RATE)
def get_solar_data():
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((ECU_IP, PORT))
        s.sendall(DATA_COMMAND)
        resp = s.recv(1024)
        s.close()

        if resp and len(resp) >= 112:
            # SUCCESS MAPPING:
            # Total Power (Watts) is at index 31-34
            # Today's Yield (kWh) is at index 35-38
            watts_raw = int.from_bytes(resp[31:35], byteorder='big')
            daily_raw = int.from_bytes(resp[35:39], byteorder='big')
            
            # Apply your specific manor calibration
            live_watts = int(watts_raw * 1.075)
            daily_kwh = round(daily_raw / 100, 2)
            
            return {
                "watts": live_watts, 
                "daily": daily_kwh, 
                "time": datetime.now().strftime('%H:%M:%S')
            }
    except Exception as e:
        if s: s.close()
    return None

# --- UI SETUP ---
st.set_page_config(page_title="Staffordshire Manor Solar", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] { font-size: 52px; color: #00d4ff; font-weight: 800; }
    .stProgress > div > div > div > div { background-color: #00d4ff; }
    </style>
    """, unsafe_allow_html=True)

if "peak_watts" not in st.session_state: 
    st.session_state.peak_watts = 0

st.title("🏰 Staffordshire Manor Solar Array")
st.divider()

@st.fragment(run_every=REFRESH_RATE)
def update_dashboard():
    # 1. Fetch Data
    data = get_solar_data()

    if data:
        # Update Peak Power Record
        if data['watts'] > st.session_state.peak_watts:
            st.session_state.peak_watts = data['watts']
            
        # 2. Main Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Production", f"{data['watts']} W")
        col2.metric("Today's Yield", f"{data['daily']} kWh")
        col3.metric("Peak Power Today", f"{st.session_state.peak_watts} W")
        
        st.divider()
        
        # 3. Goal Progress
        goal = 20.0
        prog = min(data['daily'] / goal, 1.0)
        st.write(f"**Daily Goal Progress** ({int(prog*100)}%) — {data['daily']} of {goal} kWh")
        st.progress(prog)
        
        st.caption(f"🛡️ Wi-Fi Connection Active | Last Sync: {data['time']}")
    else:
        st.error("🔄 ECU is processing data... syncing.")
        if st.button("Manual Refresh"):
            st.cache_data.clear()
            st.rerun()

update_dashboard()