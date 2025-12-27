from db import get_connection
from hash_password import verify_password

def authenticate(email, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.mot_de_passe, r.nom
        FROM planning.utilisateurs u
        JOIN planning.roles r ON u.role_id = r.id
        WHERE u.email=%s AND u.actif=true
    """, (email,))
    row = cur.fetchone()
    conn.close()
    if row and verify_password(password, row[1]):
        return {"id": row[0], "role": row[2]}
    return None
