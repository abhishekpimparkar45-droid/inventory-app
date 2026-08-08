import streamlit as st

st.markdown("""
    <link rel="manifest" href="manifest.json">
""", unsafe_allow_html=True)
from datetime import datetime
import hashlib
import json
import sqlite3
import pandas as pd
import streamlit as st

# ==========================================
# 1. PAGE CONFIG & SETUP
# ==========================================
st.set_page_config(
    page_title="Elite Water Purifier Inventory & Invoicing",
    page_icon="https://raw.githubusercontent.com/abhishekpimparkar45-droid/inventory-app/main/logo.png.jpg",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==========================================
# 2. DATABASE SETUP & AUTO-MIGRATION (Fixed 5 Columns Schema)
# ==========================================
def get_db_connection():
    conn = sqlite3.connect("water_purifier_inventory.db", check_same_thread=False)
    cursor = conn.cursor()

    # Check existing columns in main_inventory if table exists
    cursor.execute("PRAGMA table_info(main_inventory)")
    columns = cursor.fetchall()
    
    # If table has wrong number of columns, drop and recreate it cleanly to avoid mismatch
    if columns and len(columns) != 5:
        cursor.execute("DROP TABLE main_inventory")
        conn.commit()

    # Main Inventory with exactly 5 columns: item_name, total_stock, defective_stock, unit_price, min_stock_alert
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS main_inventory (
            item_name TEXT PRIMARY KEY,
            total_stock INTEGER,
            defective_stock INTEGER,
            unit_price REAL DEFAULT 0.0,
            min_stock_alert INTEGER DEFAULT 5
        )
    """)

    # Technicians
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS technicians (
            technician_name TEXT PRIMARY KEY
        )
    """)

    # Technician Stock
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS technician_stock (
            technician_name TEXT,
            item_name TEXT,
            quantity INTEGER,
            PRIMARY KEY (technician_name, item_name)
        )
    """)

    # History Log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            date TEXT,
            transaction_type TEXT,
            technician_name TEXT,
            item_name TEXT,
            quantity INTEGER,
            status TEXT
        )
    """)

    # Purchase Invoices (Inward Bills from Vendors)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_invoices (
            invoice_id TEXT PRIMARY KEY,
            supplier_name TEXT,
            invoice_date TEXT,
            total_amount REAL,
            items_json TEXT
        )
    """)

    # Users Profile & Auth
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT,
            password TEXT,
            bio TEXT,
            avatar_seed TEXT
        )
    """)

    # Insert Default Water Purifier Spares if table is empty (5 values for 5 columns)
    cursor.execute("SELECT COUNT(*) FROM main_inventory")
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ("Sediment Filter 10 inch", 50, 0, 150.0, 5),
            ("Pre-Carbon Filter", 40, 0, 180.0, 5),
            ("RO Membrane 80 GPD", 25, 0, 850.0, 3),
            ("Booster Pump 100 GPD", 15, 0, 1450.0, 2),
            ("SMPS Power Adapter 24V", 30, 0, 450.0, 5),
            ("UV Barrel Assembly", 12, 0, 650.0, 2),
            ("FR 450 Flow Restrictor", 100, 0, 40.0, 10)
        ]
        cursor.executemany("INSERT OR IGNORE INTO main_inventory VALUES (?, ?, ?, ?, ?)", sample_items)

    cursor.execute("SELECT COUNT(*) FROM technicians")
    if cursor.fetchone()[0] == 0:
        for t in ["Rahul Sharma", "Amit Patel", "Sagar Shinde"]:
            cursor.execute("INSERT OR IGNORE INTO technicians (technician_name) VALUES (?)", (t,))

    conn.commit()
    return conn

conn = get_db_connection()
cursor = conn.cursor()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 3. SESSION STATE INITIALIZATION
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True
if "current_user" not in st.session_state:
    st.session_state.current_user = "ActiveUser"
if "user_email" not in st.session_state:
    st.session_state.user_email = "admin@eliteinventory.com"
if "user_bio" not in st.session_state:
    st.session_state.user_bio = "Senior Inventory & Service Manager"
if "avatar_seed" not in st.session_state:
    st.session_state.avatar_seed = "Felix"
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "📊 Dashboard View"
if "inward_cart" not in st.session_state:
    st.session_state.inward_cart = []

# ==========================================
# 4. GEN-Z COLORFUL GLASSMORPHISM STYLING
# ==========================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        #MainMenu, footer, header { visibility: hidden; }
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }

        .stApp {
            background-color: #0D0D12 !important;
            color: #F3F4F6 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .ambient-glow-1 {
            position: fixed; top: -10%; left: 10%; width: 450px; height: 450px;
            background: radial-gradient(circle, rgba(168, 85, 247, 0.28) 0%, rgba(0,0,0,0) 70%);
            filter: blur(85px); z-index: -1; pointer-events: none;
        }
        .ambient-glow-2 {
            position: fixed; top: 20%; right: 5%; width: 500px; height: 500px;
            background: radial-gradient(circle, rgba(0, 245, 255, 0.22) 0%, rgba(0,0,0,0) 70%);
            filter: blur(95px); z-index: -1; pointer-events: none;
        }

        .genz-header-title {
            font-size: 2.1rem; font-weight: 800;
            background: linear-gradient(90deg, #00F5FF 0%, #A855F7 50%, #FF007F 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            letter-spacing: -0.5px;
        }

        .icon-glow { filter: drop-shadow(0px 0px 8px rgba(0, 245, 255, 0.8)); display: inline-block; }
        .icon-magenta { filter: drop-shadow(0px 0px 8px rgba(255, 0, 127, 0.8)); }
        .icon-yellow { filter: drop-shadow(0px 0px 8px rgba(255, 215, 0, 0.8)); }

        div[data-testid="stMetric"] {
            background: rgba(22, 22, 34, 0.65) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-left: 4px solid #00F5FF !important;
            padding: 16px !important; border-radius: 16px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
        }
        div[data-testid="stMetric"] label {
            color: #9CA3AF !important; font-weight: 700 !important;
            text-transform: uppercase !important; font-size: 0.72rem !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #FFFFFF !important; font-weight: 800 !important; font-size: 1.8rem !important;
        }

        .stButton > button {
            background: rgba(22, 22, 34, 0.75) !important;
            color: #F3F4F6 !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 14px !important;
            font-weight: 700 !important;
            padding: 0.65rem 1rem !important;
            transition: all 0.3s ease !important;
            width: 100% !important;
        }
        .stButton > button:hover {
            border-color: #00F5FF !important;
            color: #00F5FF !important;
            box-shadow: 0 8px 25px rgba(0, 245, 255, 0.35) !important;
            transform: translateY(-2px) !important;
        }

        .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
            background-color: rgba(22, 22, 34, 0.85) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 12px !important;
        }

        div[data-testid="stDataFrame"] {
            background: rgba(22, 22, 34, 0.5) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
    </style>
    <div class="ambient-glow-1"></div>
    <div class="ambient-glow-2"></div>
""", unsafe_allow_html=True)

# ==========================================
# 5. HEADER BAR & NAVIGATION
# ==========================================
h_col1, h_col2 = st.columns([2.2, 1.3])

with h_col1:
    st.markdown("""
        <div>
            <h1 class="genz-header-title"><span class="icon-yellow">⚡</span> Elite Inventory & Inward Stock</h1>
            <p style="color: #9CA3AF; font-size: 0.78rem; margin-top: 2px;">Water Purifier Inventory • GenZ Glassmorphism UI</p>
        </div>
    """, unsafe_allow_html=True)

with h_col2:
    p1, p2 = st.columns([2, 1])
    with p1:
        st.markdown(f"""
            <div style="text-align: right; padding-top: 2px;">
                <span style="font-size: 10px; font-weight: 800; color: #00F5FF; text-transform: uppercase;">● Online</span><br>
                <span style="font-size: 13px; font-weight: 700; color: #FFFFFF;">@{st.session_state.current_user}</span>
            </div>
        """, unsafe_allow_html=True)
    with p2:
        if st.button("👤 Profile", key="hdr_prof_btn"):
            st.session_state.nav_page = "⚙️ Vault & User Profile"
            st.rerun()

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

nav_options = [
    "📊 Dashboard View",
    "🧾 Inward Invoice Entry (Stock In)",
    "📤 Issue Stock to Technician",
    "🔄 Defective Returns",
    "👷‍♂️ Field Technicians",
    "📜 System History Logs",
    "⚙️ Vault & User Profile"
]

def on_nav_change():
    st.session_state.nav_page = st.session_state.select_nav_option

curr_idx = nav_options.index(st.session_state.nav_page) if st.session_state.nav_page in nav_options else 0

st.selectbox(
    "Navigation Selector",
    nav_options,
    index=curr_idx,
    key="select_nav_option",
    on_change=on_nav_change,
    label_visibility="collapsed"
)

selected_nav = st.session_state.nav_page
st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

def show_back_to_dashboard_button():
    if selected_nav != "📊 Dashboard View":
        b_col1, b_col2 = st.columns([1, 5])
        with b_col1:
            if st.button("🔙 Back to Dashboard", key=f"back_btn_{selected_nav}"):
                st.session_state.nav_page = "📊 Dashboard View"
                st.rerun()
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

show_back_to_dashboard_button()

# ==========================================
# 6. NAVIGATION VIEWS
# ==========================================

# PAGE 1: DASHBOARD VIEW
if selected_nav == "📊 Dashboard View":
    st.markdown('<p style="font-size: 11px; font-weight: 800; color: #9CA3AF; letter-spacing: 1.5px;">🚀 QUICK ACCESS TOOLS</p>', unsafe_allow_html=True)

    def set_page(page_name):
        st.session_state.nav_page = page_name

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.button("📊\nDashboard", on_click=set_page, args=("📊 Dashboard View",))
    with c2: st.button("🧾\nInward Invoices", on_click=set_page, args=("🧾 Inward Invoice Entry (Stock In)",))
    with c3: st.button("📤\nIssue Stock", on_click=set_page, args=("📤 Issue Stock to Technician",))
    with c4: st.button("🔄\nDefectives", on_click=set_page, args=("🔄 Defective Returns",))
    with c5: st.button("🔐\nUser Profile", on_click=set_page, args=("⚙️ Vault & User Profile",))

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    df_main = pd.read_sql_query("SELECT * FROM main_inventory", conn)
    df_purchase_inv = pd.read_sql_query("SELECT * FROM purchase_invoices", conn)

    total_items = len(df_main)
    total_stock_qty = df_main["total_stock"].sum() if not df_main.empty else 0
    total_defective = df_main["defective_stock"].sum() if not df_main.empty else 0
    total_purchase_val = df_purchase_inv["total_amount"].sum() if not df_purchase_inv.empty else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL ITEMS", f"{total_items}")
    m2.metric("AVAILABLE STOCK", f"{int(total_stock_qty)} Units")
    m3.metric("DEFECTIVE RETURNS", f"{int(total_defective)} Units")
    m4.metric("TOTAL PURCHASE COST", f"₹ {total_purchase_val:,.2f}")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### 📋 Live Inventory Database (Water Purifier Spares)")
    search_q = st.text_input("🔍 Search spare parts by name...").strip()

    if not df_main.empty and search_q:
        df_main_disp = df_main[df_main["item_name"].str.contains(search_q, case=False, na=False)]
    else:
        df_main_disp = df_main

    if df_main_disp.empty:
        st.info("No materials found in inventory database.")
    else:
        st.dataframe(df_main_disp, use_container_width=True)

    # Edit Stock Feature
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    with st.expander("🛠️ ✏️ Edit Existing Inventory Stock (स्टॉक किंवा किंमत दुरुस्त करा)", expanded=False):
        st.caption("जर एखाद्या स्पेर पार्टचा स्टॉक किंवा रेट चुकून चुकीचा एन्ट्री झाला असेल, तर तुम्ही इथे थेट अपडेट करू शकता.")
        
        if df_main.empty:
            st.info("इन्व्हेंटरीमध्ये कोणतेही आयटम्स उपलब्ध नाहीत.")
        else:
            all_items_list = df_main["item_name"].tolist()
            selected_edit_item = st.selectbox("🎯 दुरुस्त करण्यासाठी आयटम निवडा:", all_items_list, key="sel_edit_item")
            
            item_row = df_main[df_main["item_name"] == selected_edit_item].iloc[0]
            curr_total = int(item_row["total_stock"])
            curr_defective = int(item_row["defective_stock"])
            curr_price = float(item_row["unit_price"])
            
            with st.form("edit_stock_form"):
                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1:
                    new_total_stock = st.number_input("नवा Available Total Stock", min_value=0, value=curr_total)
                with e_col2:
                    new_defective_stock = st.number_input("नवा Defective Stock", min_value=0, value=curr_defective)
                with e_col3:
                    new_unit_price = st.number_input("नवी Unit Price (₹)", min_value=0.0, value=curr_price)
                
                if st.form_submit_button("💾 Update Stock Now"):
                    cursor.execute("""
                        UPDATE main_inventory 
                        SET total_stock = ?, defective_stock = ?, unit_price = ? 
                        WHERE item_name = ?
                    """, (new_total_stock, new_defective_stock, new_unit_price, selected_edit_item))
                    
                    cursor.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?)",
                        (str(datetime.now().date()), "MANUAL_STOCK_EDIT", st.session_state.current_user, selected_edit_item, new_total_stock, "Updated Stock/Price"))
                    
                    conn.commit()
                    st.success(f"✅ '{selected_edit_item}' चा स्टॉक यशस्वीरीत्या अपडेट झाला!")
                    st.rerun()

# PAGE 2: INWARD INVOICE ENTRY (STOCK IN)
elif selected_nav == "🧾 Inward Invoice Entry (Stock In)":
    st.subheader("🧾 Received Vendor Invoice & Automatic Stock Inward")
    st.caption("Enter the bill details received from your supplier to automatically update your warehouse inventory.")

    tab_entry, tab_history = st.tabs(["➕ Add Received Invoice", "📜 Vendor Invoice History"])

    with tab_entry:
        col_inv_left, col_inv_right = st.columns([1.2, 1])

        with col_inv_left:
            st.markdown("##### 🏢 Vendor / Supplier Bill Details")
            v_inv_no = st.text_input("Invoice / Bill Number (e.g. INV-9042)", key="v_inv_no")
            v_name = st.text_input("Supplier / Distributor Name", key="v_name")
            v_date = st.date_input("Invoice Date", value=datetime.now().date())

            st.markdown("---")
            st.markdown("##### 📦 Add Spares Listed in Bill")

            df_existing = pd.read_sql_query("SELECT item_name FROM main_inventory", conn)
            existing_list = df_existing["item_name"].tolist() if not df_existing.empty else []

            item_type = st.radio("Select Item Input Mode:", ["Select Existing Spare Part", "➕ Add New Spare Part Name"], horizontal=True)

            if item_type == "Select Existing Spare Part" and existing_list:
                sel_item = st.selectbox("Select Item", existing_list)
            else:
                sel_item = st.text_input("Enter New Spare Part Name").strip()

            item_qty = st.number_input("Received Quantity", min_value=1, value=10)
            item_cost = st.number_input("Purchase Price Per Unit (₹)", min_value=0.0, value=150.0)

            if st.button("➕ Add Item to Bill List"):
                if not sel_item:
                    st.error("Please specify a valid item name!")
                else:
                    st.session_state.inward_cart.append({
                        "item_name": sel_item,
                        "quantity": int(item_qty),
                        "unit_price": float(item_cost),
                        "subtotal": float(item_qty * item_cost)
                    })
                    st.success(f"Added {sel_item} (Qty: {item_qty}) to bill preview!")

        with col_inv_right:
            st.markdown("##### 🛒 Bill Items Preview")
            if not st.session_state.inward_cart:
                st.info("No items added to this invoice yet.")
            else:
                cart_df = pd.DataFrame(st.session_state.inward_cart)
                st.dataframe(cart_df[["item_name", "quantity", "unit_price", "subtotal"]], use_container_width=True)

                grand_total = cart_df["subtotal"].sum()
                st.markdown(f"### **Total Invoice Amount: ₹ {grand_total:,.2f}**")

                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("❌ Clear Current Entry"):
                        st.session_state.inward_cart = []
                        st.rerun()

                with c_btn2:
                    if st.button("✅ Process Invoice & Add to Stock"):
                        if not v_inv_no or not v_name:
                            st.error("Please fill in both Invoice Number and Supplier Name!")
                        elif not st.session_state.inward_cart:
                            st.error("Please add at least one item to the bill cart!")
                        else:
                            items_json = json.dumps(st.session_state.inward_cart)
                            inv_date_str = str(v_date)

                            try:
                                cursor.execute("INSERT INTO purchase_invoices VALUES (?, ?, ?, ?, ?)",
                                               (v_inv_no, v_name, inv_date_str, grand_total, items_json))
                                
                                for item in st.session_state.inward_cart:
                                    i_name = item["item_name"]
                                    i_qty = int(item["quantity"])
                                    i_rate = float(item["unit_price"])

                                    cursor.execute("SELECT total_stock FROM main_inventory WHERE item_name = ?", (i_name,))
                                    row = cursor.fetchone()

                                    if row:
                                        new_stock = int(row[0]) + i_qty
                                        cursor.execute("UPDATE main_inventory SET total_stock = ?, unit_price = ? WHERE item_name = ?",
                                                       (new_stock, i_rate, i_name))
                                    else:
                                        # Corrected: Exactly 5 values supplied for 5 columns
                                        cursor.execute("INSERT INTO main_inventory VALUES (?, ?, ?, ?, ?)",
                                                       (i_name, i_qty, 0, i_rate, 5))

                                    cursor.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?)",
                                                   (inv_date_str, "VENDOR_INVOICE_IN", v_name, i_name, i_qty, f"Bill No: {v_inv_no}"))

                                conn.commit()
                                st.session_state.inward_cart = []
                                st.success(f"Invoice #{v_inv_no} saved and stock successfully added to inventory!")
                                st.rerun()

                            except sqlite3.IntegrityError:
                                st.error(f"Invoice Number '{v_inv_no}' already exists in the system!")
                            except Exception as e:
                                st.error(f"An error occurred: {e}")

    with tab_history:
        st.markdown("##### 📜 All Received Supplier Invoices & Included Items")
        df_hist_inv = pd.read_sql_query("SELECT * FROM purchase_invoices ORDER BY invoice_date DESC", conn)

        if df_hist_inv.empty:
            st.info("No vendor invoices logged yet.")
        else:
            for _, row in df_hist_inv.iterrows():
                with st.expander(f"🧾 Bill No: {row['invoice_id']} | Vendor: {row['supplier_name']} | Date: {row['invoice_date']} | Total: ₹ {row['total_amount']:,.2f}"):
                    try:
                        items_list = json.loads(row['items_json'])
                        items_df = pd.DataFrame(items_list)
                        st.markdown("**📦 या बिलामध्ये आलेले स्पेअर पार्ट्स (Items List):**")
                        st.dataframe(items_df[["item_name", "quantity", "unit_price", "subtotal"]], use_container_width=True)
                    except Exception:
                        st.write("Could not parse items data.")

# PAGE 3: ISSUE STOCK TO TECHNICIAN
elif selected_nav == "📤 Issue Stock to Technician":
    st.subheader("📤 Issue Spare Parts to Field Technicians")
    df_tech = pd.read_sql_query("SELECT technician_name FROM technicians", conn)
    df_main = pd.read_sql_query("SELECT item_name, total_stock FROM main_inventory WHERE total_stock > 0", conn)

    if df_tech.empty or df_main.empty:
        st.warning("Please add technicians and stock items first.")
    else:
        with st.form("issue_stock_form"):
            t_target = st.selectbox("Technician", df_tech["technician_name"].tolist())
            i_target = st.selectbox("Material / Part", df_main["item_name"].tolist())
            issue_qty = st.number_input("Quantity to Issue", min_value=1, value=1)
            issue_date = st.date_input("Issue Date", value=datetime.now().date())

            if st.form_submit_button("Issue Material"):
                cursor.execute("SELECT total_stock FROM main_inventory WHERE item_name = ?", (i_target,))
                available = cursor.fetchone()[0]

                if available >= issue_qty:
                    cursor.execute("UPDATE main_inventory SET total_stock = ? WHERE item_name = ?", (available - issue_qty, i_target))

                    cursor.execute("SELECT quantity FROM technician_stock WHERE technician_name = ? AND item_name = ?", (t_target, i_target))
                    res = cursor.fetchone()
                    if res:
                        cursor.execute("UPDATE technician_stock SET quantity = ? WHERE technician_name = ? AND item_name = ?", (res[0] + issue_qty, t_target, i_target))
                    else:
                        cursor.execute("INSERT INTO technician_stock VALUES (?, ?, ?)", (t_target, i_target, issue_qty))

                    cursor.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?)",
                                   (str(issue_date), "GIVEN_TO_TECH", t_target, i_target, issue_qty, "Active With Tech"))
                    conn.commit()
                    st.success(f"Issued {issue_qty} x {i_target} to {t_target}!")
                    st.rerun()
                else:
                    st.error(f"Stock limit exceeded! Only {available} available in warehouse.")

# PAGE 4: DEFECTIVE RETURNS
elif selected_nav == "🔄 Defective Returns":
    st.subheader("🔄 Log Defective or Good Returns from Technicians")
    df_tech = pd.read_sql_query("SELECT technician_name FROM technicians", conn)

    if not df_tech.empty:
        sel_tech = st.selectbox("Select Technician", df_tech["technician_name"].tolist())
        df_assigned = pd.read_sql_query("SELECT item_name, quantity FROM technician_stock WHERE technician_name = ? AND quantity > 0", conn, params=(sel_tech,))

        if df_assigned.empty:
            st.info(f"No active material held by {sel_tech}.")
        else:
            st.dataframe(df_assigned, use_container_width=True)
            with st.form("defective_form"):
                d_item = st.selectbox("Returned Material Name", df_assigned["item_name"].tolist())
                d_qty = st.number_input("Returned Quantity", min_value=1, value=1)
                
                return_condition = st.radio(
                    "Return Condition (परताव्याचा प्रकार):", 
                    ["🟢 Good / Reusable Stock (नवा/चांगला स्टॉक परत)", "🔴 Defective Stock (डिफेक्टिव्ह पार्ट परत)"],
                    index=1
                )

                if st.form_submit_button("Record Return"):
                    cursor.execute("SELECT quantity FROM technician_stock WHERE technician_name = ? AND item_name = ?", (sel_tech, d_item))
                    held_qty_row = cursor.fetchone()
                    held_qty = held_qty_row[0] if held_qty_row else 0

                    if held_qty >= d_qty:
                        cursor.execute("UPDATE technician_stock SET quantity = ? WHERE technician_name = ? AND item_name = ?", (held_qty - d_qty, sel_tech, d_item))

                        if "Good / Reusable" in return_condition:
                            cursor.execute("SELECT total_stock FROM main_inventory WHERE item_name = ?", (d_item,))
                            curr_total_stk = cursor.fetchone()[0]
                            cursor.execute("UPDATE main_inventory SET total_stock = ? WHERE item_name = ?", (curr_total_stk + d_qty, d_item))
                            
                            cursor.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?)",
                                           (str(datetime.now().date()), "GOOD_RETURN_FROM_TECH", sel_tech, d_item, d_qty, "Returned to Main Stock"))
                            st.success(f"'{d_item}' ({d_qty} Qty) was returned in Good condition and added back to Main Warehouse Stock!")
                        else:
                            cursor.execute("SELECT defective_stock FROM main_inventory WHERE item_name = ?", (d_item,))
                            def_curr = cursor.fetchone()[0]
                            cursor.execute("UPDATE main_inventory SET defective_stock = ? WHERE item_name = ?", (def_curr + d_qty, d_item))

                            cursor.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?)",
                                           (str(datetime.now().date()), "DEFECTIVE_RETURN", sel_tech, d_item, d_qty, "Defective Returned"))
                            st.success(f"'{d_item}' ({d_qty} Qty) logged as Defective Return!")

                        conn.commit()
                        st.rerun()
                    else:
                        st.error("Error: Return quantity is greater than what technician currently holds!")

# PAGE 5: FIELD TECHNICIANS
elif selected_nav == "👷‍♂️ Field Technicians":
    st.subheader("👷‍♂️ Technician Roster & Issued Stock History")
    c_add, c_list = st.columns([1, 1])

    with c_add:
        with st.form("add_tech_f"):
            new_t = st.text_input("Technician Name").strip()
            if st.form_submit_button("Register Technician") and new_t:
                try:
                    cursor.execute("INSERT INTO technicians VALUES (?)", (new_t,))
                    conn.commit()
                    st.success(f"Registered {new_t}")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Technician already exists!")

    with c_list:
        techs_df = pd.read_sql_query("SELECT technician_name FROM technicians", conn)
        for _, row in techs_df.iterrows():
            ca, cb = st.columns([3, 1])
            ca.write(f"👷‍♂️ **{row['technician_name']}**")
            if cb.button("Remove", key=f"rm_{row['technician_name']}"):
                cursor.execute("DELETE FROM technicians WHERE technician_name = ?", (row['technician_name'],))
                conn.commit()
                st.rerun()

    st.markdown("---")
    st.markdown("### 🎒 Inventory Currently Held by Technicians")
    df_tech_stk = pd.read_sql_query("SELECT * FROM technician_stock WHERE quantity > 0", conn)
    st.dataframe(df_tech_stk, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📅 Date-wise Material History per Technician")
    sel_hist_tech = st.selectbox("Select Technician to View Date-wise History:", techs_df["technician_name"].tolist() if not techs_df.empty else [])
    if sel_hist_tech:
        df_tech_history = pd.read_sql_query(
            "SELECT date, transaction_type, item_name, quantity, status FROM history WHERE technician_name = ? ORDER BY date DESC",
            conn, params=(sel_hist_tech,)
        )
        if df_tech_history.empty:
            st.info(f"No history logs found for {sel_hist_tech}.")
        else:
            st.dataframe(df_tech_history, use_container_width=True)

# PAGE 6: SYSTEM HISTORY LOGS
elif selected_nav == "📜 System History Logs":
    st.subheader("📜 Complete Material Transaction History")
    df_hist = pd.read_sql_query("SELECT * FROM history ORDER BY date DESC", conn)

    if not df_hist.empty:
        st.download_button(
            label="📥 Export Logs to CSV",
            data=df_hist.to_csv(index=False).encode("utf-8"),
            file_name=f"Inventory_Log_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("No transaction history available.")

# PAGE 7: VAULT & USER PROFILE
elif selected_nav == "⚙️ Vault & User Profile":
    st.subheader("⚙️ User Profile & Account Settings")

    tab_edit_prof, tab_logout = st.tabs(["👤 Edit Profile", "🚪 Logout & Session"])

    with tab_edit_prof:
        st.markdown("##### ✏️ Update Active User Profile")
        with st.form("edit_profile_form"):
            edit_username = st.text_input("Username", value=st.session_state.current_user)
            edit_email = st.text_input("Email Address", value=st.session_state.user_email)
            edit_bio = st.text_area("Role / Bio", value=st.session_state.user_bio)
            edit_seed = st.text_input("Avatar Seed Key", value=st.session_state.avatar_seed)

            if st.form_submit_button("💾 Save Profile Changes"):
                st.session_state.current_user = edit_username
                st.session_state.user_email = edit_email
                st.session_state.user_bio = edit_bio
                st.session_state.avatar_seed = edit_seed

                cursor.execute("INSERT OR REPLACE INTO users (username, email, password, bio, avatar_seed) VALUES (?, ?, ?, ?, ?)",
                               (edit_username, edit_email, hash_password("default123"), edit_bio, edit_seed))
                conn.commit()
                st.success("Profile updated successfully!")
                st.rerun()

    with tab_logout:
        st.markdown("##### 🔐 Active Session Management")
        st.info(f"Currently logged in as: **@{st.session_state.current_user}** ({st.session_state.user_email})")

        if st.button("🚪 Logout From App"):
            st.session_state.logged_in = False
            st.session_state.current_user = "Guest"
            st.session_state.user_email = ""
            st.rerun()
