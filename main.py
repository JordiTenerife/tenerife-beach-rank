import requests
import json
import time
from datetime import datetime
import urllib3

# --- VERSIÓN 2.3 - MODO SAFARI (Completo) ---
print("\n✅ VERSIÓN 2.3 CARGADA - SIMULANDO SAFARI\n")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 👇👇👇 1. PEGA TU CLAVE AQUÍ 👇👇👇
API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkb21pbmFyZWVsbXVuZG9AZ21haWwuY29tIiwianRpIjoiYTU3ODRkYTctZjRmMi00ODdhLWE4MTYtMzkzMGU5ZmEyMWVlIiwiaXNzIjoiQUVNRVQiLCJpYXQiOjE3Njc4MDc3MzYsInVzZXJJZCI6ImE1Nzg0ZGE3LWY0ZjItNDg3YS1hODE2LTM5MzBlOWZhMjFlZSIsInJvbGUiOiIifQ.FI8FHfjblsDLUIoUFa-QzKxl62eGfLBZe-lrLtFTs-U" 

INPUT_FILE = 'playas.json'
OUTPUT_FILE = 'data.json'

# 👇👇👇 2. AQUÍ ESTÁN LOS HEADERS (El disfraz) 👇👇👇
# Esto es lo que hace creer a AEMET que eres un navegador Safari
headers = {
    'api_key': API_KEY,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache'
}

def extraer_valor(dato, clave):
    """Saca el valor numérico de forma segura."""
    if not dato: return 0
    valor = dato.get(clave)
    if valor is None: return 0
    if isinstance(valor, (int, float)): return int(valor)
    if isinstance(valor, list) and len(valor) > 0: return int(valor[0])
    if isinstance(valor, dict): return int(valor.get('valor1', 0))
    try: return int(valor)
    except: return 0

def calcular_score(datos_playa):
    score = 5.0
    log = []
    
    if 'prediccion' not in datos_playa or 'dia' not in datos_playa['prediccion']:
        return None 
        
    dia_hoy = datos_playa['prediccion']['dia'][0]
    
    # Objetos
    estado_cielo_obj = dia_hoy['estadoCielo'].get('13-19') or dia_hoy['estadoCielo'].get('08-14') or {}
    viento_obj = dia_hoy['viento'].get('13-19') or dia_hoy['viento'].get('08-14') or {}
    
    # Valores
    t_max = extraer_valor(dia_hoy['tMaxima'], 'valor1')
    fuerza_viento = extraer_valor(viento_obj, 'velocidad')
    desc_cielo = estado_cielo_obj.get('descripcion1', "") if estado_cielo_obj else ""
    
    # Algoritmo
    if fuerza_viento > 30: score -= 4; log.append(f"Viento fuerte ({fuerza_viento}km/h)")
    elif fuerza_viento > 20: score -= 2; log.append(f"Viento moderado ({fuerza_viento}km/h)")
    elif fuerza_viento < 10: score += 1.5; log.append("Viento calma")
    
    if t_max > 25: score += 2; log.append(f"Calor {t_max}º")
    elif t_max < 18: score -= 2; log.append(f"Fresco {t_max}º")
    
    if "despejado" in desc_cielo.lower(): score += 2; log.append("Soleado")
    
    return {
        "score": max(0, min(10, round(score, 1))),
        "razones": log,
        "datos_brutos": {"t_max": t_max, "viento": fuerza_viento, "cielo": desc_cielo}
    }

def main():
    print("🌊 Iniciando análisis...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            playas = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: No encuentro {INPUT_FILE}.")
        return

    resultados = []

    for i, playa in enumerate(playas):
        print(f"[{i+1}/{len(playas)}] 📡 Consultando {playa['nombre']}...", end=" ", flush=True)
        
        try:
            url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/playa/{playa['id_aemet']}"
            
            # Petición 1 (Obtener URL)
            res = requests.get(url, headers=headers, verify=False, timeout=15)
            
            if res.status_code == 200:
                data_url = res.json().get('datos')
                if data_url:
                    # Petición 2 (Bajar datos)
                    res_datos = requests.get(data_url, headers=headers, verify=False, timeout=15)
                    
                    if res_datos.status_code == 200:
                        datos = res_datos.json()
                        datos = datos[0] if isinstance(datos, list) else datos
                        analisis = calcular_score(datos)
                        
                        if analisis:
                            print(f"✅ Nota: {analisis['score']}")
                            resultados.append({
                                "nombre": playa['nombre'],
                                "municipio": playa['municipio'],
                                "zona": playa['zona'],
                                "score": analisis['score'],
                                "detalles": analisis['razones'],
                                "clima": analisis['datos_brutos'],
                                "actualizado": datetime.now().strftime("%d/%m %H:%M")
                            })
                        else: print("⚠️ Datos vacíos")
                    else: print("⚠️ Fallo descarga datos")
                else: print("⚠️ AEMET no dio URL")
            
            elif res.status_code == 429:
                print("\n🛑 STOP: Bloqueo de velocidad. Espera un rato.")
                break
            else:
                print(f"⚠️ Error {res.status_code}")
            
        except Exception as e:
            print(f"❌ Fallo: {e}")
        
        time.sleep(3)

    if resultados:
        resultados = sorted(resultados, key=lambda x: x['score'], reverse=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        print(f"\n🏆 GANADORA: {resultados[0]['nombre']} ({resultados[0]['score']})")
    else:
        print("\n💀 No se obtuvieron datos.")

if __name__ == "__main__":
    main()