import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Personal Habit Tracker", layout="wide")
st.title("🚀 Daily Growth Tracker")

# 1. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Fetch data
try:
    df = conn.read(worksheet="Sheet1", ttl=0)
    df = df.dropna(how="all")
except:
    df = pd.DataFrame(columns=["Date", "Exercise", "Affirmations", "Teeth_Whitening", "Job_Apps", "Networking", "Budget", "Night_Affirmations"])

# 3. Increment Logic for Job Apps & Networking
if 'job_count' not in st.session_state: st.session_state.job_count = 0
if 'net_count' not in st.session_state: st.session_state.net_count = 0

def increment_jobs(): st.session_state.job_count += 1
def increment_net(): st.session_state.net_count += 1

# 4. Entry Form
with st.sidebar:
    st.header("Log Activity")
    log_date = st.date_input("Date", datetime.now())
    
    st.subheader("Checklist")
    ex = st.checkbox("Exercise 🏋️")
    aff = st.checkbox("Morning Affirmations ✨")
    teeth = st.checkbox("Teeth Whitening 🦷")
    budget = st.checkbox("Updated Budget 💰")
    night_aff = st.checkbox("Night Affirmations 🌙")
    
    st.subheader("Counters")
    st.write(f"Jobs Applied: {st.session_state.job_count}")
    st.button("+1 Job App", on_click=increment_jobs)
    
    st.write(f"Networking Reached: {st.session_state.net_count}")
    st.button("+1 Networking", on_click=increment_net)

    if st.button("Save Daily Log"):
        date_str = log_date.strftime("%Y-%m-%d")
        new_entry = {
            "Date": date_str,
            "Exercise": ex, "Affirmations": aff, "Teeth_Whitening": teeth,
            "Job_Apps": st.session_state.job_count, 
            "Networking": st.session_state.net_count,
            "Budget": budget, "Night_Affirmations": night_aff
        }

        # Normalize dates for comparison
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        
        if date_str in df["Date"].values:
            # Update existing row for that date
            idx = df.index[df["Date"] == date_str][0]
            for key, val in new_entry.items():
                df.at[idx, key] = val
            updated_df = df
        else:
            # Append new row
            updated_df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

        conn.update(worksheet="Sheet1", data=updated_df)
        st.session_state.job_count = 0
        st.session_state.net_count = 0
        st.success("Saved!")
        st.rerun()
# 5. Dashboard & Streaks
st.subheader("Your Progress")

if not df.empty:
    # Streak Calculation Logic (Simplified)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date', ascending=False)
    
    # Show Yesterday/Today's snapshot
    cols = st.columns(4)
    latest = df.iloc[0]
    cols[0].metric("Last Log Date", str(latest['Date'].date()))
    cols[1].metric("Last Job Count", int(latest['Job_Apps']))
    cols[2].metric("Networking", int(latest['Networking']))
    
    # Visualizing Boolean Habits
    st.divider()
    st.write("### Consistency View")
    st.dataframe(df.set_index('Date'), use_container_width=True)
else:
    st.info("Start logging to see your streaks!")