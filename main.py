import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

GITHUB = 'https://raw.githubusercontent.com/dj2828/aggiorna-dj/main/'

response = requests.get(GITHUB + 'freaky.json')
data = response.json()
with open('cose.json', 'wb') as f:
    json.dump(data, f, indent=4)

print("Cosa vuoi aggiornare?")