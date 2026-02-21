import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

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

# 3. Pre-load today's existing data into session state
today_str = datetime.now().strftime("%Y-%m-%d")
if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    today_row = df[df["Date"] == today_str]
    if not today_row.empty:
        row = today_row.iloc[0]
        if 'job_count' not in st.session_state:
            st.session_state.job_count = int(float(row["Job_Apps"]))
        if 'net_count' not in st.session_state:
            st.session_state.net_count = int(float(row["Networking"]))
        if 'ex' not in st.session_state:
            st.session_state.ex = bool(int(float(row["Exercise"])))
        if 'aff' not in st.session_state:
            st.session_state.aff = bool(int(float(row["Affirmations"])))
        if 'teeth' not in st.session_state:
            st.session_state.teeth = bool(int(float(row["Teeth_Whitening"])))
        if 'budget' not in st.session_state:
            st.session_state.budget = bool(int(float(row["Budget"])))
        if 'night_aff' not in st.session_state:
            st.session_state.night_aff = bool(int(float(row["Night_Affirmations"])))

# Initialize defaults if no prior data today
for key in ['ex', 'aff', 'teeth', 'budget', 'night_aff']:
    if key not in st.session_state:
        st.session_state[key] = False
if 'job_count' not in st.session_state:
    st.session_state.job_count = 0
if 'net_count' not in st.session_state:
    st.session_state.net_count = 0

# 4. Counter callbacks
def increment_jobs(): st.session_state.job_count += 1
def increment_net(): st.session_state.net_count += 1

# 5. Sidebar Form
with st.sidebar:
    st.header("Log Activity")
    log_date = st.date_input("Date", datetime.now())

    st.subheader("Checklist")
    ex = st.checkbox("Exercise 🏋️", key="ex")
    aff = st.checkbox("Morning Affirmations ✨", key="aff")
    teeth = st.checkbox("Teeth Whitening 🦷", key="teeth")
    budget = st.checkbox("Updated Budget 💰", key="budget")
    night_aff = st.checkbox("Night Affirmations 🌙", key="night_aff")

    st.subheader("Counters")
    st.write(f"Jobs Applied: {st.session_state.job_count}")
    st.button("+1 Job App", on_click=increment_jobs)

    st.write(f"Networking Reached: {st.session_state.net_count}")
    st.button("+1 Networking", on_click=increment_net)

    if st.button("Save Daily Log"):
        date_str = log_date.strftime("%Y-%m-%d")
        new_entry = {
            "Date": date_str,
            "Exercise": int(st.session_state.ex),
            "Affirmations": int(st.session_state.aff),
            "Teeth_Whitening": int(st.session_state.teeth),
            "Job_Apps": st.session_state.job_count,
            "Networking": st.session_state.net_count,
            "Budget": int(st.session_state.budget),
            "Night_Affirmations": int(st.session_state.night_aff)
        }

        # Ensure date column is string formatted for comparison
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        if date_str in df["Date"].values:
            # Update existing row
            idx = df.index[df["Date"] == date_str][0]
            for key, val in new_entry.items():
                df.at[idx, key] = val
            updated_df = df
        else:
            # Append new row
            updated_df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

        conn.update(worksheet="Sheet1", data=updated_df)
        st.success("✅ Saved!")
        st.rerun()

# 6. Dashboard
st.subheader("Your Progress")

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date', ascending=False)

    # Top metrics
    cols = st.columns(4)
    latest = df.iloc[0]
    cols[0].metric("Last Log Date", str(latest['Date'].date()))
    cols[1].metric("Jobs Applied (last)", int(float(latest['Job_Apps'])))
    cols[2].metric("Networking (last)", int(float(latest['Networking'])))

    # Streak calculation for exercise (example)
    df_sorted = df.sort_values('Date', ascending=False).reset_index(drop=True)
    streak = 0
    for i, row in df_sorted.iterrows():
        if int(float(row['Exercise'])) == 1:
            streak += 1
        else:
            break
    cols[3].metric("Exercise Streak 🔥", f"{streak} days")

    # Cumulative job apps
    st.divider()
    st.write("### 📈 Cumulative Job Applications")
    df_chart = df.sort_values('Date')
    df_chart['Cumulative_Jobs'] = df_chart['Job_Apps'].astype(float).cumsum()
    st.line_chart(df_chart.set_index('Date')['Cumulative_Jobs'])

    # Consistency table
    st.divider()
    st.write("### 📅 Consistency View")
    display_df = df.set_index('Date').copy()
    # Convert 1/0 to ✅/❌ for readability
    bool_cols = ["Exercise", "Affirmations", "Teeth_Whitening", "Budget", "Night_Affirmations"]
    for col in bool_cols:
        display_df[col] = display_df[col].apply(lambda x: "✅" if int(float(x)) == 1 else "❌")
    st.dataframe(display_df, use_container_width=True)

else:
    st.info("Start logging to see your progress!")