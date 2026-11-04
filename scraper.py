import os
import re
import requests
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE PRODOTTO ---
URL = "https://www.amazon.it/gp/product/B0GHNB78F7/ref=ox_sc_act_title_1?smid=AR03I86151UAC&psc=1"  # 1. Incolla qui il link del prodotto
SELETTORE_CSS = "#corePriceDisplay_desktop_feature_div .a-price-whole"               # 2. Incolla qui il Selettore CSS copiato
PREZZO_OBIETTIVO = 18                    # 3. Sotto questa cifra (in Euro) parte l'avviso

# Legge il nome del tuo canale segreto dalla cassaforte di GitHub
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")

def invia_ntfy(prezzo_attuale):
    if not NTFY_TOPIC:
        print("Errore: il secret NTFY_TOPIC non è configurato su GitHub!")
        return

    messaggio = (
        f"Il prodotto è sceso a {prezzo_attuale:.2f} € "
        f"(il tuo obiettivo era {PREZZO_OBIETTIVO:.2f} €).\n"
        f"Tocca questa notifica per aprire subito il sito!"
    )

    # Invio della notifica push tramite ntfy.sh
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=messaggio.encode("utf-8"),
        headers={
            "Title": f"Prezzo sceso a {prezzo_attuale:.2f} EUR!",
            "Priority": "high",
            "Tags": "fire,shopping_cart",  # ntfy li trasforma nelle icone 🔥 e 🛒
            "Click": URL                   # Rende la notifica cliccabile
        },
        timeout=10
    )

def controlla_prezzo():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    risposta = requests.get(URL, headers=headers, timeout=15)
    risposta.raise_for_status()
    
    pagina = BeautifulSoup(risposta.text, "html.parser")
    elemento_prezzo = pagina.select_one(SELETTORE_CSS)
    
    if not elemento_prezzo:
        print("Errore: selettore non trovato nella pagina.")
        return

    testo_grezzo = elemento_prezzo.get_text().strip()
    print(f"Testo letto sulla pagina: {testo_grezzo}")
    
    # Pulizia: rimuove il punto delle migliaia e converte la virgola decimale in punto
    testo_pulito = testo_grezzo.replace(".", "").replace(",", ".")
    numeri = re.findall(r"\d+\.?\d*", testo_pulito)
    
    if not numeri:
        print("Impossibile estrarre un valore numerico.")
        return
        
    prezzo_attuale = float(numeri[0])
    print(f"Prezzo convertito: {prezzo_attuale} € (Obiettivo: {PREZZO_OBIETTIVO} €)")
    
    if prezzo_attuale <= PREZZO_OBIETTIVO:
        invia_ntfy(prezzo_attuale)
        print("Notifica inviata con successo tramite ntfy!")
    else:
        print("Prezzo ancora sopra la soglia. Nessuna notifica.")

if __name__ == "__main__":
    controlla_prezzo()
