import requests
import json
import time
import os
import urllib3

# --- VERSIÓN 4.0 - SOPORTE MAPAS Y 60 PLAYAS ---
print("\n✅ INICIANDO ROBOT - MODO 60 PLAYAS\n")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# LEEMOS LA CLAVE SECRETA
try:
    API_KEY = os.environ["AEMET_API_KEY"]
except KeyError:
    print("❌ ERROR: No encuentro la clave AEMET_API_KEY en los secretos.")
    exit(1)

INPUT_FILE = 'playas.json'
OUTPUT_FILE = 'data.json'

headers = {
    'api_key': API_KEY,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Accept': 'application/json'
}

def obtener_datos_playa(id_playa):
    url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/playa/{id_playa}"
    try:
        # Paso 1: Pedir la URL de los datos
        res1 = requests.get(url, headers=headers, verify=False, timeout=10)
        if res1.status_code != 200:
            return None
        
        datos_url = res1.json().get('datos')
        if not datos_url:
            return None

        # Paso 2: Descargar los datos reales
        res2 = requests.get(datos_url, verify=False, timeout=10)
        if res2.status_code != 200:
            return None
        
        # AEMET devuelve una lista, cogemos el primer elemento
        raw_data = res2.json()
        if isinstance(raw_data, list):
            return raw_data[0]
        return raw_data

    except Exception as e:
        print(f"⚠️ Error conectando con AEMET para ID {id_playa}: {e}")
        return None

def procesar_playas():
    # Cargar lista de playas
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        playas = json.load(f)

    resultados = []
    
    print(f"🏖️ Procesando {len(playas)} playas... (Esto tomará unos 3 minutos)")

    for i, playa in enumerate(playas):
        print(f"[{i+1}/{len(playas)}] Consultando: {playa['nombre']}...")
        
        datos = obtener_datos_playa(playa['id_aemet'])
        
        if datos and 'prediccion' in datos and 'dia' in datos['prediccion']:
            # Cogemos la predicción de HOY (índice 0)
            hoy = datos['prediccion']['dia'][0]
            
            # --- EXTRAER DATOS (Simplificados) ---
            # Temperatura (buscamos la máxima)
            try:
                t_max = hoy['temperatura']['maxima']
            except:
                t_max = 22 # Valor por defecto si falla
            
            # Viento (valor numérico)
            try:
                # AEMET da el viento complejo, cogemos velocidad media del primer periodo
                viento_valor = hoy['viento'][0]['velocidad']
            except:
                viento_valor = 15

            # Cielo (descripción)
            try:
                cielo_desc = hoy['estadoCielo'][0]['descripcion1']
                if not cielo_desc: cielo_desc = "Despejado"
            except:
                cielo_desc = "Soleado"

            # --- CALCULAR NOTA (ALGORITMO SIMPLE) ---
            score = 10
            # Si hace mucho viento, bajamos nota
            if viento_valor > 20: score -= 2
            if viento_valor > 30: score -= 3
            # Si hace frío, bajamos nota
            if t_max < 20: score -= 2
            if t_max < 18: score -= 3
            
            # Limites 0-10
            score = max(0, min(10, score))

            # Guardamos la ficha completa
            resultados.append({
                "nombre": playa["nombre"],
                "municipio": playa["municipio"],
                "zona": playa["zona"],
                "id_aemet": playa["id_aemet"],
                "coordenadas": playa.get("coordenadas"), # <--- IMPORTANTE: Copiamos las coordenadas
                "score": score,
                "clima": {
                    "t_max": t_max,
                    "viento": viento_valor,
                    "cielo": cielo_desc
                },
                "detalles": [cielo_desc, f"Viento: {viento_valor}km/h"]
            })
        else:
            print(f"❌ Fallo al obtener datos de {playa['nombre']}")
        
        # PAUSA OBLIGATORIA (Evita bloqueos de AEMET)
        time.sleep(2) 

    # Ordenar ranking: mejores primero
    resultados.sort(key=lambda x: x['score'], reverse=True)

    # Guardar archivo final
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ ÉXITO: {len(resultados)} playas guardadas en {OUTPUT_FILE}")

if __name__ == "__main__":
    procesar_playas()
