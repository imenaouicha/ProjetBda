# admin.py - Interface Admin CONNECTÉE à PostgreSQL
import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import time

# ============================================
# CONNEXION À POSTGRESQL
# ============================================

@st.cache_resource
def init_connection():
    """Initialise la connexion à PostgreSQL avec encodage UTF-8"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="exams_db",
            user="postgres",        # à remplacer
            password="sarah",       # à remplacer
            options='-c client_encoding=UTF8'
        )
        return conn
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données: {e}")
        return None

conn = init_connection()

def execute_query(query, params=None):
    if conn:
        try:
            return pd.read_sql(query, conn, params=params)
        except Exception as e:
            st.error(f"Erreur SQL: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def execute_update(query, params=None):
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Erreur mise à jour: {e}")
            return False
    return False

# ============================================
# CONFIGURATION DE LA PAGE
# ============================================

st.set_page_config(
    page_title="Admin - Planning Examens",
    page_icon="🔧",
    layout="wide"
)

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.title("Administration")
    st.markdown("---")

    
    page = st.radio(
        "Navigation",
        ["Génération EDT", "Détection Conflits", "Optimisation Ressources"]
    )
    
    st.markdown(f"**Date :** {datetime.now().strftime('%d/%m/%Y')}")
    
    if st.button("Déconnexion", use_container_width=True): 
        st.success("Déconnecté !")

# ============================================
# PAGE: GÉNÉRATION EDT
# ============================================
if page == "Génération EDT":
    st.title("Génération automatique d'EDT")

    # -----------------------------
    # Sélection du périmètre
    # -----------------------------
    st.header("Sélection du périmètre")

    df_dept = execute_query(
        "SELECT id, nom FROM planning.departements ORDER BY nom;"
    )

    departement = st.selectbox(
        "Département",
        df_dept["nom"].tolist(),
        key="gen_dept"
    )

    dept_id = int(
        df_dept.loc[df_dept["nom"] == departement, "id"].iloc[0]
    )

    df_form = execute_query(
        "SELECT id, nom FROM planning.formations WHERE dept_id = %s ORDER BY nom;",
        (dept_id,)
    )

    if df_form.empty:
        st.error("Aucune formation trouvée")
        formation_id = None
    else:
        formation = st.selectbox(
            "Formation",
            df_form["nom"].tolist(),
            key="gen_form"
        )
        formation_id = int(
            df_form.loc[df_form["nom"] == formation, "id"].iloc[0]
        )

    # -----------------------------
    # Période
    # -----------------------------
    with st.form("form_gen_edt"):
        col1, col2 = st.columns(2)
        with col1:
            date_debut = st.date_input(
                "Date début",
                value=datetime.now(),
                key="gen_date_debut"
            )
        with col2:
            date_fin = st.date_input(
                "Date fin",
                value=datetime.now() + timedelta(days=14),
                key="gen_date_fin"
            )

        submit = st.form_submit_button("Générer EDT")

    # -----------------------------
    # Génération réelle
    # -----------------------------
    if submit:
        if formation_id is None:
            st.error("Formation invalide")
        else:
            with st.spinner("Génération en cours..."):
                progress = st.progress(0)

                modules = execute_query(
                    "SELECT id, nom FROM planning.modules WHERE formation_id = %s;",
                    (formation_id,)
                )

                salles = execute_query(
                    "SELECT id, nom FROM planning.lieu_examen ORDER BY capacite DESC;"
                )

                if modules.empty or salles.empty:
                    st.error("Modules ou salles manquants")
                else:
                    inserted = []
                    failed = []

                    total = len(modules)

                    for i, row in modules.iterrows():
                        module_id = int(row["id"])
                        module_nom = row["nom"]

                        salle = salles.iloc[i % len(salles)]
                        salle_id = int(salle["id"])
                        salle_nom = salle["nom"]

                        jour = i % max(1, (date_fin - date_debut).days + 1)
                        exam_date = date_debut + timedelta(days=jour)
                        exam_time = datetime.strptime("08:00", "%H:%M").time()
                        exam_datetime = datetime.combine(exam_date, exam_time) + timedelta(hours=(i % 5) * 2)

                        query_insert = """
                            INSERT INTO planning.examens
                            (module_id, prof_id, salle_id, date_heure, duree_minutes)
                            SELECT %s, p.id, %s, %s, 120
                            FROM planning.professeurs p
                            WHERE p.dept_id = %s
                            LIMIT 1;
                        """

                        ok = execute_update(
                            query_insert,
                            (
                                module_id,
                                salle_id,
                                exam_datetime,
                                dept_id
                            )
                        )

                        if ok:
                            inserted.append({
                                "Matiere": module_nom,
                                "Salle": salle_nom,
                                "Date_Heure": exam_datetime
                            })
                        else:
                            failed.append({
                                "Matiere": module_nom,
                                "Raison": "Trigger ou insertion refusée"
                            })

                        progress.progress(int((i + 1) / total * 100))

                    if inserted:
                        st.success("EDT généré")
                        st.dataframe(pd.DataFrame(inserted), use_container_width=True)

                    if failed:
                        st.warning("Certains examens n'ont pas été générés")
                        st.dataframe(pd.DataFrame(failed), use_container_width=True)


# ============================================
# PAGE: DÉTECTION CONFLITS
# ============================================

elif page == "Détection Conflits":
    st.title("Détection des conflits")
    
    if st.button("Scanner les conflits", type="primary", use_container_width=True):
        # Récupération de tous les examens
        query_examens = """
        SELECT 
            e.id,
            e.module_id,
            e.prof_id,
            e.salle_id,
            e.date_heure,
            e.duree_minutes,
            p.nom as professeur,
            l.nom as salle
        FROM planning.examens e
        JOIN planning.professeurs p ON e.prof_id = p.id
        JOIN planning.lieu_examen l ON e.salle_id = l.id;
        """
        df_examens = execute_query(query_examens)

        # Récupération des inscriptions étudiants avec examen_id
        query_inscriptions = """
        SELECT 
            s.etudiant_id,
            s.module_id,
            s.examen_id
        FROM planning.inscriptions s
        WHERE s.examen_id IS NOT NULL;
        """
        df_inscriptions = execute_query(query_inscriptions)

        if df_examens.empty:
            st.success("✅ Aucun examen dans la base")
        else:
            # Calcul date de fin
            df_examens['date_fin'] = df_examens['date_heure'] + pd.to_timedelta(df_examens['duree_minutes'], unit='m')

            conflits = []

            # Détection conflits salle et prof
            for i, e1 in df_examens.iterrows():
                for j, e2 in df_examens.iterrows():
                    if i >= j:
                        continue
                    # Salle
                    if e1['salle_id'] == e2['salle_id'] and not (e1['date_fin'] <= e2['date_heure'] or e2['date_fin'] <= e1['date_heure']):
                        conflits.append({
                            "Type": "Salle surchargée",
                            "Détails": f"Salle {e1['salle']} a 2 examens qui se chevauchent entre {e1['date_heure']} et {e1['date_fin']}"
                        })
                    # Prof
                    if e1['prof_id'] == e2['prof_id'] and not (e1['date_fin'] <= e2['date_heure'] or e2['date_fin'] <= e1['date_heure']):
                        conflits.append({
                            "Type": "Conflit professeur",
                            "Détails": f"Professeur {e1['professeur']} a 2 examens qui se chevauchent entre {e1['date_heure']} et {e1['date_fin']}"
                        })

            # Détection conflits étudiants
            if not df_inscriptions.empty:
                # Fusion sur examen_id pour récupérer les vrais examens de chaque étudiant
                df_etud_exam = df_inscriptions.merge(df_examens, left_on='examen_id', right_on='id', how='inner')
                for i, e1 in df_etud_exam.iterrows():
                    for j, e2 in df_etud_exam.iterrows():
                        if i >= j:
                            continue
                        if e1['etudiant_id'] == e2['etudiant_id'] and not (e1['date_fin'] <= e2['date_heure'] or e2['date_fin'] <= e1['date_heure']):
                            conflits.append({
                                "Type": "Conflit étudiant",
                                "Détails": f"Étudiant ID {e1['etudiant_id']} a 2 examens qui se chevauchent entre {e1['date_heure']} et {e1['date_fin']}"
                            })

            if not conflits:
                st.success("✅ Aucun conflit détecté !")
            else:
                # Déduplication
                conflits_df = pd.DataFrame(conflits).drop_duplicates(subset=["Type","Détails"])
                st.dataframe(conflits_df, use_container_width=True)

# ============================================
# PAGE: OPTIMISATION DES RESSOURCE
# ============================================
elif page == "Optimisation Ressources":
    st.title("Optimisation des ressources")
    
    if st.button("Optimiser toutes les ressources", type="primary"):
        st.info("Optimisation en cours...")

        # Récupération des données
        df_examens = execute_query("""
            SELECT e.id as examen_id, e.module_id, e.prof_id, e.salle_id, e.date_heure, e.duree_minutes
            FROM planning.examens e;
        """)
        df_salles = execute_query("""
            SELECT id as salle_id, nom, capacite
            FROM planning.lieu_examen
            ORDER BY capacite DESC;
        """)
        df_inscriptions = execute_query("""
            SELECT etudiant_id, examen_id
            FROM planning.inscriptions
            WHERE examen_id IS NOT NULL;
        """)

        if df_examens.empty or df_salles.empty:
            st.warning("Aucun examen ou salle trouvé pour optimiser")
        else:
            df_examens['date_fin'] = df_examens['date_heure'] + pd.to_timedelta(df_examens['duree_minutes'], unit='m')
            optimisation = []

            # Liste de créneaux possibles (ex: 8h-10h, 10h-12h…)
            debut_jour = datetime.strptime("08:00:00", "%H:%M:%S").time()
            fin_jour = datetime.strptime("18:00:00", "%H:%M:%S").time()
            duree_creneau = 120  # en minutes
            heures_creneaux = [datetime.combine(datetime.today(), debut_jour) + timedelta(minutes=120*i) 
                               for i in range(int((fin_jour.hour - debut_jour.hour)*60/duree_creneau))]

            for i, examen in df_examens.iterrows():
                affecte = False
                etudiants_exam = df_inscriptions[df_inscriptions['examen_id'] == examen['examen_id']]['etudiant_id'].tolist()
                
                # Essayer d'affecter sur le créneau initial
                for j, salle in df_salles.iterrows():
                    salle_dispo = all(
                        (examen['date_fin'] <= e['date_heure'] or e['date_fin'] <= examen['date_heure'])
                        for e in optimisation if e['salle_id'] == salle['salle_id']
                    )
                    prof_dispo = all(
                        (examen['date_fin'] <= e['date_heure'] or e['date_fin'] <= examen['date_heure'])
                        for e in optimisation if e['prof_id'] == examen['prof_id']
                    )
                    etudiants_dispo = all(
                        (examen['date_fin'] <= e['date_heure'] or e['date_fin'] <= examen['date_heure'])
                        for e in optimisation if e.get('etudiants', []) and set(e['etudiants']) & set(etudiants_exam)
                    )
                    if salle_dispo and prof_dispo and etudiants_dispo:
                        optimisation.append({
                            "examen_id": examen['examen_id'],
                            "salle_id": salle['salle_id'],
                            "Salle": salle['nom'],
                            "prof_id": examen['prof_id'],
                            "date_heure": examen['date_heure'],
                            "date_fin": examen['date_fin'],
                            "etudiants": etudiants_exam
                        })
                        # Mise à jour salle dans la base
                        execute_update(
                            "UPDATE planning.examens SET salle_id = %s WHERE id = %s",
                            (salle['salle_id'], examen['examen_id'])
                        )
                        affecte = True
                        break

                # Si conflit, tenter de déplacer sur un autre créneau
                if not affecte:
                    for h in heures_creneaux:
                        nouvel_debut = examen['date_heure'].replace(hour=h.hour, minute=h.minute)
                        nouvel_fin = nouvel_debut + timedelta(minutes=examen['duree_minutes'])
                        for j, salle in df_salles.iterrows():
                            salle_dispo = all(
                                (nouvel_fin <= e['date_heure'] or e['date_fin'] <= nouvel_debut)
                                for e in optimisation if e['salle_id'] == salle['salle_id']
                            )
                            prof_dispo = all(
                                (nouvel_fin <= e['date_heure'] or e['date_fin'] <= nouvel_debut)
                                for e in optimisation if e['prof_id'] == examen['prof_id']
                            )
                            etudiants_dispo = all(
                                (nouvel_fin <= e['date_heure'] or e['date_fin'] <= nouvel_debut)
                                for e in optimisation if e.get('etudiants', []) and set(e['etudiants']) & set(etudiants_exam)
                            )
                            if salle_dispo and prof_dispo and etudiants_dispo:
                                optimisation.append({
                                    "examen_id": examen['examen_id'],
                                    "salle_id": salle['salle_id'],
                                    "Salle": salle['nom'],
                                    "prof_id": examen['prof_id'],
                                    "date_heure": nouvel_debut,
                                    "date_fin": nouvel_fin,
                                    "etudiants": etudiants_exam
                                })
                                execute_update(
                                    "UPDATE planning.examens SET salle_id = %s, date_heure = %s WHERE id = %s",
                                    (salle['salle_id'], nouvel_debut, examen['examen_id'])
                                )
                                affecte = True
                                break
                        if affecte:
                            break

                if not affecte:
                    # Aucun créneau dispo
                    optimisation.append({
                        "examen_id": examen['examen_id'],
                        "salle_id": None,
                        "Salle": "Aucune salle disponible",
                        "prof_id": examen['prof_id'],
                        "date_heure": examen['date_heure'],
                        "date_fin": examen['date_fin'],
                        "etudiants": etudiants_exam
                    })

            df_opt = pd.DataFrame(optimisation).sort_values(['date_heure', 'Salle'])
            st.success("Optimisation complète terminée !")
            st.dataframe(df_opt.drop(columns=['etudiants']), use_container_width=True)


# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.markdown("**Système de planification des examens** - Version 1.0 | © 2025")

