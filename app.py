import streamlit as st
from auth import authenticate
from interfaces import doyen, adminexamen, professeur, etudiant, chefdept

# Configuration globale
st.set_page_config(
    page_title="Plateforme d’Optimisation des Examens",
    layout="wide"
)

# Style professionnel (Bootstrap-like)
st.markdown("""
<style>
/* Conteneur principal */
.block-container {
    padding: 3rem 4rem;
    font-family: 'Arial', sans-serif;
    background-color: #f4f5f7;
}

/* Titres */
h1, h2, h3 {
    color: #222;
    font-weight: 600;
    text-align: center;
    margin-bottom: 2rem;
}

/* Sidebar */
.sidebar .sidebar-content {
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
    padding: 1rem 1.5rem;
    font-size: 0.95rem;
}

/* Boutons */
.stButton>button {
    background-color: #004085;
    color: white;
    border-radius: 4px;
    border: none;
    padding: 0.6rem 1.2rem;
    font-weight: 500;
}
.stButton>button:hover {
    background-color: #002752;
}

/* Formulaire login */
input[type=text], input[type=password] {
    border-radius: 4px;
    border: 1px solid #cccccc;
    padding: 0.6rem;
    width: 100%;
    margin-bottom: 1rem;
    font-size: 1rem;
}

/* Alertes */
.stAlert {
    font-weight: 500;
}

/* Metrics / KPI cards */
.stMetric {
    background-color: #ffffff;
    padding: 1rem;
    border-radius: 6px;
    border: 1px solid #dcdcdc;
}

/* Tables */
.dataframe tbody tr:hover { 
    background-color: #f1f1f1; 
}
.dataframe thead {
    background-color: #e9ecef;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# Session
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# Page login
def login_page():
    st.write("")  # espace haut
    st.markdown("<h1>Connexion</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
    if submit:
        user = authenticate(email, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Identifiants incorrects")

# Routage principal
if not st.session_state.logged_in:
    login_page()
else:
    user = st.session_state.user
    role = user["role"]

    if role in ["doyen", "vice-doyen"]:
        doyen.interface_doyen(user)
    elif role == "admin":
        adminexamen.interface_adminexamen(user)
    elif role == ["chef_dept"]:
        chefdept.interface_chefdept(user)
    elif role == "professeur":
        professeur.interface_professeur(user)
    elif role == "etudiant":
        etudiant.interface_etudiant(user)
    else:
        st.error("Rôle non reconnu")
