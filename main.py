import os
import requests
import json
import zipfile
import shutil
import tempfile
import time
import subprocess
import sys
import stat  # Aggiunto per gestire i permessi dei file
from InquirerPy import prompt
from InquirerPy.base.control import Choice
from typing import List, Dict, Any

# --- CONFIGURATION ---
# Change to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

GITHUB_BASE_URL = 'https://raw.githubusercontent.com/dj2828/aggiorna-dj/main/'

# --- UTILITY FUNCTIONS ---

def get_local_components() -> List[str]:
    """Finds existing local directories that can be updated."""
    local_items = os.listdir("./")
    local_dirs = [name for name in local_items if os.path.isdir(name)]
    
    if ".git" in local_dirs:
        local_dirs.remove(".git")
    if "down" in local_dirs:
        local_dirs.remove("down")
        
    return local_dirs

def fetch_available_components(url: str) -> Dict[str, Dict]:
    """Fetches the list of available components from the GitHub JSON file."""
    try:
        response = requests.get(url + 'freaky.json')
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Errore nel recupero della lista dei componenti: {e}")
        exit()

def create_choices(component_list: Dict[str, Dict], local_list: List[str], mode: str) -> List[Any]:
    """
    Creates the choices list for InquirerPy.
    """
    choices = []
    component_names = list(component_list.keys())

    for i, name in enumerate(component_names):
        is_local = name in local_list
        if mode == 'update' and is_local:
             choices.append(f"{i+1}) {name}")
        elif mode == 'download' and not is_local:
             choices.append(f"{i+1}) {name}")
             
    return choices

def prompt_user(message: str, choices: List[Any]) -> str:
    """Handles the user prompting."""
    questions = [
        {
            "type": "list",
            "message": message,
            "choices": choices,
            "name": "selected_choice",
            "cycle": False,
        }
    ]
    selection_result = prompt(questions)
    return selection_result['selected_choice']

def process_selection(selected_choice_string: str, available_data: Dict[str, Dict]) -> tuple[str, str, list]:
    """Parses the choice string and returns the key and value from the data."""
    try:
        scelta_index = int(selected_choice_string.split(')')[0]) - 1
    except (ValueError, IndexError):
        raise ValueError("Selezione non valida per l'analisi dell'indice.")
        
    key_name = list(available_data.keys())[scelta_index]
    entry = available_data.get(key_name, {})
    cosa = entry.get('zip')
    da_tenere = entry.get('da-tenere', [])
    dove = key_name

    return cosa, dove, da_tenere

def check_and_install_dependencies():
    """Controlla ed eventualmente installa pip e venv usando pacman (Arch) o apt (Debian)."""
    has_venv = subprocess.run([sys.executable, "-m", "venv", "--help"], capture_output=True).returncode == 0
    has_pip = subprocess.run([sys.executable, "-m", "pip", "--help"], capture_output=True).returncode == 0
        
    if not has_venv or not has_pip:
        print("\n[!] Moduli 'pip' o 'venv' mancanti per l'interprete corrente.")
        if shutil.which("pacman"):
            print("Rilevato pacman. Avvio installazione dipendenze per Arch Linux...")
            subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "python-pip", "python-virtualenv"], check=True)
        elif shutil.which("apt-get"):
            print("Rilevato apt. Avvio installazione dipendenze per Debian/Ubuntu...")
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "python3-pip", "python3-venv"], check=True)
        else:
            print("Gestore di pacchetti non riconosciuto. Procedere all'installazione manuale.")

def download_and_extract(file_to_download: str, target_directory: str, preserve: List[str] | None = None):
    """Handles the download, extraction, preservation and cleanup process."""
    print(f"Aggiornamento di '{target_directory}' in corso. Download di '{file_to_download}'...")

    download_url = GITHUB_BASE_URL + "down/" + file_to_download + "?t=" + str(int(time.time()))
    headers = {'Cache-Control': 'no-cache'}
    temp_preserve_dir = None
    extraction_succeeded = False

    if not os.path.exists(target_directory):
        os.mkdir(target_directory)

    try:
        if preserve:
            temp_preserve_dir = tempfile.mkdtemp(prefix=f"preserve_{os.path.basename(target_directory)}_")
            for item in preserve:
                src_path = os.path.join(target_directory, item)
                if os.path.exists(src_path):
                    dest_path = os.path.join(temp_preserve_dir, os.path.basename(item))
                    shutil.move(src_path, dest_path)

        for child in os.listdir(target_directory):
            child_path = os.path.join(target_directory, child)
            if temp_preserve_dir and os.path.abspath(child_path) == os.path.abspath(temp_preserve_dir):
                continue
            try:
                if os.path.isdir(child_path) and not os.path.islink(child_path):
                    shutil.rmtree(child_path)
                else:
                    os.remove(child_path)
            except Exception:
                pass

        request = requests.get(download_url, headers=headers, stream=True)
        request.raise_for_status()

        with open(file_to_download, 'wb') as f:
            for chunk in request.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        with zipfile.ZipFile(file_to_download, 'r') as zip_ref:
            zip_ref.extractall(target_directory)

        print(f"Aggiornamento completato. Contenuto estratto in '{target_directory}'.")
        extraction_succeeded = True

    except requests.exceptions.RequestException as e:
        print(f"Errore durante il download o l'estrazione: {e}")
        extraction_succeeded = False

    finally:
        if os.path.exists(file_to_download):
            try:
                os.remove(file_to_download)
            except OSError:
                pass

        if temp_preserve_dir and os.path.exists(temp_preserve_dir):
            for preserved_name in os.listdir(temp_preserve_dir):
                src = os.path.join(temp_preserve_dir, preserved_name)
                dest = os.path.join(target_directory, preserved_name)

                if os.path.exists(dest):
                    try:
                        if os.path.isdir(dest) and not os.path.islink(dest):
                            shutil.rmtree(dest)
                        else:
                            os.remove(dest)
                    except Exception:
                        pass

                try:
                    shutil.move(src, dest)
                except Exception:
                    try:
                        if os.path.isdir(src):
                            shutil.copytree(src, dest)
                        else:
                            shutil.copy2(src, dest)
                    except Exception:
                        pass

            try:
                if os.path.exists(temp_preserve_dir):
                    shutil.rmtree(temp_preserve_dir)
            except OSError:
                pass

        if extraction_succeeded:
            # NUOVA FUNZIONE: Rende i file .py eseguibili (chmod +x)
            for root_dir, _, files in os.walk(target_directory):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root_dir, file)
                        try:
                            st = os.stat(file_path)
                            # Aggiunge i permessi di esecuzione per proprietario (USR), gruppo (GRP) e altri (OTH)
                            os.chmod(file_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                        except Exception as e:
                            print(f"Impossibile rendere eseguibile {file_path}: {e}")

            req_path = os.path.join(target_directory, 'requirements.txt')
            if os.path.exists(req_path):
                print(f"\nTrovato `requirements.txt` in '{target_directory}'.")
                
                check_and_install_dependencies()

                install_choices = [
                    Choice(value="venv", name="Virtual Environment locale (.venv) [Consigliato]"),
                    Choice(value="system", name="Sistema (Globale / User)")
                ]
                install_mode = prompt_user("Come vuoi installare i requisiti Python?", install_choices)

                try:
                    if install_mode == "venv":
                        venv_path = os.path.join(target_directory, '.venv')
                        if not os.path.exists(venv_path):
                            print("Creazione del virtual environment in corso...")
                            subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
                        
                        pip_exe = os.path.join(venv_path, 'Scripts', 'pip.exe') if os.name == 'nt' else os.path.join(venv_path, 'bin', 'pip')
                        
                        print("Installazione dei pacchetti nel virtual environment...")
                        subprocess.run([pip_exe, 'install', '-r', os.path.basename(req_path), '--upgrade'], check=True, cwd=target_directory)

                    elif install_mode == "system":
                        print("Installazione dei pacchetti a livello di sistema...")
                        cmd = [sys.executable, '-m', 'pip', 'install', '-r', os.path.basename(req_path), '--upgrade']
                        
                        cmd_break = cmd + ['--break-system-packages']
                        try:
                            subprocess.run(cmd_break, check=True, cwd=target_directory)
                        except subprocess.CalledProcessError:
                            subprocess.run(cmd, check=True, cwd=target_directory)

                    print("Installazione dei requisiti completata.")
                except subprocess.CalledProcessError as e:
                    print(f"Errore durante l'installazione dei requisiti: {e}")
                except Exception as e:
                    print(f"Errore inatteso durante l'installazione: {e}")

                try:
                    os.remove(req_path)
                    print("File 'requirements.txt' rimosso.")
                except OSError:
                    print("Impossibile rimuovere 'requirements.txt'.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    available_data = fetch_available_components(GITHUB_BASE_URL)
    local_components = get_local_components()
    
    update_choices = create_choices(available_data, local_components, 'update')
    
    if not update_choices:
        print("Nessun elemento locale aggiornabile trovato.")
    
    initial_choices = [Choice(value="scarica", name="Scarica nuovo")] + update_choices
    
    if len(initial_choices) == 1 and initial_choices[0].value == "scarica":
        print("Nessun elemento aggiornabile trovato. Passaggio diretto alla sezione 'Scarica nuovo'.")
        selected_choice = 'scarica'
    elif not initial_choices:
        print("Nessun elemento aggiornabile o scaricabile trovato.")
        exit()
    else:
        selected_choice = prompt_user("Scegli un elemento da aggiornare o 'Scarica nuovo':", initial_choices)
    
    if selected_choice == 'scarica':
        download_choices = create_choices(available_data, local_components, 'download')
        
        if not download_choices:
            print("Nessun nuovo elemento scaricabile trovato.")
            exit()
            
        selected_choice = prompt_user("Scegli un elemento da scaricare:", download_choices)
        
    try:
        cosa, dove, da_tenere = process_selection(selected_choice, available_data)
        download_and_extract(cosa, dove, preserve=da_tenere)
    except ValueError as e:
        print(f"Errore di elaborazione della selezione: {e}")
    except IndexError:
        print("Errore: La selezione non corrisponde ad alcun elemento disponibile.")