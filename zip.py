import os
import json
import zipfile
from typing import Dict, List, Any

# --- CONFIGURATION ---
# Nome del file di configurazione JSON
CONFIG_FILE = 'zip_config.json'
# Directory di output per i file ZIP
OUTPUT_DIR = 'down'

# --- UTILITY FUNCTIONS ---

def load_config(file_path: str) -> Dict[str, Any]:
    """Carica la configurazione dal file JSON."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Errore: File di configurazione '{file_path}' non trovato.")
        exit()
    except json.JSONDecodeError:
        print(f"Errore: Il file '{file_path}' non è un JSON valido.")
        exit()
    except Exception as e:
        print(f"Errore durante il caricamento della configurazione: {e}")
        exit()

def create_zip_archive(zip_filename: str, project_name: str, project_path: str, files_to_include: List[str]):
    """Crea un file ZIP con i file specificati da una cartella di progetto."""
    
    # Crea il percorso completo per il file ZIP
    zip_path = os.path.join(OUTPUT_DIR, zip_filename)
    
    # Controlla se la cartella del progetto esiste
    if not os.path.isdir(project_path):
        print(f"⚠️ Attenzione: La directory di progetto '{project_name}' al percorso '{project_path}' non esiste. Salto l'archiviazione.")
        return

    print(f"📦 Creazione di {zip_filename}...")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # Se la lista è vuota o contiene solo '.', zippa tutto il contenuto della cartella
            if not files_to_include or files_to_include == ['.']:
                print(f"   -> Zippo tutti i contenuti di '{project_path}'.")
                for root, _, files in os.walk(project_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        arcname = os.path.relpath(full_path, project_path)
                        zipf.write(full_path, arcname)
                        
            # Altrimenti, zippa solo i file/sottocartelle specificati
            else:
                print(f"   -> Zippo file/sottocartelle specifici da '{project_path}'.")
                for item in files_to_include:
                    full_path = os.path.join(project_path, item)
                    
                    if os.path.exists(full_path):
                        # Se è un singolo file, lo zippa direttamente
                        if os.path.isfile(full_path):
                             # Usa os.path.basename(item) per estrarre solo il nome del file
                             # e metterlo nella root dello zip. Es: "watchdog/setup.py" -> "setup.py"
                             arcname = os.path.basename(item)
                             zipf.write(full_path, arcname)
                        # Se è una directory, la zippa ricorsivamente
                        elif os.path.isdir(full_path):
                             for root, _, files in os.walk(full_path):
                                 for file in files:
                                     file_path = os.path.join(root, file)
                                     arcname = os.path.relpath(file_path, project_path)
                                     zipf.write(file_path, arcname)
                        else:
                            print(f"   -> Ignorato: '{item}' non è un file o una directory valida.")
                    else:
                        print(f"   -> File/Cartella non trovato in: {full_path}")

        print(f"✅ Completato: {zip_filename}")

    except Exception as e:
        print(f"❌ Errore durante la creazione di {zip_filename}: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    # Cambia alla directory dello script per la gestione relativa di CONFIG_FILE e OUTPUT_DIR
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Assicura che la directory di output esista
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Creata directory di output: '{OUTPUT_DIR}'")

    # Carica la configurazione
    config = load_config(CONFIG_FILE)
    
    if not config:
        print("Nessuna configurazione trovata.")
        exit()

    print("\n--- INIZIO ZIPPING DEI PROGETTI DA PATH DIVERSI ---")
    
    # Itera su ogni progetto nel file di configurazione
    for project_name, details in config.items():
        if 'zip_filename' in details and 'files' in details:
            
            project_path = details.get('path', details.get('dir', project_name))

            create_zip_archive(
                zip_filename=details['zip_filename'],
                project_name=project_name,
                project_path=project_path,
                files_to_include=details['files']
            )
        else:
            print(f"Errore nella configurazione per '{project_name}': mancano 'zip_filename' o 'files'.")
            
    print("\n--- PROCESSO DI ZIPPING COMPLETATO ---")
    input("Premi Invio per chiudere...")