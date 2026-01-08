import requests
import json
import time
import os
import urllib3
import random

# --- VERSIÓN 5.0 - ANTI-BLOQUEO & MAPA FIX ---
print("\n✅ INICIANDO ROBOT v5.0 - MODO ROBUSTO\n")

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

# Función con REINTENTOS
def obtener_datos_con_reintentos(id_playa, intentos=3):
    url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/playa/{id_playa}"
    
    for i in range(intentos):
        try:
            # Paso 1
            res1 = requests.get(url, headers=headers, verify=False, timeout=15)
            if res1.status_code == 200:
                datos_url = res1.json().get('datos')
                if datos_url:
                    # Paso 2
                    res2 = requests.get(datos_url, verify=False, timeout=15)
                    if res2.status_code == 200:
                        raw = res2.json()
                        return raw[0] if isinstance(raw, list) else raw
            
            # Si falla, esperamos un poco más antes de reintentar
            print(f"   ⚠️ Intento {i+1} fallido. Reintentando en 5s...")
            time.sleep(5)

        except Exception as e:
            print(f"   ⚠️ Error de red: {e}")
            time.sleep(5)
    
    return None

def procesar_playas():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        playas = json.load(f)

    resultados = []
    print(f"🏖️ Procesando {len(playas)} playas con sistema anti-bloqueo...")

    for i, playa in enumerate(playas):
        print(f"[{i+1}/{len(playas)}] Consultando: {playa['nombre']}...", end=" ", flush=True)
        
        datos = obtener_datos_con_reintentos(playa['id_aemet'])
        
        # VALORES POR DEFECTO (Si falla AEMET, al menos mostramos la playa en el mapa)
        t_max = 0
        viento_valor = 0
        cielo_desc = "Sin datos"
        score = 0
        datos_validos = False

        if datos and 'prediccion' in datos and 'dia' in datos['prediccion']:
            try:
                hoy = datos['prediccion']['dia'][0]
                
                # Extracción segura de datos
                t_max = int(hoy['temperatura']['maxima'])
                
                viento_lista = hoy.get('viento', [])
                if viento_lista:
                    viento_valor = int(viento_lista[0].get('velocidad', 10))
                else:
                    viento_valor = 10

                cielo_lista = hoy.get('estadoCielo', [])
                if cielo_lista:
                    cielo_desc = cielo_lista[0].get('descripcion1', 'Despejado')
                else:
                    cielo_desc = "Despejado"

                # ALGORITMO DE NOTA
                score = 10
                if viento_valor > 20: score -= 2
                if viento_valor > 30: score -= 4
                if t_max < 21: score -= 2
                if t_max < 19: score -= 3
                score = max(0, min(10, score))
                
                datos_validos = True
                print("✅ OK")

            except Exception as e:
                print(f"❌ Error procesando datos: {e}")
        else:
            print("❌ Sin respuesta AEMET")

        # GUARDAMOS SIEMPRE (Para que salga en el mapa aunque no haya clima)
        resultados.append({
            "nombre": playa["nombre"],
            "municipio": playa["municipio"],
            "zona": playa["zona"],
            "id_aemet": playa["id_aemet"],
            "coordenadas": playa.get("coordenadas"), 
            "score": score if datos_validos else 0, # Nota 0 si no hay datos
            "clima": {
                "t_max": t_max,
                "viento": viento_valor,
                "cielo": cielo_desc
            },
            "detalles": [cielo_desc, f"Viento: {viento_valor}km/h"]
        })
        
        # PAUSA ALEATORIA (3 a 6 segundos) PARA EVITAR BLOQUEO
        time.sleep(random.uniform(3, 6))

    resultados.sort(key=lambda x: x['score'], reverse=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ FINALIZADO: {len(resultados)} playas guardadas.")

if __name__ == "__main__":
    procesar_playas()
