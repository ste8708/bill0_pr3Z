import os
import re
from curl_cffi import requests
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE PRODOTTO ---
URL = "https://www.amazon.it/gp/product/B0GHNB78F7"  # 1. Incolla qui il link del sensore ThirdReality
PREZZO_OBIETTIVO = 999.00                             # 2. Lascia 999 per il test, poi metti la tua soglia (es. 17.00)

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
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

def pulisci_prezzo(testo):
    """Trasforma stringhe come '19,99 €' o '19\n,99' in un numero float 19.99"""
    testo_compatto = "".join(testo.split()).replace("€", "").replace(".", "").replace(",", ".")
    numeri = re.findall(r"\d+\.\d+|\d+", testo_compatto)
    return float(numeri[0]) if numeri else None

def estrai_prezzo_amazon(pagina):
    # 1. Cerchiamo prima nei selettori esatti del prezzo di acquisto (Colonna Centrale + BuyBox di Destra)
    selettori_acquisto = [
        "span.priceToPay span.a-offscreen",
        "span.priceToPay",
        "#corePriceDisplay_desktop_feature_div .a-price",
        "#corePrice_feature_div .a-price",
        "#desktop_buybox .a-price",
        "#buybox .a-price",
        "#apex_desktop .a-price"
    ]
    
    for sel in selettori_acquisto:
        elementi = pagina.select(sel)
        for el in elementi:
            # Se dentro c'è a-price-whole + a-price-fraction, li uniamo con precisione
            intero = el.select_one(".a-price-whole")
            frazione = el.select_one(".a-price-fraction")
            if intero:
                int_str = re.sub(r"[^\d]", "", intero.get_text())
                fraz_str = re.sub(r"[^\d]", "", frazione.get_text()) if frazione else "00"
                if int_str:
                    prezzo = float(f"{int_str}.{fraz_str}")
                    print(f"✅ Prezzo trovato con '{sel}': {prezzo:.2f} €")
                    return prezzo
            
            # Altrimenti leggiamo il testo diretto (es. da .a-offscreen)
            prezzo = pulisci_prezzo(el.get_text())
            if prezzo:
                print(f"✅ Prezzo trovato con '{sel}': {prezzo:.2f} €")
                return prezzo

    # 2. Se ancora non lo vede, controlliamo tutti i prezzi sulla pagina escludendo i caroselli pubblicitari
    for el in pagina.select(".a-price"):
        # Ignora i prezzi che si trovano dentro i caroselli "Prodotti sponsorizzati" o "Spesso comprati insieme"
        if el.find_parent(class_=re.compile(r"carousel|sims|sp_detail")):
            continue
        prezzo = pulisci_prezzo(el.get_text())
        if prezzo:
            print(f"✅ Prezzo trovato con scansione generale: {prezzo:.2f} €")
            return prezzo

    return None

def controlla_prezzo():
    sessione = requests.Session(impersonate="chrome124")
    sessione.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9",
        "Referer": "https://www.google.it/",
    })
    
    if AMAZON_COOKIE:
        print("Uso il cookie italiano pre-salvato...")
        sessione.headers.update({"Cookie": AMAZON_COOKIE})

    risposta = sessione.get(URL, timeout=20)
    pagina = BeautifulSoup(risposta.text, "html.parser")
    
    loc_el = pagina.select_one("#glow-ingress-line2")
    localita_vista = loc_el.get_text().strip() if loc_el else "Non rilevata"
    print(f"📍 Località vista da Amazon: '{localita_vista}'")

    prezzo_attuale = estrai_prezzo_amazon(pagina)
    
    if prezzo_attuale is None:
        print("❌ Prezzo ancora non trovato.")
        # Diagnostica: ci mostra cosa c'è scritto nel box di destra (BuyBox)
        buybox = pagina.select_one("#buybox") or pagina.select_one("#rightCol")
        if buybox:
            testo_buybox = " ".join(buybox.get_text().split())[:200]
            print(f"Contenuto visto nella colonna di acquisto: '{testo_buybox}...'")
        tutti = [p.get_text().strip() for p in pagina.select(".a-price")[:6]]
        print(f"Tutti i tag .a-price presenti: {tutti}")
        return

    print(f"💰 Prezzo rilevato: {prezzo_attuale:.2f} € (Obiettivo: {PREZZO_OBIETTIVO:.2f} €)")
    
    if prezzo_attuale <= PREZZO_OBIETTIVO:
        invia_ntfy(
            f"Prezzo: {prezzo_attuale:.2f} EUR!",
            f"Sensore ThirdReality a {prezzo_attuale:.2f} € (CAP: {localita_vista}).\nTocca per aprire Amazon!"
        )
        print("Notifica inviata con successo!")
    else:
        print("Prezzo sopra la soglia. Nessuna notifica.")

if __name__ == "__main__":
    controlla_prezzo()
