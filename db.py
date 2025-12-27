import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="exams_db",
        user="postgres",
        password="imen",     # 🔴 mets ton vrai mot de passe
        host="localhost",
        port="5432"
    )
