import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(
    page_title="Chef de Département",
    layout="wide"
)

st.title("Chef de Département – Gestion des Examens")


conn = psycopg2.connect(
    host="localhost",
    database="exams_db",    
    user="postgres",
    password="ikramhm022"   
)


query_stats = """
SELECT f.nom AS formation, COUNT(e.id) AS nombre_examens
FROM planning.formations f
LEFT JOIN planning.modules m ON m.formation_id = f.id
LEFT JOIN planning.examens e ON e.module_id = m.id
WHERE f.dept_id = 1
GROUP BY f.nom;
"""

query_examens = """
SELECT 
    e.id,
    f.nom AS formation,
    m.nom AS module,
    p.nom AS professeur,
    l.nom AS salle,
    e.date_heure,
    e.duree_minutes,
    e.statut
FROM planning.examens e
JOIN planning.modules m ON e.module_id = m.id
JOIN planning.formations f ON m.formation_id = f.id
JOIN planning.professeurs p ON e.prof_id = p.id
JOIN planning.lieu_examen l ON e.salle_id = l.id
WHERE f.dept_id = 1
ORDER BY e.date_heure;
"""

query_conflits = """
SELECT 
    f.nom AS formation,
    DATE(e.date_heure) AS jour,
    COUNT(e.id) AS nb_examens
FROM planning.examens e
JOIN planning.modules m ON e.module_id = m.id
JOIN planning.formations f ON m.formation_id = f.id
WHERE f.dept_id = 1
GROUP BY f.nom, DATE(e.date_heure)
HAVING COUNT(e.id) > 1;
"""


df_stats = pd.read_sql(query_stats, conn)
df_examens = pd.read_sql(query_examens, conn)
df_conflits = pd.read_sql(query_conflits, conn)

st.sidebar.title("Menu")

menu = st.sidebar.radio(
    "Navigation",
    ["📊 Statistiques", "📋 Examens", "⚠️ Conflits par formation", "✅ Validation"]
)

if st.sidebar.button("🚪 Déconnexion"):
    st.session_state.clear()
    st.success("Vous êtes déconnecté ✅")
    st.stop()

if menu == "📊 Statistiques":
    st.subheader("📊 Statistiques par formation")
    st.dataframe(df_stats, use_container_width=True)


elif menu == "📋 Examens":
    st.subheader("📋 Examens du département")
    st.dataframe(df_examens, use_container_width=True)


elif menu == "⚠️ Conflits par formation":
    st.subheader("⚠️ Conflits par formation")
    if df_conflits.empty:
        st.success("✅ Aucun conflit détecté")
    else:
        st.warning("⚠️ Des conflits ont été détectés")
        st.dataframe(df_conflits, use_container_width=True)


elif menu == "✅ Validation":
    st.subheader("✅ Validation des examens")
    examens_attente = df_examens[df_examens["statut"] == "en attente"]

    if examens_attente.empty:
        st.success("Tous les examens sont validés")
    else:
        exam_id = st.selectbox(
            "Choisir un examen à valider",
            examens_attente["id"]
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Valider"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE planning.examens SET statut='validé' WHERE id=%s",
                    (exam_id,)
                )
                conn.commit()
                st.success("Examen validé")
                st.experimental_rerun()

        with col2:
            if st.button("❌ Refuser"):
                cur = conn.cursor()
                cur.execute(
                    "UPDATE planning.examens SET statut='refusé' WHERE id=%s",
                    (exam_id,)
                )
                conn.commit()
                st.warning("Examen refusé")
                st.experimental_rerun()
