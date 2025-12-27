import streamlit as st
import pandas as pd
from db import get_connection

# =====================================
# UTILITAIRE : vérifier si une vue existe
# =====================================
def vue_existe(conn, schema, vue):
    q = """
    SELECT 1
    FROM information_schema.views
    WHERE table_schema = %s AND table_name = %s
    """
    df = pd.read_sql(q, conn, params=(schema, vue))
    return not df.empty

# =====================================
# INTERFACE DOYEN / VICE-DOYEN
# =====================================
def interface_doyen(user):

    # ---------- CSS professionnel ----------
    st.markdown("""
    <style>
    /* Sidebar */
    .sidebar .sidebar-content {
        background-color: #ffffff;
        border-right: 1px solid #dcdcdc;
        padding: 1rem 1.5rem;
        font-size: 0.95rem;
        font-family: 'Arial', sans-serif;
    }

    /* Titres */
    h1, h2, h3 { color: #1a1a1a; font-weight: 600; }

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

    /* Metrics / KPI cards */
    .stMetric {
        background-color:  #cce7ff;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #dcdcdc;
    }

    /* Tables */
    .dataframe tbody tr:hover { background-color: #f1f1f1; }
    .dataframe thead { background-color: #e9ecef; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    # ---------- SIDEBAR ----------
    with st.sidebar:
        
        st.divider()

        menu = st.radio(
            "Navigation",
            ["Tableau de bord", "Emplois du temps", "Indicateurs", "Rapports"],
            index=0
        )

        if st.button("Se déconnecter", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()

    st.title("Plateforme d’Optimisation des Examens")
    conn = get_connection()

    # =======================
    # TABLEAU DE BORD
    # =======================
    if menu == "Tableau de bord":

        c1, c2, c3, c4 = st.columns(4)

        exams_count = pd.read_sql("SELECT COUNT(*) FROM planning.examens", conn).iloc[0,0]
        students_count = pd.read_sql("SELECT COUNT(*) FROM planning.etudiants", conn).iloc[0,0]
        rooms_count = pd.read_sql("SELECT COUNT(*) FROM planning.lieu_examen", conn).iloc[0,0]
        professors_count = pd.read_sql("SELECT COUNT(*) FROM planning.professeurs", conn).iloc[0,0]

        c1.metric("Examens", exams_count)
        c2.metric("Étudiants", students_count)
        c3.metric("Salles", rooms_count)
        c4.metric("Professeurs", professors_count)

        st.subheader("Occupation des salles / Amphis")
        if not vue_existe(conn, "planning", "v_occupation_salles"):
            st.warning("La vue v_occupation_salles n’existe pas encore. Création automatique...")
            cur = conn.cursor()
            cur.execute("""
                CREATE OR REPLACE VIEW planning.v_occupation_salles AS
                SELECT 
                    l.id AS salle_id,
                    l.nom AS salle_nom,
                    COALESCE(COUNT(i.etudiant_id),0) AS nb_inscrits,
                    l.capacite,
                    ROUND(COALESCE(COUNT(i.etudiant_id),0)::numeric / NULLIF(l.capacite,0) * 100, 2) AS taux_occupation
                FROM planning.lieu_examen l
                LEFT JOIN planning.examens e ON e.salle_id = l.id
                LEFT JOIN planning.inscriptions i ON i.examen_id = e.id
                GROUP BY l.id, l.nom, l.capacite
                ORDER BY l.nom;
            """)
            conn.commit()
            st.success("Vue v_occupation_salles créée avec succès !")

        df_salles = pd.read_sql("SELECT * FROM planning.v_occupation_salles", conn)

        # Coloration simple
        def color_row(row):
            if row['taux_occupation'] > 90:
                return ['background-color: #f3f6f4']*len(row)
            elif row['taux_occupation'] > 70:
                return ['background-color: #f3f6f4']*len(row)
            else:
                return ['background-color: #f3f6f4']*len(row)

        st.dataframe(df_salles.style.apply(color_row, axis=1), use_container_width=True)
        st.bar_chart(df_salles.set_index('salle_nom')['taux_occupation'])

        st.subheader("Conflits détectés")
        df_conflicts = pd.read_sql("""
            SELECT e1.id AS exam1, e2.id AS exam2, e1.date_heure AS date_heure, l.nom AS salle
            FROM planning.examens e1
            JOIN planning.examens e2 ON e1.id < e2.id AND e1.date_heure = e2.date_heure
            JOIN planning.lieu_examen l ON e1.salle_id = l.id AND e1.salle_id = e2.salle_id
        """, conn)
        if df_conflicts.empty:
            st.success("Aucun conflit détecté")
        else:
            st.error(f"{len(df_conflicts)} conflit(s) détecté(s)")
            st.dataframe(df_conflicts)

    # =======================
    # EMPLOIS DU TEMPS
    # =======================
    elif menu == "Emplois du temps":
        st.subheader("Emplois du temps des examens")
        df = pd.read_sql("""
            SELECT e.id AS exam_id,
                   m.nom AS module,
                   l.nom AS salle,
                   e.date_heure,
                   e.duree_minutes
            FROM planning.examens e
            JOIN planning.modules m ON e.module_id = m.id
            JOIN planning.lieu_examen l ON e.salle_id = l.id
            ORDER BY e.date_heure
        """, conn)
        st.dataframe(df, use_container_width=True)
        if st.button("Valider définitivement l’EDT"):
            st.success("Emploi du temps validé avec succès !")

    # =======================
    # INDICATEURS
    # =======================
    elif menu == "Indicateurs":
        st.subheader("Nombre d'examens par département")
        df = pd.read_sql("""
            SELECT d.nom AS departement,
                   COUNT(e.id) AS nb_examens
            FROM planning.departements d
            LEFT JOIN planning.formations f ON f.dept_id = d.id
            LEFT JOIN planning.modules m ON m.formation_id = f.id
            LEFT JOIN planning.examens e ON e.module_id = m.id
            GROUP BY d.nom
        """, conn)
        st.bar_chart(df.set_index("departement"))

        st.subheader("Taux d'utilisation des salles par département")
        df_salles_dep = pd.read_sql("""
            SELECT d.nom AS departement,
                   ROUND(AVG(occup.nb_etudiants::numeric / NULLIF(occup.capacite,0) * 100),2) AS taux_utilisation
            FROM planning.departements d
            LEFT JOIN planning.formations f ON f.dept_id = d.id
            LEFT JOIN planning.modules m ON m.formation_id = f.id
            LEFT JOIN planning.examens e ON e.module_id = m.id
            LEFT JOIN planning.lieu_examen l ON e.salle_id = l.id
            LEFT JOIN (
                SELECT e.salle_id, COUNT(i.etudiant_id) AS nb_etudiants, l.capacite
                FROM planning.examens e
                LEFT JOIN planning.inscriptions i ON i.examen_id = e.id
                LEFT JOIN planning.lieu_examen l ON e.salle_id = l.id
                GROUP BY e.salle_id, l.capacite
            ) AS occup ON occup.salle_id = l.id
            GROUP BY d.nom
            ORDER BY d.nom
        """, conn)
        st.bar_chart(df_salles_dep.set_index("departement"))

    # =======================
    # RAPPORTS
    # =======================
    elif menu == "Rapports":
        st.subheader("Export des examens")
        df = pd.read_sql("""
            SELECT m.nom AS module,
                   l.nom AS salle,
                   e.date_heure,
                   p.nom AS professeur
            FROM planning.examens e
            JOIN planning.modules m ON e.module_id = m.id
            JOIN planning.lieu_examen l ON e.salle_id = l.id
            JOIN planning.professeurs p ON e.prof_id = p.id
        """, conn)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Exporter en CSV",
            csv,
            "examens_valides.csv",
            "text/csv"
        )

    conn.close()
