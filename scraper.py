import os
import re
from curl_cffi import requests
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE PRODOTTO ---
URL = "https://www.amazon.it/gp/product/B0GHNB78F7"  # 1. Incolla qui il link del sensore ThirdReality
PREZZO_OBIETTIVO = 999.00                             # 2. Lascia pure 999 per fare il test del prezzo italiano!
CAP_ITALIANO = "28010"                                # 3. Il CAP italiano da simulare

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
# Opzionale: se hai salvato i cookie nei Secrets di GitHub, li usa
AMAZON_COOKIE = os.environ.get("AMAZON_COOKIE")

def invia_ntfy(titolo, messaggio):
    if not NTFY_TOPIC:
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

def imposta_posizione_italia(sessione):
    """Simula il clic su 'Invia a: CAP 28010 (Italia)' su Amazon.it"""
    # 1. Visita rapida alla home per ricevere il cookie di sessione italiano (session-id) e il token CSRF
    home = sessione.get("https://www.amazon.it/", timeout=15)
    
    # Estrae il token anti-CSRF necessario per cambiare il CAP
    csrf_match = re.search(r'anti-csrftoken-a2z"\s+value="([^"]+)"', home.text)
    if not csrf_match:
        csrf_match = re.search(r'csrfToken"\s*:\s*"([^"]+)"', home.text)
        
    headers_ajax = {
        "Accept": "text/html,*/*",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.amazon.it/",
    }
    if csrf_match:
        headers_ajax["anti-csrftoken-a2z"] = csrf_match.group(1)

    payload = {
        "locationType": "LOCATION_INPUT",
        "zipCode": CAP_ITALIANO,
        "storeContext": "generic",
        "deviceType": "web",
        "pageType": "Gateway",
        "actionSource": "glow"
    }
    
    # 2. Invia il CAP italiano ad Amazon (ora i cookie della sessione sono localizzati in Italia!)
    r = sessione.post(
        "https://www.amazon.it/portal-migration/hz/glow/address-change?actionSource=glow",
        data=payload,
        headers=headers_ajax,
        timeout=15
    )
    print(f"Cambio località sul CAP {CAP_ITALIANO}: HTTP {r.status_code}")

def estrai_prezzo_amazon(pagina):
    # Cerchiamo ESCLUSIVAMENTE nel riquadro principale del prodotto (evitando i prodotti sponsorizzati a fondo pagina!)
    selettori_principali = [
        "#corePriceDisplay_desktop_feature_div .priceToPay .a-price-whole",
        "#corePrice_feature_div .a-price-whole",
        "#apex_desktop .a-price-whole",
        "#centerCol .a-price-whole"
    ]
    
    for sel in selettori_principali:
        el_intero = pagina.select_one(sel)
        if el_intero and el_intero.get_text().strip():
            intero = re.sub(r"[^\d]", "", el_intero.get_text())
            genitore = el_intero.find_parent(class_="a-price")
            el_centesimi = genitore.select_one(".a-price-fraction") if genitore else None
            centesimi = re.sub(r"[^\d]", "", el_centesimi.get_text()) if el_centesimi else "00"
            
            if intero:
                prezzo = float(f"{intero}.{centesimi}")
                print(f"✅ Trovato nel box principale con '{sel}': {prezzo:.2f} €")
                return prezzo
    return None

def controlla_prezzo():
    sessione = requests.Session(impersonate="chrome124")
    sessione.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9",
    })
    
    if AMAZON_COOKIE:
        print("Uso il cookie italiano pre-salvato...")
        sessione.headers.update({"Cookie": AMAZON_COOKIE})
    else:
        print("Imposto automaticamente il CAP italiano nella sessione...")
        imposta_posizione_italia(sessione)

    risposta = sessione.get(URL, timeout=20)
    pagina = BeautifulSoup(risposta.text, "html.parser")
    
    # Stampiamo nel log quale località vede Amazon in alto a sinistra!
    loc_el = pagina.select_one("#glow-ingress-line2")
    localita_vista = loc_el.get_text().strip() if loc_el else "Non rilevata"
    print(f"📍 Località vista da Amazon: '{localita_vista}'")

    prezzo_attuale = estrai_prezzo_amazon(pagina)
    
    if prezzo_attuale is None:
        print("❌ Prezzo non trovato nel box principale. Probabilmente Amazon richiede il cookie di sessione.")
        return

    print(f"💰 Prezzo rilevato: {prezzo_attuale:.2f} € (Obiettivo: {PREZZO_OBIETTIVO:.2f} €)")
    
    if prezzo_attuale <= PREZZO_OBIETTIVO:
        invia_ntfy(
            f"Prezzo: {prezzo_attuale:.2f} EUR!",
            f"Sensore ThirdReality a {prezzo_attuale:.2f} € (Località: {localita_vista}).\nTocca per aprire Amazon!"
        )

if __name__ == "__main__":
    controlla_prezzo()
