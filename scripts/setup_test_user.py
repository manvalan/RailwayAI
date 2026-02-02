import os
import sys
from pathlib import Path

# Aggiunge la root del progetto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.integration.user_service import UserService
from python.integration.database import db

def setup_user():
    print(f"Database path: {os.path.abspath('railway_ai.db')}")
    
    # Rimuove il file se è corrotto (0 byte)
    if os.path.exists('railway_ai.db') and os.path.getsize('railway_ai.db') == 0:
        print("Il database è vuoto. Lo inizializzo...")
        os.remove('railway_ai.db')
    
    # Inizializza il DB creando le tabelle
    from python.integration.database import DatabaseManager
    new_db = DatabaseManager('railway_ai.db')
    
    # Crea l'utente test
    username = "test"
    password = "test1234"
    
    # Verifica se esiste già
    user = UserService.get_user(username)
    if user:
        print(f"L'utente '{username}' esiste già. Aggiorno la password...")
        UserService.update_password(username, password)
    else:
        print(f"Creo l'utente '{username}'...")
        success = UserService.create_user(username, password)
        if success:
            print(f"✅ Utente '{username}' creato con successo!")
        else:
            print(f"❌ Errore nella creazione dell'utente '{username}'.")
    
    # Verifica finale
    user = UserService.get_user(username)
    print(f"Stato utente: {user}")

if __name__ == "__main__":
    setup_user()
