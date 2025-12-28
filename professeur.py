import psycopg2
import pandas as pd
import streamlit as st

# Charger Bootstrap via un lien CDN
st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
""", unsafe_allow_html=True)


st.set_page_config(
    page_title="Interface Professeur",
    layout="wide"
)

st.title("Interface Professeur – Gestion des Examens")


conn = psycopg2.connect(
    host="localhost",
    database="exams_db",  
    user="postgres",
    password="ikramhm022"   
)


menu = st.sidebar.radio(
    "Navigation",
    ["📋 Mes Examens", "➕ Proposer un examen", "⚠️ Conflits", "👀 Mes surveillances"]
)


if menu == "📋 Mes Examens":
    st.subheader("📋 Examens programmés par moi")

    query = """
    SELECT e.id, m.nom AS module, l.nom AS salle, e.date_heure, e.duree_minutes, e.statut
    FROM planning.examens e
    JOIN planning.modules m ON e.module_id = m.id
    JOIN planning.lieu_examen l ON e.salle_id = l.id
    WHERE e.prof_id = 1   -- ⚠️ Id du professeur connecté
    ORDER BY e.date_heure;
    """
    df_examens = pd.read_sql(query, conn)
    st.dataframe(df_examens, use_container_width=True)

elif menu == "➕ Proposer un examen":
    st.subheader("➕ Proposer un nouvel examen")

    module_id = st.number_input("Module ID", min_value=1)
    salle_id = st.number_input("Salle ID", min_value=1)
    date_heure = st.date_input("Date") 
    heure = st.time_input("Heure")
    duree = st.number_input("Durée (minutes)", min_value=30, max_value=360)

    if st.button("📌 Soumettre"):
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO planning.examens (module_id, prof_id, salle_id, date_heure, duree_minutes, statut)
            VALUES (%s, %s, %s, %s, %s, 'en attente')
        """, (module_id, 1, salle_id, f"{date_heure} {heure}", duree))  # ⚠️ prof_id = 1
        conn.commit()
        st.success("Examen proposé avec succès ✅")

elif menu == "⚠️ Conflits":
    st.subheader("⚠️ Conflits détectés pour mes examens")

    query_conf = """
    SELECT DATE(e.date_heure) AS jour, COUNT(e.id) AS nb_examens
    FROM planning.examens e
    WHERE e.prof_id = 1
    GROUP BY DATE(e.date_heure)
    HAVING COUNT(e.id) > 1;
    """
    df_conf = pd.read_sql(query_conf, conn)

    if df_conf.empty:
        st.success("✅ Aucun conflit détecté")
    else:
        st.warning("⚠️ Conflits détectés")
        st.dataframe(df_conf, use_container_width=True)


elif menu == "👀 Mes surveillances":
    st.subheader("👀 Surveillances attribuées")

    query_surv = """
    SELECT s.id, e.date_heure, m.nom AS module, l.nom AS salle, s.priorite_dept
    FROM planning.surveillances s
    JOIN planning.examens e ON s.examen_id = e.id
    JOIN planning.modules m ON e.module_id = m.id
    JOIN planning.lieu_examen l ON e.salle_id = l.id
    WHERE s.prof_id = 1;
    """
    df_surv = pd.read_sql(query_surv, conn)
    st.dataframe(df_surv, use_container_width=True)

