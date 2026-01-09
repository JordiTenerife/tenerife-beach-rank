import requests
import json
import time
import os
import urllib3
import random

# --- VERSIÓN 6.0 - MODO TORTUGA (ANTI-ERROR 429) ---
print("\n🐢 INICIANDO ROBOT v6.0 - MODO LENTO Y SEGURO\n")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    API_KEY = os.environ["AEMET_API_KEY"]
except KeyError:
    print("❌ ERROR: Falta la API Key.")
    exit(1)

INPUT_FILE = 'playas.json'
OUTPUT_FILE = 'data.json'

headers = {
    'api_key': API_KEY,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Accept': 'application/json'
}

def obtener_datos_con_paciencia(id_playa):
    url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/playa/{id_playa}"
    
    # Intentamos hasta 3 veces con mucha calma
    for i in range(3):
        try:
            res1 = requests.get(url, headers=headers, verify=False, timeout=20)
            
            # Si nos dicen que esperemos (429), obedecemos y esperamos 1 minuto
            if res1.status_code == 429:
                print(f"   ✋ AEMET pide calma (429). Esperando 60s...")
                time.sleep(60)
                continue # Reintentar
            
            if res1.status_code == 200:
                datos_url = res1.json().get('datos')
                if datos_url:
                    res2 = requests.get(datos_url, verify=False, timeout=20)
                    if res2.status_code == 200:
                        raw = res2.json()
                        return raw[0] if isinstance(raw, list) else raw
            
            # Si falla por otra cosa, esperamos 5s
            time.sleep(5)

        except Exception as e:
            print(f"   ⚠️ Error red: {e}")
            time.sleep(5)
    
    return None

def procesar_playas():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        playas = json.load(f)

    resultados = []
    print(f"🏖️ Procesando {len(playas)} playas en MODO TORTUGA...")

    for i, playa in enumerate(playas):
        print(f"[{i+1}/{len(playas)}] {playa['nombre']}...", end=" ", flush=True)
        
        datos = obtener_datos_con_paciencia(playa['id_aemet'])
        
        # Valores por defecto (Seguridad)
        t_max = 0
        viento_valor = 0
        cielo_desc = "Sin datos"
        score = 0
        datos_validos = False

        if datos and 'prediccion' in datos:
            try:
                hoy = datos['prediccion']['dia'][0]
                t_max = int(hoy['temperatura']['maxima'])
                viento_valor = int(hoy['viento'][0]['velocidad'])
                cielo_desc = hoy['estadoCielo'][0]['descripcion1']
                
                # Algoritmo de nota
                score = 10
                if viento_valor > 20: score -= 2
                if viento_valor > 30: score -= 4
                if t_max < 21: score -= 2
                if t_max < 19: score -= 3
                score = max(0, min(10, score))
                
                datos_validos = True
                print("✅")
            except:
                print("⚠️ Datos incompletos")
        else:
            print("❌ Sin respuesta")

        resultados.append({
            "nombre": playa["nombre"],
            "municipio": playa["municipio"],
            "zona": playa["zona"],
            "id_aemet": playa["id_aemet"],
            "coordenadas": playa.get("coordenadas"),
            "score": score if datos_validos else 0,
            "clima": {"t_max": t_max, "viento": viento_valor, "cielo": cielo_desc},
            "detalles": [cielo_desc, f"Viento: {viento_valor}km/h"]
        })
        
        # PAUSA LARGA: Entre 8 y 12 segundos por playa
        # Esto asegura que no pasamos de 6 peticiones por minuto (super seguro)
        time.sleep(random.uniform(8, 12))

    resultados.sort(key=lambda x: x['score'], reverse=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ FINALIZADO. Datos guardados.")

if __name__ == "__main__":
    procesar_playas()
