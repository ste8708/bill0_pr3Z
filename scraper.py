import os
import re
from curl_cffi import requests
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE PRODOTTO ---
URL = "https://www.amazon.it/gp/product/B0GHNB78F7"  # 1. Incolla qui il link del sensore ThirdReality
PREZZO_OBIETTIVO = 999.00                             # 2. Lasciato a 999 per verificare subito la lettura del prezzo!

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

def estrai_prezzo_amazon(pagina, html_grezzo):
    # LIVELLO 1: Selettori CSS svincolati dal blocco '#corePriceDisplay_desktop_feature_div'
    selettori = [
        ".priceToPay .a-price-whole",
        "#centerCol .a-price-whole",
        "#apex_desktop .a-price-whole",
        ".reinventPricePriceToPayMargin .a-price-whole",
        ".a-price-whole"  # Prende il primo prezzo intero presente sulla pagina
    ]
    
    for sel in selettori:
        el_intero = pagina.select_one(sel)
        if el_intero and el_intero.get_text().strip():
            intero = re.sub(r"[^\d]", "", el_intero.get_text())
            # Cerchiamo se subito accanto c'è anche il tag dei centesimi (.a-price-fraction)
            genitore = el_intero.find_parent(class_="a-price")
            el_centesimi = genitore.select_one(".a-price-fraction") if genitore else None
            centesimi = re.sub(r"[^\d]", "", el_centesimi.get_text()) if el_centesimi else "00"
            
            if intero:
                prezzo_completo = float(f"{intero}.{centesimi}")
                print(f"✅ Trovato con selettore CSS '{sel}': {prezzo_completo:.2f} €")
                return prezzo_completo

    # LIVELLO 2: Ricerca nel codice JSON nascosto di Amazon (spesso presente anche se la grafica è nascosta per IP USA)
    pattern_json = [
        r'"priceAmount"\s*:\s*(\d+\.?\d*)',
        r'"buyingPrice"\s*:\s*(\d+\.?\d*)',
        r'"displayPrice"\s*:\s*"([^"]+)"'
    ]
    for pat in pattern_json:
        match = re.search(pat, html_grezzo)
        if match:
            valore = match.group(1).replace(".", "").replace(",", ".")
            num = re.findall(r"\d+\.?\d*", valore)
            if num:
                prezzo_json = float(num[0])
                print(f"✅ Trovato nel JSON interno di Amazon: {prezzo_json:.2f} €")
                return prezzo_json

    return None

def controlla_prezzo():
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9",
        "Referer": "https://www.google.it/",
    }
    cookies = {
        "lc-acb-it": "it_IT",
        "i18n-prefs": "EUR"
    }
    
    risposta = requests.get(URL, headers=headers, cookies=cookies, impersonate="chrome124", timeout=20)
    print(f"Stato risposta server: HTTP {risposta.status_code}")
    
    pagina = BeautifulSoup(risposta.text, "html.parser")
    titolo = pagina.title.get_text().strip() if pagina.title else "Sconosciuto"
    print(f"Prodotto: {titolo[:60]}...")

    prezzo_attuale = estrai_prezzo_amazon(pagina, risposta.text)
    
    if prezzo_attuale is None:
        print("❌ Nessun prezzo trovato nella pagina.")
        # Diagnostica per capire cosa mostra Amazon al server USA di GitHub
        box_disponibilita = pagina.select_one("#availability")
        if box_disponibilita:
            print(f"Testo nel box disponibilità: '{box_disponibilita.get_text().strip()}'")
        tutti_prezzi = [el.get_text().strip() for el in pagina.select(".a-price")[:5]]
        print(f"Primi 5 blocchi '.a-price' visti nella pagina: {tutti_prezzi}")
        return

    print(f"💰 Prezzo rilevato: {prezzo_attuale:.2f} € (Obiettivo: {PREZZO_OBIETTIVO:.2f} €)")
    
    if prezzo_attuale <= PREZZO_OBIETTIVO:
        invia_ntfy(
            f"Prezzo: {prezzo_attuale:.2f} EUR!",
            f"Sensore ThirdReality a {prezzo_attuale:.2f} € (soglia: {PREZZO_OBIETTIVO:.2f} €).\nTocca per aprire Amazon!"
        )
        print("Notifica inviata con successo!")
    else:
        print("Prezzo ancora sopra la soglia.")

if __name__ == "__main__":
    controlla_prezzo()
