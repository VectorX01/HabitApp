import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Habit Accountability Log", layout="wide")
st.title("Habit Accountability Log")

# ---------------------------------------------------------------------------
# 1. Habit configuration
#    type "bool"  -> daily yes/no checkbox
#    type "count" -> daily counter (e.g. how many job apps sent today)
#    weekly_target -> for bool: days/week required. for count: total sum/week
#                      required.
#    daily_target  -> count habits only. minimum count that counts the day as
#                      "done" for streak/miss purposes (default: any count > 0).
# ---------------------------------------------------------------------------
HABITS = {
    "Say_Affirmations":       {"label": "Say Affirmations",        "emoji": "🗣️", "type": "bool",  "weekly_target": 7},
    "Gym":                    {"label": "Gym",                     "emoji": "🏋️", "type": "bool",  "weekly_target": 6},
    "Interview_Prep":         {"label": "Interview Prep",          "emoji": "🎯", "type": "bool",  "weekly_target": 7},
    "Brain_Teasers":          {"label": "Brain Teasers",           "emoji": "🧩", "type": "bool",  "weekly_target": 7},
    "Coding":                 {"label": "Coding",                  "emoji": "💻", "type": "bool",  "weekly_target": 7},
    "Evening_Run":            {"label": "Evening Run",             "emoji": "🏃", "type": "bool",  "weekly_target": 6},
    "Job_Applications":       {"label": "Job Applications",        "emoji": "📄", "type": "count", "weekly_target": 70, "daily_target": 10},
    "Communication_Practice": {"label": "Communication Practice",  "emoji": "🎤", "type": "bool",  "weekly_target": 7},
    "Networking":             {"label": "Networking",              "emoji": "🤝", "type": "count", "weekly_target": 5},
    "Write_Affirmations":     {"label": "Write Affirmations",      "emoji": "✍️", "type": "bool",  "weekly_target": 7},
    "Teeth_Care_Night":       {"label": "Teeth Care @ Night",      "emoji": "🦷", "type": "bool",  "weekly_target": 7},
    "Skin_Care_Night":        {"label": "Skin Care @ Night",       "emoji": "🧴", "type": "bool",  "weekly_target": 7},
}
HABIT_KEYS = list(HABITS.keys())
BOOL_HABITS = [k for k, v in HABITS.items() if v["type"] == "bool"]
COUNT_HABITS = [k for k, v in HABITS.items() if v["type"] == "count"]
ALL_COLUMNS = ["Date"] + HABIT_KEYS

# ---------------------------------------------------------------------------
# 2. Connect to Google Sheets & load data
# ---------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(worksheet="Sheet1", ttl=0)
    df = df.dropna(how="all")
    # Make sure every habit column exists even if the sheet predates it
    for col in ALL_COLUMNS:
        if col not in df.columns:
            df[col] = 0
    df = df[ALL_COLUMNS]
except Exception:
    df = pd.DataFrame(columns=ALL_COLUMNS)

if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")


def as_number(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# 3. Pre-load today's existing data into session state
# ---------------------------------------------------------------------------
today_str = datetime.now().strftime("%Y-%m-%d")
today_row = df[df["Date"] == today_str] if not df.empty else pd.DataFrame()

for key in HABIT_KEYS:
    state_key = f"chk_{key}" if HABITS[key]["type"] == "bool" else f"cnt_{key}"
    if state_key not in st.session_state:
        if not today_row.empty:
            val = as_number(today_row.iloc[0][key])
            st.session_state[state_key] = bool(int(val)) if HABITS[key]["type"] == "bool" else int(val)
        else:
            st.session_state[state_key] = False if HABITS[key]["type"] == "bool" else 0


def increment(key):
    st.session_state[f"cnt_{key}"] += 1


def decrement(key):
    if st.session_state[f"cnt_{key}"] > 0:
        st.session_state[f"cnt_{key}"] -= 1


# ---------------------------------------------------------------------------
# 4. Sidebar - daily log form
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Log Today's Activity")
    log_date = st.date_input("Date", datetime.now())

    st.subheader("Checklist")
    for key in BOOL_HABITS:
        st.checkbox(f"{HABITS[key]['emoji']} {HABITS[key]['label']}", key=f"chk_{key}")

    st.subheader("Counters")
    for key in COUNT_HABITS:
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.write(f"{HABITS[key]['emoji']} {HABITS[key]['label']}: **{st.session_state[f'cnt_{key}']}**")
        c2.button("+1", key=f"inc_{key}", on_click=increment, args=(key,))
        c3.button("-1", key=f"dec_{key}", on_click=decrement, args=(key,))

    if st.button("💾 Save Daily Log", use_container_width=True):
        date_str = log_date.strftime("%Y-%m-%d")
        new_entry = {"Date": date_str}
        for key in HABIT_KEYS:
            if HABITS[key]["type"] == "bool":
                new_entry[key] = int(st.session_state[f"chk_{key}"])
            else:
                new_entry[key] = st.session_state[f"cnt_{key}"]

        if df.empty:
            updated_df = pd.DataFrame([new_entry])
        elif date_str in df["Date"].values:
            idx = df.index[df["Date"] == date_str][0]
            for k, v in new_entry.items():
                df.at[idx, k] = v
            updated_df = df
        else:
            updated_df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

        conn.update(worksheet="Sheet1", data=updated_df)
        st.success("✅ Saved!")
        st.rerun()

# ---------------------------------------------------------------------------
# 5. Streak calculations
# ---------------------------------------------------------------------------
def is_done(value, key):
    habit = HABITS[key]
    v = as_number(value)
    if habit["type"] == "count":
        daily_target = habit.get("daily_target")
        return v >= daily_target if daily_target else v > 0
    return int(v) == 1


def current_streak(data, key):
    """Consecutive days up to the most recent log where the habit was done."""
    if data.empty:
        return 0
    d = data.copy()
    d["Date"] = pd.to_datetime(d["Date"])
    d = d.sort_values("Date", ascending=False)
    streak = 0
    expected_date = None
    for _, row in d.iterrows():
        row_date = row["Date"].normalize()
        if expected_date is None:
            expected_date = row_date
        if row_date != expected_date:
            break
        if not is_done(row[key], key):
            break
        streak += 1
        expected_date = expected_date - timedelta(days=1)
    return streak


def best_streak(data, key):
    """Longest run of consecutive calendar days the habit was done."""
    if data.empty:
        return 0
    d = data.copy()
    d["Date"] = pd.to_datetime(d["Date"])
    d = d.sort_values("Date")
    best = 0
    current = 0
    prev_date = None
    for _, row in d.iterrows():
        row_date = row["Date"].normalize()
        if is_done(row[key], key):
            if prev_date is not None and (row_date - prev_date).days == 1:
                current += 1
            else:
                current = 1
            best = max(best, current)
        else:
            current = 0
        prev_date = row_date
    return best


def week_progress(data, key, week_start, today):
    if data.empty:
        return 0
    d = data.copy()
    d["Date"] = pd.to_datetime(d["Date"])
    week_df = d[(d["Date"] >= pd.Timestamp(week_start)) & (d["Date"] <= pd.Timestamp(today))]
    if HABITS[key]["type"] == "bool":
        return sum(is_done(v, key) for v in week_df[key])
    return sum(as_number(v) for v in week_df[key])


def build_miss_log(data, today, days=30):
    """Every habit not done on a given day is a miss. A day with no log at
    all counts as a miss for every habit — no log means nothing got done."""
    if data.empty:
        return pd.DataFrame(columns=["Date", "Habit_Key", "Habit"])
    d = data.copy()
    d["Date"] = pd.to_datetime(d["Date"])
    first_log = d["Date"].min().normalize().date()
    start = max(today - timedelta(days=days - 1), first_log)
    lookup = d.set_index(d["Date"].dt.strftime("%Y-%m-%d"))
    rows = []
    for dt in pd.date_range(start, today, freq="D"):
        date_str = dt.strftime("%Y-%m-%d")
        row = lookup.loc[date_str] if date_str in lookup.index else None
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        for k in HABIT_KEYS:
            done = is_done(row[k], k) if row is not None else False
            if not done:
                rows.append({"Date": date_str, "Habit_Key": k, "Habit": HABITS[k]["label"]})
    return pd.DataFrame(rows, columns=["Date", "Habit_Key", "Habit"])


streaks = {key: {"current": current_streak(df, key), "best": best_streak(df, key)} for key in HABIT_KEYS}

if not today_row.empty:
    done_today_map = {k: is_done(today_row.iloc[0][k], k) for k in HABIT_KEYS}
else:
    done_today_map = {
        k: (st.session_state[f"chk_{k}"] if HABITS[k]["type"] == "bool" else st.session_state[f"cnt_{k}"] > 0)
        for k in HABIT_KEYS
    }

today_date = datetime.now().date()
week_start = today_date - timedelta(days=today_date.weekday())
days_elapsed = (today_date - week_start).days + 1
days_left = 7 - days_elapsed

not_done_before_today = df[df["Date"] != today_str] if not df.empty else df
at_risk = {
    k: current_streak(not_done_before_today, k)
    for k in HABIT_KEYS
    if not done_today_map[k] and current_streak(not_done_before_today, k) > 0
}

miss_log = build_miss_log(df, today_date, days=30)
miss_counts_30d = miss_log["Habit_Key"].value_counts().to_dict() if not miss_log.empty else {}

# ---------------------------------------------------------------------------
# 6. Dashboard
# ---------------------------------------------------------------------------
if at_risk:
    lines = "  \n".join(f"**{HABITS[k]['label']}** — {v} day streak, not logged today" for k, v in at_risk.items())
    st.error("STREAKS AT RISK TODAY — log these before the day ends:  \n" + lines)

st.subheader("Today's Status")
today_done = sum(done_today_map.values())
m1, m2, m3, m4 = st.columns(4)
m1.metric("Completed Today", f"{today_done}/{len(HABIT_KEYS)}")
m2.metric("Total Days Logged", len(df) if not df.empty else 0)
m3.metric("Misses (last 30d)", len(miss_log))
m4.metric("Streaks at Risk", len(at_risk))

st.divider()
st.write("### 🎯 Weekly Commitment")
st.caption(f"Week of {week_start.strftime('%b %d')} — day {days_elapsed} of 7, {days_left} left.")
cols = st.columns(3)
for i, key in enumerate(HABIT_KEYS):
    habit = HABITS[key]
    target = habit["weekly_target"]
    progress = week_progress(df, key, week_start, today_date)
    remaining = max(target - progress, 0)
    if remaining <= 0:
        status, color = "TARGET HIT", "off"
    elif habit["type"] == "bool" and remaining > days_left:
        status, color = "TARGET MISSED THIS WEEK", "inverse"
    else:
        status, color = f"NEEDS {remaining:g} MORE", "inverse"
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{habit['emoji']} {habit['label']}**")
            st.write(f"{progress:g}/{target:g} this week")
            st.badge(status, color="green" if color == "off" else "red")

st.divider()
st.write("### 📋 Streaks & Misses")
cols = st.columns(3)
for i, key in enumerate(HABIT_KEYS):
    habit = HABITS[key]
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{habit['emoji']} {habit['label']}**")
            if habit["type"] == "count":
                today_val = int(as_number(today_row.iloc[0][key])) if not today_row.empty else st.session_state[f"cnt_{key}"]
                daily_target = habit.get("daily_target")
                if daily_target:
                    st.write(f"Today: **{today_val}/{daily_target}** — " + ("Done" if done_today_map[key] else "NOT DONE"))
                else:
                    st.write(f"Today: **{today_val}**")
            else:
                st.write("Today: " + ("Done" if done_today_map[key] else "NOT DONE"))
            st.write(f"Current streak: {streaks[key]['current']} days (best: {streaks[key]['best']})")
            st.caption(f"Misses in last 30 days: {miss_counts_30d.get(key, 0)}")

st.divider()
st.write("### 🧾 Miss Log — last 30 days, nothing hidden")
if not miss_log.empty:
    st.dataframe(
        miss_log[["Date", "Habit"]].sort_values("Date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.write("No misses logged yet.")

# ---------------------------------------------------------------------------
# 7. Charts & accounting views
# ---------------------------------------------------------------------------
if not df.empty:
    df_chart = df.copy()
    df_chart["Date"] = pd.to_datetime(df_chart["Date"])
    df_chart = df_chart.sort_values("Date")

    st.divider()
    st.write("### 📈 Cumulative Job Applications & Networking")
    for key in COUNT_HABITS:
        df_chart[f"Cumulative_{key}"] = df_chart[key].apply(as_number).cumsum()
    st.line_chart(df_chart.set_index("Date")[[f"Cumulative_{k}" for k in COUNT_HABITS]])

    st.divider()
    st.write("### 🗓️ Last 30 Days")
    last_30 = pd.DataFrame({"Date": [datetime.now().date() - timedelta(days=i) for i in range(29, -1, -1)]})
    last_30["Date_str"] = last_30["Date"].apply(lambda d: d.strftime("%Y-%m-%d"))
    df_lookup = df.set_index("Date")

    def day_pct(date_str):
        if date_str not in df_lookup.index:
            return None
        row = df_lookup.loc[date_str]
        done = sum(is_done(row[k], k) for k in HABIT_KEYS)
        return done / len(HABIT_KEYS)

    def color_for(pct):
        if pct is None:
            return "#2b2b2b"
        if pct == 0:
            return "#5c1a1a"
        if pct < 0.5:
            return "#8a5a1a"
        if pct < 1:
            return "#3d7a3d"
        return "#1fa11f"

    heat_cols = st.columns(30)
    for i, row in last_30.iterrows():
        pct = day_pct(row["Date_str"])
        color = color_for(pct)
        label = row["Date"].strftime("%d")
        heat_cols[i].markdown(
            f"<div title='{row['Date_str']}' style='background:{color};border-radius:4px;"
            f"text-align:center;padding:6px 0;color:white;font-size:11px;'>{label}</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.write("### 📅 Full Consistency Log")
    display_df = df.set_index("Date").sort_index(ascending=False).copy()
    for col in BOOL_HABITS:
        display_df[col] = display_df[col].apply(lambda x: "✅" if int(as_number(x)) == 1 else "❌")
    display_df = display_df.rename(columns={k: v["label"] for k, v in HABITS.items()})
    st.dataframe(display_df, use_container_width=True)
else:
    st.info("Start logging to see your progress!")
