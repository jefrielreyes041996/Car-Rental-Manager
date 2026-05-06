import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import json

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="FleetDrive Manager",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3, .big-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
}

.stApp {
    background: #0d0f14;
    color: #e8e8e8;
}

section[data-testid="stSidebar"] {
    background: #13151c;
    border-right: 1px solid #1e2130;
}

.metric-card {
    background: #13151c;
    border: 1px solid #1e2130;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}

.metric-card .value {
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    color: #f0c040;
}

.metric-card .label {
    font-size: 0.85rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.trip-card {
    background: #13151c;
    border: 1px solid #1e2130;
    border-left: 3px solid #f0c040;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 10px;
}

.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.status-available { background: #1a3a2a; color: #4caf7d; }
.status-on-trip { background: #3a2a1a; color: #f0a040; }
.status-maintenance { background: #3a1a1a; color: #f04040; }
.status-scheduled { background: #1a2a3a; color: #40a0f0; }
.status-completed { background: #1a3a2a; color: #4caf7d; }
.status-cancelled { background: #3a1a1a; color: #f04040; }
.status-ongoing { background: #3a2a1a; color: #f0a040; }

.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #f0c040;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e2130;
}

.avail-day {
    display: inline-block;
    background: #1a3a2a;
    color: #4caf7d;
    padding: 4px 10px;
    border-radius: 6px;
    margin: 2px;
    font-size: 0.78rem;
}

.booked-day {
    display: inline-block;
    background: #3a2a1a;
    color: #f0a040;
    padding: 4px 10px;
    border-radius: 6px;
    margin: 2px;
    font-size: 0.78rem;
}

div[data-testid="stSelectbox"] > div,
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stNumberInput"] > div > div > input,
div[data-testid="stTextArea"] textarea {
    background: #1a1d26 !important;
    border: 1px solid #2a2d3a !important;
    color: #e8e8e8 !important;
    border-radius: 8px !important;
}

.stButton > button {
    background: #f0c040;
    color: #0d0f14;
    border: none;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    padding: 8px 20px;
    transition: all 0.2s;
}

.stButton > button:hover {
    background: #f5d060;
    transform: translateY(-1px);
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    color: #888;
}

.stTabs [aria-selected="true"] {
    color: #f0c040 !important;
}

label {
    color: #aaa !important;
    font-size: 0.85rem !important;
}

.stDataFrame {
    border: 1px solid #1e2130;
    border-radius: 10px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)


# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect("fleet_drive.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        make TEXT, model TEXT, year INTEGER,
        plate TEXT UNIQUE, color TEXT, type TEXT,
        status TEXT DEFAULT 'Available',
        notes TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS drivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, license_no TEXT UNIQUE,
        contact TEXT, emergency_contact TEXT,
        status TEXT DEFAULT 'Available',
        notes TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT, client_contact TEXT,
        vehicle_id INTEGER, driver_id INTEGER,
        origin TEXT, destination TEXT,
        start_date TEXT, end_date TEXT, num_days INTEGER,
        gas_allowance REAL DEFAULT 0,
        toll_allowance REAL DEFAULT 0,
        meal_allowance REAL DEFAULT 0,
        other_allowance REAL DEFAULT 0,
        actual_gas REAL DEFAULT 0,
        actual_toll REAL DEFAULT 0,
        actual_meal REAL DEFAULT 0,
        actual_other REAL DEFAULT 0,
        status TEXT DEFAULT 'Scheduled',
        notes TEXT,
        created_at TEXT
    )""")

    conn.commit()
    conn.close()

init_db()


# --- HELPERS ---
def get_vehicles():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM vehicles", conn)
    conn.close()
    return df

def get_drivers():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM drivers", conn)
    conn.close()
    return df

def get_trips():
    conn = get_db()
    df = pd.read_sql("""
        SELECT t.*, v.make || ' ' || v.model AS vehicle_name, v.plate,
               d.name AS driver_name
        FROM trips t
        LEFT JOIN vehicles v ON t.vehicle_id = v.id
        LEFT JOIN drivers d ON t.driver_id = d.id
    """, conn)
    conn.close()
    return df

def status_badge(status):
    cls = {
        "Available": "status-available",
        "On Trip": "status-on-trip",
        "Maintenance": "status-maintenance",
        "Scheduled": "status-scheduled",
        "Completed": "status-completed",
        "Cancelled": "status-cancelled",
        "Ongoing": "status-ongoing",
        "On Duty": "status-on-trip",
    }.get(status, "status-available")
    return f'<span class="status-badge {cls}">{status}</span>'

def get_vehicle_bookings(vehicle_id):
    conn = get_db()
    df = pd.read_sql("""
        SELECT t.*, d.name as driver_name
        FROM trips t
        LEFT JOIN drivers d ON t.driver_id = d.id
        WHERE t.vehicle_id = ? AND t.status NOT IN ('Cancelled')
        ORDER BY t.start_date ASC
    """, conn, params=(vehicle_id,))
    conn.close()
    return df


# --- SIDEBAR ---
st.sidebar.markdown("""
<div style='padding: 10px 0 20px 0'>
    <div style='font-family: Syne, sans-serif; font-size: 1.6rem; font-weight: 800; color: #f0c040;'>⚡ FleetDrive</div>
    <div style='font-size: 0.78rem; color: #555; letter-spacing: 1px; text-transform: uppercase;'>Car Rental Manager</div>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🚗 Vehicles",
    "👤 Drivers",
    "📋 Trips & Bookings",
    "💰 Allowances & Expenses",
    "📅 Vehicle Availability",
    "📊 Reports"
], label_visibility="collapsed")


# ==============================
# DASHBOARD
# ==============================
if page == "🏠 Dashboard":
    st.markdown("<div class='section-title'>🏠 Dashboard Overview</div>", unsafe_allow_html=True)

    vehicles = get_vehicles()
    drivers = get_drivers()
    trips = get_trips()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class='metric-card'>
            <div class='value'>{len(vehicles)}</div>
            <div class='label'>Total Vehicles</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        avail_v = len(vehicles[vehicles['status'] == 'Available']) if not vehicles.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='value' style='color:#4caf7d'>{avail_v}</div>
            <div class='label'>Available Vehicles</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='metric-card'>
            <div class='value'>{len(drivers)}</div>
            <div class='label'>Total Drivers</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        active = len(trips[trips['status'].isin(['Scheduled', 'Ongoing'])]) if not trips.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='value' style='color:#f0a040'>{active}</div>
            <div class='label'>Active Trips</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        completed = len(trips[trips['status'] == 'Completed']) if not trips.empty else 0
        st.markdown(f"""<div class='metric-card'>
            <div class='value' style='color:#4caf7d'>{completed}</div>
            <div class='label'>Completed Trips</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-title'>🔴 Active / Upcoming Trips</div>", unsafe_allow_html=True)
        if not trips.empty:
            active_trips = trips[trips['status'].isin(['Scheduled', 'Ongoing'])]
            if active_trips.empty:
                st.info("No active trips.")
            for _, row in active_trips.iterrows():
                st.markdown(f"""<div class='trip-card'>
                    <b>{row['client_name']}</b> {status_badge(row['status'])}<br>
                    🚗 {row.get('vehicle_name','')} ({row.get('plate','')})<br>
                    👤 {row.get('driver_name','')}<br>
                    📍 {row['origin']} → {row['destination']}<br>
                    📅 {row['start_date']} to {row['end_date']} ({row['num_days']} days)
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No trips yet.")

    with col2:
        st.markdown("<div class='section-title'>🚗 Fleet Status</div>", unsafe_allow_html=True)
        if not vehicles.empty:
            for _, v in vehicles.iterrows():
                st.markdown(f"""<div class='trip-card'>
                    <b>{v['make']} {v['model']}</b> {status_badge(v['status'])}<br>
                    🔖 {v['plate']} &nbsp;|&nbsp; 🎨 {v['color']} &nbsp;|&nbsp; 📂 {v['type']}<br>
                    📅 {v['year']}
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No vehicles added yet.")


# ==============================
# VEHICLES
# ==============================
elif page == "🚗 Vehicles":
    st.markdown("<div class='section-title'>🚗 Vehicle Management</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Vehicle List", "Add / Edit Vehicle"])

    with tab1:
        vehicles = get_vehicles()
        if vehicles.empty:
            st.info("No vehicles added yet.")
        else:
            for _, v in vehicles.iterrows():
                with st.expander(f"🚗 {v['make']} {v['model']} — {v['plate']}"):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Make:** {v['make']}<br>**Model:** {v['model']}<br>**Year:** {v['year']}", unsafe_allow_html=True)
                    c2.markdown(f"**Plate:** {v['plate']}<br>**Color:** {v['color']}<br>**Type:** {v['type']}", unsafe_allow_html=True)
                    c3.markdown(f"**Status:** {status_badge(v['status'])}<br>**Notes:** {v['notes'] or '—'}", unsafe_allow_html=True)

                    col_e, col_d = st.columns([1, 1])
                    with col_e:
                        new_status = st.selectbox("Update Status", ["Available", "On Trip", "Maintenance"], key=f"vs_{v['id']}")
                        if st.button("Update Status", key=f"vsu_{v['id']}"):
                            conn = get_db()
                            conn.execute("UPDATE vehicles SET status=? WHERE id=?", (new_status, v['id']))
                            conn.commit(); conn.close()
                            st.success("Status updated!"); st.rerun()
                    with col_d:
                        if st.button("🗑️ Delete Vehicle", key=f"vd_{v['id']}"):
                            conn = get_db()
                            conn.execute("DELETE FROM vehicles WHERE id=?", (v['id'],))
                            conn.commit(); conn.close()
                            st.success("Deleted!"); st.rerun()

    with tab2:
        st.markdown("**Add a New Vehicle**")
        c1, c2 = st.columns(2)
        make = c1.text_input("Make (e.g. Toyota)")
        model = c2.text_input("Model (e.g. Fortuner)")
        c3, c4 = st.columns(2)
        year = c3.number_input("Year", min_value=1990, max_value=2030, value=2020)
        plate = c4.text_input("Plate Number")
        c5, c6 = st.columns(2)
        color = c5.text_input("Color")
        vtype = c6.selectbox("Type", ["Sedan", "SUV", "Van", "Pickup", "Bus", "Motorcycle", "Other"])
        notes = st.text_area("Notes (optional)")

        if st.button("➕ Add Vehicle"):
            if make and model and plate:
                try:
                    conn = get_db()
                    conn.execute("INSERT INTO vehicles (make, model, year, plate, color, type, notes) VALUES (?,?,?,?,?,?,?)",
                                 (make, model, year, plate, color, vtype, notes))
                    conn.commit(); conn.close()
                    st.success(f"✅ {make} {model} ({plate}) added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please fill in Make, Model, and Plate.")


# ==============================
# DRIVERS
# ==============================
elif page == "👤 Drivers":
    st.markdown("<div class='section-title'>👤 Driver Management</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Driver List", "Add Driver"])

    with tab1:
        drivers = get_drivers()
        if drivers.empty:
            st.info("No drivers yet.")
        else:
            for _, d in drivers.iterrows():
                with st.expander(f"👤 {d['name']} — {d['license_no']}"):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Contact:** {d['contact']}<br>**Emergency:** {d['emergency_contact']}", unsafe_allow_html=True)
                    c2.markdown(f"**Status:** {status_badge(d['status'])}<br>**Notes:** {d['notes'] or '—'}", unsafe_allow_html=True)

                    new_status = st.selectbox("Update Status", ["Available", "On Duty"], key=f"ds_{d['id']}")
                    col_u, col_d = st.columns(2)
                    if col_u.button("Update Status", key=f"dsu_{d['id']}"):
                        conn = get_db()
                        conn.execute("UPDATE drivers SET status=? WHERE id=?", (new_status, d['id']))
                        conn.commit(); conn.close()
                        st.success("Updated!"); st.rerun()
                    if col_d.button("🗑️ Delete", key=f"dd_{d['id']}"):
                        conn = get_db()
                        conn.execute("DELETE FROM drivers WHERE id=?", (d['id'],))
                        conn.commit(); conn.close()
                        st.success("Deleted!"); st.rerun()

    with tab2:
        st.markdown("**Add a New Driver**")
        c1, c2 = st.columns(2)
        name = c1.text_input("Full Name")
        license_no = c2.text_input("License Number")
        c3, c4 = st.columns(2)
        contact = c3.text_input("Contact Number")
        emergency = c4.text_input("Emergency Contact")
        notes = st.text_area("Notes (optional)")

        if st.button("➕ Add Driver"):
            if name and license_no:
                try:
                    conn = get_db()
                    conn.execute("INSERT INTO drivers (name, license_no, contact, emergency_contact, notes) VALUES (?,?,?,?,?)",
                                 (name, license_no, contact, emergency, notes))
                    conn.commit(); conn.close()
                    st.success(f"✅ {name} added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Name and License Number required.")


# ==============================
# TRIPS & BOOKINGS
# ==============================
elif page == "📋 Trips & Bookings":
    st.markdown("<div class='section-title'>📋 Trips & Bookings</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["All Trips", "New Booking"])

    with tab1:
        trips = get_trips()
        filter_status = st.selectbox("Filter by Status", ["All", "Scheduled", "Ongoing", "Completed", "Cancelled"])
        if filter_status != "All" and not trips.empty:
            trips = trips[trips['status'] == filter_status]

        if trips.empty:
            st.info("No trips found.")
        else:
            for _, t in trips.iterrows():
                total_given = t['gas_allowance'] + t['toll_allowance'] + t['meal_allowance'] + t['other_allowance']
                total_actual = t['actual_gas'] + t['actual_toll'] + t['actual_meal'] + t['actual_other']
                with st.expander(f"📋 {t['client_name']} — {t['origin']} → {t['destination']} | {t['start_date']}"):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Client:** {t['client_name']}<br>**Contact:** {t['client_contact']}<br>**Status:** {status_badge(t['status'])}", unsafe_allow_html=True)
                    c2.markdown(f"**Vehicle:** {t.get('vehicle_name','')} ({t.get('plate','')})<br>**Driver:** {t.get('driver_name','')}<br>**Days:** {t['num_days']}", unsafe_allow_html=True)
                    c3.markdown(f"**Allowance Given:** ₱{total_given:,.2f}<br>**Actual Spent:** ₱{total_actual:,.2f}<br>**Balance:** ₱{total_given - total_actual:,.2f}", unsafe_allow_html=True)

                    new_status = st.selectbox("Update Status", ["Scheduled", "Ongoing", "Completed", "Cancelled"], key=f"ts_{t['id']}")
                    col_u, col_d = st.columns(2)
                    if col_u.button("Update Status", key=f"tsu_{t['id']}"):
                        conn = get_db()
                        conn.execute("UPDATE trips SET status=? WHERE id=?", (new_status, t['id']))
                        conn.commit(); conn.close()
                        st.success("Trip status updated!"); st.rerun()
                    if col_d.button("🗑️ Delete Trip", key=f"td_{t['id']}"):
                        conn = get_db()
                        conn.execute("DELETE FROM trips WHERE id=?", (t['id'],))
                        conn.commit(); conn.close()
                        st.success("Deleted!"); st.rerun()

    with tab2:
        vehicles = get_vehicles()
        drivers = get_drivers()

        if vehicles.empty or drivers.empty:
            st.warning("Please add vehicles and drivers first.")
        else:
            st.markdown("**New Trip Booking**")
            c1, c2 = st.columns(2)
            client_name = c1.text_input("Client Name")
            client_contact = c2.text_input("Client Contact")

            vehicle_options = {f"{r['make']} {r['model']} ({r['plate']})": r['id'] for _, r in vehicles.iterrows()}
            driver_options = {r['name']: r['id'] for _, r in drivers.iterrows()}

            c3, c4 = st.columns(2)
            selected_vehicle = c3.selectbox("Select Vehicle", list(vehicle_options.keys()))
            selected_driver = c4.selectbox("Select Driver", list(driver_options.keys()))

            c5, c6 = st.columns(2)
            origin = c5.text_input("Origin")
            destination = c6.text_input("Destination")

            c7, c8 = st.columns(2)
            start_date = c7.date_input("Start Date", value=date.today())
            end_date = c8.date_input("End Date", value=date.today() + timedelta(days=1))
            num_days = (end_date - start_date).days + 1

            st.markdown(f"**Trip Duration: {num_days} day(s)**")
            st.markdown("**Allowances**")
            ca, cb, cc, cd = st.columns(4)
            gas_allow = ca.number_input("Gas (₱)", min_value=0.0, step=100.0)
            toll_allow = cb.number_input("Toll (₱)", min_value=0.0, step=50.0)
            meal_allow = cc.number_input("Meals (₱)", min_value=0.0, step=50.0)
            other_allow = cd.number_input("Others (₱)", min_value=0.0, step=50.0)

            notes = st.text_area("Notes (optional)")

            if st.button("📋 Create Booking"):
                if client_name and origin and destination and start_date and end_date:
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO trips
                            (client_name, client_contact, vehicle_id, driver_id, origin, destination,
                             start_date, end_date, num_days, gas_allowance, toll_allowance,
                             meal_allowance, other_allowance, status, notes, created_at)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (client_name, client_contact,
                             vehicle_options[selected_vehicle], driver_options[selected_driver],
                             origin, destination,
                             str(start_date), str(end_date), num_days,
                             gas_allow, toll_allow, meal_allow, other_allow,
                             "Scheduled", notes, str(datetime.now())))
                        conn.commit(); conn.close()
                        st.success(f"✅ Booking created for {client_name}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Please fill in all required fields.")


# ==============================
# ALLOWANCES & EXPENSES
# ==============================
elif page == "💰 Allowances & Expenses":
    st.markdown("<div class='section-title'>💰 Allowances & Actual Expenses</div>", unsafe_allow_html=True)

    trips = get_trips()
    if trips.empty:
        st.info("No trips yet.")
    else:
        trip_options = {f"{r['client_name']} — {r['origin']} → {r['destination']} ({r['start_date']})": r['id']
                        for _, r in trips.iterrows()}
        selected = st.selectbox("Select Trip", list(trip_options.keys()))
        trip_id = trip_options[selected]
        conn = get_db()
        t = conn.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
        conn.close()

        cols = ["id","client_name","client_contact","vehicle_id","driver_id","origin","destination",
                "start_date","end_date","num_days","gas_allowance","toll_allowance","meal_allowance",
                "other_allowance","actual_gas","actual_toll","actual_meal","actual_other",
                "status","notes","created_at"]
        t = dict(zip(cols, t))

        st.markdown("### 📊 Allowance vs Actual")
        items = ["Gas", "Toll", "Meals", "Others"]
        given = [t['gas_allowance'], t['toll_allowance'], t['meal_allowance'], t['other_allowance']]
        actual = [t['actual_gas'], t['actual_toll'], t['actual_meal'], t['actual_other']]

        df_compare = pd.DataFrame({"Item": items, "Given (₱)": given, "Actual (₱)": actual})
        df_compare["Balance (₱)"] = df_compare["Given (₱)"] - df_compare["Actual (₱)"]
        st.dataframe(df_compare, use_container_width=True, hide_index=True)

        total_given = sum(given)
        total_actual = sum(actual)
        balance = total_given - total_actual
        color = "#4caf7d" if balance >= 0 else "#f04040"

        st.markdown(f"""
        <div class='trip-card' style='margin-top:10px'>
            <b>Total Given:</b> ₱{total_given:,.2f} &nbsp;|&nbsp;
            <b>Total Actual:</b> ₱{total_actual:,.2f} &nbsp;|&nbsp;
            <b style='color:{color}'>Balance: ₱{balance:,.2f}</b>
        </div>""", unsafe_allow_html=True)

        st.markdown("### ✏️ Update Actual Expenses")
        ca, cb, cc, cd = st.columns(4)
        act_gas = ca.number_input("Actual Gas (₱)", value=float(t['actual_gas']), step=100.0)
        act_toll = cb.number_input("Actual Toll (₱)", value=float(t['actual_toll']), step=50.0)
        act_meal = cc.number_input("Actual Meals (₱)", value=float(t['actual_meal']), step=50.0)
        act_other = cd.number_input("Actual Others (₱)", value=float(t['actual_other']), step=50.0)

        if st.button("💾 Save Actual Expenses"):
            conn = get_db()
            conn.execute("UPDATE trips SET actual_gas=?, actual_toll=?, actual_meal=?, actual_other=? WHERE id=?",
                         (act_gas, act_toll, act_meal, act_other, trip_id))
            conn.commit(); conn.close()
            st.success("Expenses updated!"); st.rerun()


# ==============================
# VEHICLE AVAILABILITY
# ==============================
elif page == "📅 Vehicle Availability":
    st.markdown("<div class='section-title'>📅 Vehicle Availability & Booking Calendar</div>", unsafe_allow_html=True)

    vehicles = get_vehicles()
    if vehicles.empty:
        st.info("No vehicles added yet.")
    else:
        vehicle_options = {f"{r['make']} {r['model']} ({r['plate']})": r['id'] for _, r in vehicles.iterrows()}
        selected_v = st.selectbox("Select Vehicle", list(vehicle_options.keys()))
        vehicle_id = vehicle_options[selected_v]

        bookings = get_vehicle_bookings(vehicle_id)

        st.markdown("#### 📋 Bookings for this Vehicle")
        if bookings.empty:
            st.success("✅ No bookings — this vehicle is fully available!")
        else:
            for _, b in bookings.iterrows():
                st.markdown(f"""<div class='trip-card'>
                    <b>{b['client_name']}</b> {status_badge(b['status'])}<br>
                    👤 Driver: {b.get('driver_name', '—')}<br>
                    📍 {b['origin']} → {b['destination']}<br>
                    📅 <b>{b['start_date']}</b> to <b>{b['end_date']}</b> ({b['num_days']} days)
                </div>""", unsafe_allow_html=True)

        st.markdown("#### 🗓️ Next 30 Days Availability")
        today = date.today()
        booked_dates = set()

        for _, b in bookings.iterrows():
            if b['status'] in ['Scheduled', 'Ongoing']:
                try:
                    s = datetime.strptime(b['start_date'], "%Y-%m-%d").date()
                    e = datetime.strptime(b['end_date'], "%Y-%m-%d").date()
                    d = s
                    while d <= e:
                        booked_dates.add(d)
                        d += timedelta(days=1)
                except:
                    pass

        calendar_html = "<div style='line-height: 2.2;'>"
        for i in range(30):
            day = today + timedelta(days=i)
            if day in booked_dates:
                calendar_html += f"<span class='booked-day'>🔴 {day.strftime('%b %d')}</span>"
            else:
                calendar_html += f"<span class='avail-day'>✅ {day.strftime('%b %d')}</span>"
        calendar_html += "</div>"
        st.markdown(calendar_html, unsafe_allow_html=True)

        st.markdown("#### 📆 Available Date Ranges (Next 30 Days)")
        available_ranges = []
        range_start = None
        for i in range(30):
            day = today + timedelta(days=i)
            if day not in booked_dates:
                if range_start is None:
                    range_start = day
            else:
                if range_start is not None:
                    available_ranges.append((range_start, today + timedelta(days=i-1)))
                    range_start = None
        if range_start is not None:
            available_ranges.append((range_start, today + timedelta(days=29)))

        if available_ranges:
            for s, e in available_ranges:
                days_count = (e - s).days + 1
                st.markdown(f"✅ **{s.strftime('%B %d')}** to **{e.strftime('%B %d, %Y')}** — {days_count} day(s) free")
        else:
            st.warning("⚠️ This vehicle is fully booked for the next 30 days.")


# ==============================
# REPORTS
# ==============================
elif page == "📊 Reports":
    st.markdown("<div class='section-title'>📊 Reports & Summary</div>", unsafe_allow_html=True)

    trips = get_trips()

    if trips.empty:
        st.info("No data yet.")
    else:
        tab1, tab2, tab3 = st.tabs(["Trip Summary", "Expense Summary", "Driver Summary"])

        with tab1:
            st.markdown("**All Trips Overview**")
            display_cols = ['client_name', 'vehicle_name', 'plate', 'driver_name',
                            'origin', 'destination', 'start_date', 'end_date', 'num_days', 'status']
            existing = [c for c in display_cols if c in trips.columns]
            st.dataframe(trips[existing], use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("**Expense Overview per Trip**")
            trips['total_given'] = trips['gas_allowance'] + trips['toll_allowance'] + trips['meal_allowance'] + trips['other_allowance']
            trips['total_actual'] = trips['actual_gas'] + trips['actual_toll'] + trips['actual_meal'] + trips['actual_other']
            trips['balance'] = trips['total_given'] - trips['total_actual']
            exp_cols = ['client_name', 'start_date', 'end_date', 'total_given', 'total_actual', 'balance', 'status']
            existing_exp = [c for c in exp_cols if c in trips.columns]
            st.dataframe(trips[existing_exp], use_container_width=True, hide_index=True)

            total_g = trips['total_given'].sum()
            total_a = trips['total_actual'].sum()
            st.markdown(f"""<div class='trip-card'>
                💰 <b>Total Allowances Given: ₱{total_g:,.2f}</b> &nbsp;|&nbsp;
                🧾 <b>Total Actual Spent: ₱{total_a:,.2f}</b> &nbsp;|&nbsp;
                📊 <b>Overall Balance: ₱{total_g - total_a:,.2f}</b>
            </div>""", unsafe_allow_html=True)

        with tab3:
            st.markdown("**Trips per Driver**")
            if 'driver_name' in trips.columns:
                driver_summary = trips.groupby('driver_name').agg(
                    Total_Trips=('id', 'count'),
                    Completed=('status', lambda x: (x == 'Completed').sum()),
                    Total_Days=('num_days', 'sum')
                ).reset_index()
                st.dataframe(driver_summary, use_container_width=True, hide_index=True)
