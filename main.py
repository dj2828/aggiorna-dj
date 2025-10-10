import os
import requests
import json
import zipfile
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
    # List all items in the current directory
    local_items = os.listdir("./")
    # Filter for directories
    local_dirs = [name for name in local_items if os.path.isdir(name)]
    
    # Remove system/utility directories
    if ".git" in local_dirs:
        local_dirs.remove(".git")
    if "down" in local_dirs:
        local_dirs.remove("down")
        
    return local_dirs

def fetch_available_components(url: str) -> Dict[str, str]:
    """Fetches the list of available components from the GitHub JSON file."""
    try:
        response = requests.get(url + 'freaky.json')
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Errore nel recupero della lista dei componenti: {e}")
        exit()

def create_choices(component_list: Dict[str, str], local_list: List[str], mode: str) -> List[Any]:
    """
    Creates the choices list for InquirerPy.
    - If mode is 'update', it includes only components present in local_list.
    - If mode is 'download', it includes only components NOT present in local_list.
    
    This function has been fixed to use the 'mode' argument explicitly 
    for correct filtering in both 'update' and 'download' scenarios.
    """
    choices = []
    # component_list is a dictionary, so we use its keys for names
    component_names = list(component_list.keys())

    for i, name in enumerate(component_names):
        is_local = name in local_list
        
        # Logic for Update choices: component must be local
        if mode == 'update' and is_local:
             # The choice string includes the 1-based index for easy parsing later
             choices.append(f"{i+1}) {name}")
        
        # Logic for Download choices: component must NOT be local
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
    # The result should always contain the key because of the prompt setup
    return selection_result['selected_choice']

def process_selection(selected_choice_string: str, available_data: Dict[str, str]) -> tuple[str, str]:
    """Parses the choice string and returns the key and value from the data."""
    # 1. Parse the string (e.g., "3) nome_scelto") to get the original index
    # The split gets '3', int() converts it, and -1 makes it a 0-based index
    try:
        scelta_index = int(selected_choice_string.split(')')[0]) - 1
    except (ValueError, IndexError):
        # Handle the case where a special choice like "scarica" is passed
        raise ValueError("Selezione non valida per l'analisi dell'indice.")
        
    # 2. Use the correct 0-based index to retrieve the KEY and VALUE
    # key_name (e.g., "mod_x") is the directory to extract to (dove)
    key_name = list(available_data.keys())[scelta_index]

    # cosa (e.g., "mod_x.zip") is the file to download (the VALUE)
    cosa = available_data[key_name]
    # dove (e.g., "mod_x") is the local directory to extract the files into (the KEY)
    dove = key_name
    
    return cosa, dove

def download_and_extract(file_to_download: str, target_directory: str):
    """Handles the download, extraction, and cleanup process."""
    print(f"Aggiornamento di '{target_directory}' in corso. Download di '{file_to_download}'...")
    
    # Full URL for the zip file
    download_url = GITHUB_BASE_URL + "down/" + file_to_download

    try:
        # 1. Download the file content
        request = requests.get(download_url)
        request.raise_for_status() # Raise an error for bad status codes (4xx or 5xx)

        # 2. Write the content to a local file
        with open(file_to_download, 'wb') as f:
            f.write(request.content)
            
        # Ensure the target directory exists
        if not os.path.exists(target_directory):
            os.mkdir(target_directory)

        # 3. Extract the contents
        with zipfile.ZipFile(file_to_download, 'r') as zip_ref:
            zip_ref.extractall(target_directory)

        print(f"Aggiornamento completato. Contenuto estratto in '{target_directory}'.")

    except requests.exceptions.RequestException as e:
        print(f"Errore durante il download o l'estrazione: {e}")
        return

    finally:
        # 4. Clean up by removing the downloaded zip file
        if os.path.exists(file_to_download):
            os.remove(file_to_download)
            # print(f"File temporaneo '{file_to_download}' rimosso.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    # 1. Fetch available components and find local ones
    available_data = fetch_available_components(GITHUB_BASE_URL)
    local_components = get_local_components()
    
    # 2. Create the list of components that are local (for updating)
    # Passed 'update' mode
    update_choices = create_choices(available_data, local_components, 'update')
    
    if not update_choices:
        print("Nessun elemento locale aggiornabile trovato.")
    
    # 3. Create the initial prompt choices, including the "Download new" option
    initial_choices = [Choice(value="scarica", name="Scarica nuovo")] + update_choices
    
    # Check if only the 'scarica' option is available (i.e., no local components)
    if len(initial_choices) == 1 and initial_choices[0].value == "scarica":
        print("Nessun elemento aggiornabile trovato. Passaggio diretto alla sezione 'Scarica nuovo'.")
        selected_choice = 'scarica'
    elif not initial_choices:
        print("Nessun elemento aggiornabile o scaricabile trovato.")
        exit()
    else:
        # 4. Prompt the user for an initial action
        selected_choice = prompt_user("Scegli un elemento da aggiornare o 'Scarica nuovo':", initial_choices)
    
    # --- HANDLE 'SCARICA NUOVO' OPTION ---
    if selected_choice == 'scarica':
        
        # Create the list of components that are NOT local (for downloading)
        # Passed 'download' mode and local_components as filter list
        download_choices = create_choices(available_data, local_components, 'download')
        
        if not download_choices:
            print("Nessun nuovo elemento scaricabile trovato.")
            exit()
            
        # Prompt the user for a new component to download
        selected_choice = prompt_user("Scegli un elemento da scaricare:", download_choices)
        
    # --- PROCESS SELECTION AND RUN UPDATE/DOWNLOAD ---
    
    try:
        cosa, dove = process_selection(selected_choice, available_data)
        download_and_extract(cosa, dove)
    except ValueError as e:
        # This catches the ValueError raised if 'scarica' somehow gets here
        print(f"Errore di elaborazione della selezione: {e}")
    except IndexError:
        print("Errore: La selezione non corrisponde ad alcun elemento disponibile.")