import os
import re
import requests
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE PRODOTTO ---
URL = "https://www.amazon.it/gp/product/B0GHNB78F7/ref=ox_sc_act_title_1?smid=AR03I86151UAC&psc=1"  # 1. Incolla qui il link del prodotto
SELETTORE_CSS = ".price#corePriceDisplay_desktop_feature_div > div > div.a-section.a-spacing-none.aok-align-center.aok-relative > span.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay.apex-pricetopay-value > span:nth-child(2) > span.a-price-whole-value"               # 2. Incolla qui il Selettore CSS copiato
PREZZO_OBIETTIVO = 18                    # 3. Sotto questa cifra (in Euro) parte l'avviso

# Chiavi lette in automatico dalla cassaforte di GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def invia_telegram(messaggio):
    url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": messaggio, "parse_mode": "Markdown"}
    requests.post(url_api, json=payload, timeout=10)

def controlla_prezzo():
    # Ci fingiamo un normale browser su Windows 11 per evitare blocchi banali
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
    
    # Pulizia: es. da "1.249,90 €" -> toglie il punto delle migliaia, mette il punto per i decimali -> 1249.90
    testo_pulito = testo_grezzo.replace(".", "").replace(",", ".")
    numeri = re.findall(r"\d+\.?\d*", testo_pulito)
    
    if not numeri:
        print("Impossibile estrarre un valore numerico.")
        return
        
    prezzo_attuale = float(numeri[0])
    print(f"Prezzo convertito: {prezzo_attuale} € (Obiettivo: {PREZZO_OBIETTIVO} €)")
    
    if prezzo_attuale <= PREZZO_OBIETTIVO:
        msg = (
            f"🔥 *PREZZO SCESO!*\n\n"
            f"Prezzo attuale: *{prezzo_attuale:.2f} €*\n"
            f"Soglia impostata: {PREZZO_OBIETTIVO:.2f} €\n\n"
            f"[Vai alla pagina del prodotto]({URL})"
        )
        invia_telegram(msg)
        print("Notifica inviata su Telegram!")
    else:
        print("Prezzo ancora sopra la soglia. Nessuna notifica.")

if __name__ == "__main__":
    controlla_prezzo()
