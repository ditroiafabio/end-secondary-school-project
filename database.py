import sqlite3
import os


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.db")

def init_db():
    # ouvre le fichier de base de données ( si la table existe pas, ça la créée)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            pseudo  TEXT    NOT NULL,
            temps   REAL    NOT NULL  -- temps en secondes (ex: 125.43)
        )
    """)
    con.commit()
    con.close()

def save_score(pseudo, temps):
    # insère un nouveau score dans la table (on garde tous les scores, même les doublons)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO scores (pseudo, temps) VALUES (?, ?)", (pseudo, temps))
    con.commit()
    con.close()

def get_top10():
    # retourne les 10 meilleurs temps (les plus bas = les plus rapides) avec leur pseudo associé
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT pseudo, temps FROM scores ORDER BY temps ASC LIMIT 10")
    rows = cur.fetchall()
    con.close()
    return rows  # liste de tuples (pseudo, temps)