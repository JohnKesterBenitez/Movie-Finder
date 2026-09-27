from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def check_user(username):
    settings = DatabaseSettings.from_env()
    db = DatabaseManager(settings)
    with db.session() as (conn, cursor):
        cursor.execute('SELECT username, recovery_question FROM users WHERE username=%s', (username,))
        print('Guest:', cursor.fetchone())
        
        cursor.execute('SELECT username, recovery_question FROM admin_users WHERE username=%s', (username,))
        print('Admin:', cursor.fetchone())

if __name__ == "__main__":
    check_user('rie')
