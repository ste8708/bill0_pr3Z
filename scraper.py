import os
import re
from curl_cffi import requests
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE PRODOTTO ---
URL = "https://www.amazon.it/gp/product/B0GHNB78F7"  # 1. Incolla qui il link del prodotto
PREZZO_OBIETTIVO = 999.00                             # 2. Prezzo soglia (lasciato a 999 per forzare il primo avviso!)
INVIA_NOTIFICA_TEST = True                            # 3. Se True, ti manda una notifica su ntfy anche se Amazon blocca!

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")

def invia_ntfy(titolo, messaggio):
    if not NTFY_TOPIC:
        print("Errore: il secret NTFY_TOPIC non è configurato!")
        return

    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=messaggio.encode("utf-8"),
        headers={
            "Title": titolo,
            "Priority": "high",
            "Tags": "fire,shopping_cart",
            "Click": URL
        },
        timeout=10
    )

def controlla_prezzo():
    # Intestazioni avanzate per simulare un utente italiano che clicca da Google
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9",
        "Referer": "https://www.google.it/",
        "Upgrade-Insecure-Requests": "1",
    }
    
    # Cookie base per dire ad Amazon che siamo sul mercato italiano con valuta Euro
    cookies = {
        "lc-acb-it": "it_IT",
        "i18n-prefs": "EUR"
    }
    
    risposta = requests.get(
        URL, 
        headers=headers, 
        cookies=cookies, 
        impersonate="chrome124", 
        timeout=20
    )
    print(f"Stato risposta server: HTTP {risposta.status_code}")
    
    pagina = BeautifulSoup(risposta.text, "html.parser")
    
    # 1. Vediamo subito che pagina ci ha risposto Amazon!
    titolo_pagina = pagina.title.get_text().strip() if pagina.title else "Nessun titolo"
    print(f"Titolo della pagina scaricata: '{titolo_pagina}'")
    
    if "Captcha" in titolo_pagina or " Continua gli acquisti" in risposta.text or " digita i caratteri" in risposta.text:
        print("ATTENZIONE: Amazon ha mostrato la pagina di blocco Anti-Bot (CAPTCHA)!")
        if INVIA_NOTIFICA_TEST:
            invia_ntfy("Test Bot Funzionante!", "Il collegamento con ntfy funziona! Ora dobbiamo solo aggirare il CAPTCHA di Amazon.")
            print("Inviata comunque una notifica di test al telefono!")
        return

    # 2. Proviamo in sequenza i 4 selettori più usati da Amazon per il prezzo
    selettori_amazon = [
        "#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen",
        "#corePriceDisplay_desktop_feature_div .a-price-whole",
        ".apexPriceToPay .a-offscreen",
        "#priceblock_ourprice"
    ]
    
    elemento_prezzo = None
    for sel in selettori_amazon:
        elemento_prezzo = pagina.select_one(sel)
        if elemento_prezzo:
            print(f"Trovato il prezzo grazie al selettore: {sel}")
            break
            
    if not elemento_prezzo:
        print("Errore: nessuno dei selettori ha trovato il prezzo nella pagina.")
        if INVIA_NOTIFICA_TEST:
            invia_ntfy("Test Bot (Senza Prezzo)", f"Il bot gira, ma non trova il prezzo sulla pagina: {titolo_pagina}")
        return

    testo_grezzo = elemento_prezzo.get_text().strip()
    print(f"Testo letto sulla pagina: '{testo_grezzo}'")
    
    testo_pulito = "".join(testo_grezzo.split()).replace(".", "").replace(",", ".")
    numeri = re.findall(r"\d+\.?\d*", testo_pulito)
    
    if not numeri:
        print("Impossibile estrarre un valore numerico.")
        return
        
    prezzo_attuale = float(numeri[0])
    print(f"Prezzo convertito: {prezzo_attuale:.2f} € (Obiettivo: {PREZZO_OBIETTIVO:.2f} €)")
    
    if prezzo_attuale <= PREZZO_OBIETTIVO:
        invia_ntfy(
            f"Prezzo sceso a {prezzo_attuale:.2f} EUR!",
            f"Il prodotto è a {prezzo_attuale:.2f} € (soglia: {PREZZO_OBIETTIVO:.2f} €).\nTocca per aprire Amazon!"
        )
        print("Notifica di offerta inviata con successo tramite ntfy!")
    else:
        print("Prezzo ancora sopra la soglia. Nessuna notifica.")

if __name__ == "__main__":
    controlla_prezzo()

import os
import re
from curl_cffi import requests
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE PRODOTTO ---
URL = "https://www.amazon.it/gp/product/B0GHNB78F7/ref=ox_sc_act_title_1?smid=AR03I86151UAC&psc=1"  # 1. Incolla qui il link del prodotto
SELETTORE_CSS = "#corePriceDisplay_desktop_feature_div .a-price-whole"               # 2. Incolla qui il Selettore CSS copiato
PREZZO_OBIETTIVO = 100                    # 3. Sotto questa cifra (in Euro) parte l'avviso

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
