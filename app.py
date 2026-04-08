import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import html
import textwrap

st.set_page_config(page_title="Student Study Scheduler", layout="wide")

st.title("Student Study Scheduler")
st.write("Enter your assignments and weekly availability.")

# -----------------------------
# SESSION STATE
# -----------------------------
if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "availability" not in st.session_state:
    st.session_state.availability = []

if "schedule" not in st.session_state:
    st.session_state.schedule = pd.DataFrame()

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def reset_all_data():
    st.session_state.tasks = []
    st.session_state.availability = []
    st.session_state.schedule = pd.DataFrame()

def get_course_colors(courses):
    palette = [
        "#2563EB", "#DC2626", "#16A34A", "#CA8A04",
        "#9333EA", "#EA580C", "#0891B2", "#BE185D",
        "#4B5563", "#0F766E"
    ]
    clean = sorted(
        set(
            str(c).strip()
            for c in courses
            if pd.notna(c) and str(c).strip()
        )
    )
    return {course: palette[i % len(palette)] for i, course in enumerate(clean)}

def make_course_badge(course, color):
    course = str(course).strip() if pd.notna(course) else "Course"
    safe_course = html.escape(course)
    safe_color = html.escape(color)

    return textwrap.dedent(f"""
    <span style="
        background-color:{safe_color};
        color:#FFFFFF;
        padding:4px 10px;
        border-radius:999px;
        font-size:12px;
        font-weight:700;
        display:inline-block;
        margin-bottom:8px;
    ">
        {safe_course}
    </span>
    """).strip()

def render_card(row, color):
    safe_task = html.escape(str(row["Task"]))
    safe_course = html.escape(str(row["Course"]))
    safe_start = html.escape(str(row["Start"]))
    safe_end = html.escape(str(row["End"]))
    safe_status = html.escape(str(row["Status"]))
    safe_color = html.escape(color)

    badge_html = make_course_badge(row["Course"], color)

    return textwrap.dedent(f"""
    <div style="
        padding:14px;
        margin-bottom:12px;
        border-radius:12px;
        border:1px solid #D1D5DB;
        border-left:6px solid {safe_color};
        background-color:#F9FAFB;
        box-shadow:0 1px 2px rgba(0,0,0,0.05);
    ">
        {badge_html}
        <div style="
            font-weight:700;
            font-size:18px;
            color:#111827;
            margin-bottom:6px;
        ">
            {safe_task}
        </div>
        <div style="
            font-size:14px;
            color:#374151;
            margin-bottom:4px;
        ">
            {safe_course}
        </div>
        <div style="
            font-size:14px;
            color:#1F2937;
            margin-bottom:4px;
        ">
            {safe_start} - {safe_end}
        </div>
        <div style="
            font-size:13px;
            color:#4B5563;
        ">
            Status: {safe_status}
        </div>
    </div>
    """).strip()

# -----------------------------
# RESET BUTTON
# -----------------------------
if st.button("Reset App"):
    reset_all_data()
    st.rerun()

# -----------------------------
# ADD TASK
# -----------------------------
st.subheader("Add Task")

with st.form("task_form"):
    task = st.text_input("Task")
    course = st.text_input("Course")
    due = st.date_input("Due Date")
    mins = st.number_input("Minutes", min_value=5, step=5)
    priority = st.slider("Priority", 1, 5)

    if st.form_submit_button("Add Task"):
        if task.strip() and course.strip():
            st.session_state.tasks.append({
                "Task": task.strip(),
                "Course": course.strip(),
                "Due Date": due,
                "Hours": mins / 60,
                "Priority": priority
            })
            st.success("Task added.")
        else:
            st.warning("Please enter both a task and a course.")

# -----------------------------
# SHOW TASKS
# -----------------------------
if st.session_state.tasks:
    st.subheader("Current Tasks")
    task_df = pd.DataFrame(st.session_state.tasks)
    st.dataframe(task_df, use_container_width=True)

# -----------------------------
# ADD AVAILABILITY
# -----------------------------
st.subheader("Availability")

with st.form("avail_form"):
    day = st.selectbox(
        "Day",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    )
    start = st.time_input("Start Time")
    end = st.time_input("End Time")

    if st.form_submit_button("Add Availability"):
        if start < end:
            st.session_state.availability.append({
                "Day": day,
                "Start": start,
                "End": end
            })
            st.success("Availability added.")
        else:
            st.warning("End time must be later than start time.")

# -----------------------------
# SHOW AVAILABILITY
# -----------------------------
if st.session_state.availability:
    st.subheader("Current Availability")
    avail_df = pd.DataFrame(st.session_state.availability)
    st.dataframe(avail_df, use_container_width=True)

# -----------------------------
# GENERATE SCHEDULE
# -----------------------------
st.subheader("Generate Schedule")

days = st.number_input("Days to plan", min_value=1, max_value=14, value=7)
block = st.selectbox("Session length (minutes)", [30, 45, 60])

if st.button("Generate Schedule"):
    df = pd.DataFrame(st.session_state.tasks)

    if df.empty:
        st.warning("Add tasks first.")
    elif not st.session_state.availability:
        st.warning("Add availability first.")
    else:
        df["Due Date"] = pd.to_datetime(df["Due Date"])
        today = datetime.now().date()

        df["Days Left"] = (df["Due Date"].dt.date - today).apply(lambda x: max(x.days, 1))
        df["Urgency"] = df["Priority"] / df["Days Left"]
        df = df.sort_values("Urgency", ascending=False).reset_index(drop=True)

        schedule = []
        block_hr = block / 60

        for i in range(days):
            d = today + timedelta(days=i)
            name = d.strftime("%A")

            for slot in st.session_state.availability:
                if slot["Day"] != name:
                    continue

                current = datetime.combine(d, slot["Start"])
                end_time = datetime.combine(d, slot["End"])

                for idx in df.index:
                    hrs = df.at[idx, "Hours"]
                    due_date = df.at[idx, "Due Date"].date()

                    if d > due_date:
                        continue

                    while hrs > 0 and current < end_time:
                        session_len = min(block_hr, hrs)
                        next_time = current + timedelta(hours=session_len)

                        if next_time > end_time:
                            break

                        schedule.append({
                            "Date": str(d),
                            "Day": name,
                            "Start": current.strftime("%I:%M %p"),
                            "End": next_time.strftime("%I:%M %p"),
                            "Task": df.at[idx, "Task"],
                            "Course": df.at[idx, "Course"],
                            "Status": "Not Started"
                        })

                        hrs -= session_len
                        current = next_time

                    df.at[idx, "Hours"] = hrs

        st.session_state.schedule = pd.DataFrame(schedule)

        if st.session_state.schedule.empty:
            st.info("No schedule could be created with the current tasks and availability.")
        else:
            st.success("Schedule generated.")

# -----------------------------
# DISPLAY CALENDAR
# -----------------------------
if not st.session_state.schedule.empty:
    st.subheader("Study Calendar")

    sched = st.session_state.schedule.copy()
    sched["Date_dt"] = pd.to_datetime(sched["Date"])
    sched = sched.sort_values(["Date_dt", "Start"])

    colors = get_course_colors(sched["Course"].unique())

    view = st.radio("View", ["Calendar", "Agenda"], horizontal=True)

    if view == "Calendar":
        dates = sched["Date_dt"].drop_duplicates().tolist()

        if len(dates) > 7:
            dates = dates[:7]

        cols = st.columns(len(dates))

        for col, d in zip(cols, dates):
            with col:
                st.markdown(f"### {d.strftime('%a %m/%d')}")
                day_df = sched[sched["Date_dt"] == d]

                if day_df.empty:
                    st.info("No sessions")
                else:
                    for i, row in day_df.iterrows():
                        color = colors.get(str(row["Course"]).strip(), "#4B5563")
                        st.markdown(render_card(row, color), unsafe_allow_html=True)

                        new_status = st.selectbox(
                            "Status",
                            ["Not Started", "In Progress", "Completed"],
                            index=["Not Started", "In Progress", "Completed"].index(row["Status"]),
                            key=f"status_{i}"
                        )
                        st.session_state.schedule.at[i, "Status"] = new_status
    else:
        for date, group in sched.groupby("Date"):
            st.markdown(f"### {date}")
            for i, row in group.iterrows():
                color = colors.get(str(row["Course"]).strip(), "#4B5563")
                st.markdown(render_card(row, color), unsafe_allow_html=True)

                new_status = st.selectbox(
                    f"Status for {row['Task']} ({row['Start']})",
                    ["Not Started", "In Progress", "Completed"],
                    index=["Not Started", "In Progress", "Completed"].index(row["Status"]),
                    key=f"agenda_status_{i}"
                )
                st.session_state.schedule.at[i, "Status"] = new_status
