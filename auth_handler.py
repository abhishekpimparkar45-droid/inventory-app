import streamlit as st

def check_user_login():
    # Hardcoded Master Credentials provided by you
    MASTER_USERNAME = "Abhishek_Pimparkar"
    MASTER_PASSWORD = "Abhi@045"

    # Initialize session state variables if not already present
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "current_user_role" not in st.session_state:
        st.session_state.current_user_role = None
    if "current_user" not in st.session_state:
        st.session_state.current_user = "ActiveUser"

    # If the user is not authenticated, show the login/auth gate
    if not st.session_state.is_authenticated:
        st.markdown("""
            <div style='text-align: center; padding: 20px;'>
                <h2 style='color: #00F5FF;'>🔐 Elite Inventory Security Portal</h2>
                <p style='color: #9CA3AF;'>Enter master credentials for main inventory, or enter a new username to create a fresh guest session on this device.</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_auth_form"):
            col1, col2 = st.columns([1, 1])
            with col1:
                u_name = st.text_input("Username").strip()
            with col2:
                u_pass = st.text_input("Password", type="password").strip()
            
            submit = st.form_submit_button("🚀 Access App")
            
            if submit:
                if u_name == MASTER_USERNAME and u_pass == MASTER_PASSWORD:
                    # Master User: Loads the main existing dataset
                    st.session_state.is_authenticated = True
                    st.session_state.current_user_role = "MASTER"
                    st.session_state.current_user = MASTER_USERNAME
                    st.success("Master Login Successful! Loading main inventory...")
                    st.rerun()
                elif u_name != "" and u_pass != "":
                    # New/Guest User on a new device: Gets a clean isolated session
                    st.session_state.is_authenticated = True
                    st.session_state.current_user_role = "NEW_USER"
                    st.session_state.current_user = u_name
                    st.success(f"New User Session Created for @{u_name}!")
                    st.rerun()
                else:
                    st.error("Please enter a valid username and password.")
        
        # Stops the main app execution until login is successful
        st.stop()
