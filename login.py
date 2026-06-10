import streamlit as st


def show_login_page(authenticate):
    st.markdown(
        """
        <style>
        /* =========================
           HILANGKAN BAWAAN STREAMLIT
        ========================= */
        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        header {
            visibility: hidden;
        }

        [data-testid="stToolbar"] {
            display: none !important;
        }

        [data-testid="stDecoration"] {
            display: none !important;
        }

        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        [data-testid="stHeader"] {
            display: none !important;
        }

        /* =========================
           BACKGROUND HALAMAN
        ========================= */
        [data-testid="stAppViewContainer"] {
            background-color: #f5f5f7 !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            background-color: #f5f5f7 !important;
        }

        .block-container {
            max-width: 100% !important;
            min-height: 100vh !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;

            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

        /* =========================
           CARD LOGIN
        ========================= */
        div[data-testid="stForm"] {
            width: 445px !important;
            background: #ffffff !important;
            border: 1px solid #e7e7e7 !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04) !important;
            padding: 34px 34px 28px 34px !important;
            margin: 0 auto !important;
        }

        /* Hilangkan border bawaan form */
        div[data-testid="stForm"] > div {
            border: none !important;
        }

        /* =========================
           BRAND / TITLE
        ========================= */
        .brand-title {
            text-align: center;
            font-size: 18px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 10px;
        }

        .login-title {
            text-align: center;
            font-size: 22px;
            font-weight: 800;
            color: #111827;
            margin-bottom: 6px;
        }

        .signup-text {
            text-align: center;
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 24px;
        }

        .signup-text a {
            color: #4f46e5;
            text-decoration: none;
            font-weight: 600;
        }

        /* =========================
           LABEL INPUT
        ========================= */
        div[data-testid="stTextInput"] label {
            margin-bottom: 4px !important;
        }

        div[data-testid="stTextInput"] label p {
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #111827 !important;
        }

        /* =========================
           INPUT
        ========================= */
        div[data-testid="stTextInput"] {
            margin-bottom: 14px !important;
        }

        div[data-baseweb="input"] {
            min-height: 44px !important;
            border-radius: 10px !important;
            border: 1px solid #d9dce3 !important;
            background-color: #ffffff !important;
            box-shadow: none !important;
        }

        div[data-baseweb="input"]:focus-within {
            border: 1px solid #6d5dfc !important;
            box-shadow: 0 0 0 2px rgba(109, 93, 252, 0.10) !important;
        }

        div[data-baseweb="input"] input {
            height: 44px !important;
            font-size: 14px !important;
            color: #111827 !important;
            background-color: #ffffff !important;
            padding-left: 12px !important;
        }

        div[data-baseweb="input"] input::placeholder {
            color: #9ca3af !important;
        }

        div[data-baseweb="input"] button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* =========================
           CHECKBOX
        ========================= */
        div[data-testid="stCheckbox"] {
            margin-top: 2px !important;
            margin-bottom: 20px !important;
        }

        div[data-testid="stCheckbox"] label p {
            font-size: 14px !important;
            color: #111827 !important;
            font-weight: 500 !important;
        }

        /* =========================
           TOMBOL SIGN IN
        ========================= */
        div[data-testid="stFormSubmitButton"] {
            margin-top: 2px !important;
        }

        div[data-testid="stFormSubmitButton"] button {
            width: 100% !important;
            height: 44px !important;
            border: none !important;
            border-radius: 10px !important;
            background: linear-gradient(90deg, #5b4cf0 0%, #4f46e5 100%) !important;
            color: #ffffff !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }

        div[data-testid="stFormSubmitButton"] button:hover {
            background: linear-gradient(90deg, #5143de 0%, #4338ca 100%) !important;
            color: #ffffff !important;
            border: none !important;
        }

        div[data-testid="stFormSubmitButton"] button:focus {
            color: #ffffff !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* =========================
           ALERT
        ========================= */
        div[data-testid="stAlert"] {
            width: 445px !important;
            margin: 14px auto 0 auto !important;
            border-radius: 10px !important;
            font-size: 13px !important;
        }

        /* =========================
           RESPONSIVE
        ========================= */
        @media screen and (max-width: 768px) {
            div[data-testid="stForm"] {
                width: 92% !important;
                padding: 28px 22px 24px 22px !important;
            }

            div[data-testid="stAlert"] {
                width: 92% !important;
            }

            .login-title {
                font-size: 20px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.form("login_form"):
        st.markdown(
            """
            <div class="brand-title">SISTEM PAKAR DIAGNOSA PENYAKIT BAYI</div>
            <div class="login-title">Sign in</div>
            """,
            unsafe_allow_html=True
        )

        username = st.text_input("Username", placeholder="")
        password = st.text_input("Password", type="password", placeholder="")
        remember_me = st.checkbox("Remember me")

        submitted = st.form_submit_button("Sign in")

        if submitted:
            if not username or not password:
                st.error("Username dan password harus diisi!")
            else:
                user = authenticate(username, password)

                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.remember_me = remember_me
                    st.rerun()
                else:
                    st.error("Username atau password salah!")