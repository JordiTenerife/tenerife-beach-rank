import requests
import json
import time
import os
from datetime import datetime

print("\n🌍 INICIANDO ROBOT v7.1 - DEBUGGER MODE\n")

try:
    API_KEY = os.environ["AEMET_API_KEY"]
except KeyError:
    print("❌ ERROR: Falta la API Key.")
    exit(1)

INPUT_FILE = 'playas.json'
OUTPUT_FILE = 'data.json'

def obtener_clima_owm(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=es"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()
        else:
            # AQUÍ ESTÁ EL CAMBIO: Ahora nos dirá qué pasa
            print(f"   ⚠️ ERROR API: {res.status_code} (Revisar Clave)")
            return None
    except Exception as e:
        print(f"   ⚠️ Error conexión: {e}")
    return None

def procesar_playas():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        playas = json.load(f)

    resultados = []
    print(f"🚀 Procesando {len(playas)} playas...")

    # Solo probamos las 3 primeras para no saturar el log si falla
    for i, playa in enumerate(playas):
        nombre = playa['nombre']
        coords = playa.get('coordenadas')

        if not coords: continue

        lat, lon = coords
        print(f"[{i+1}/{len(playas)}] {nombre}...", end=" ", flush=True)

        datos = obtener_clima_owm(lat, lon)
        
        # ... (Resto del código igual que v7.0) ...
        # Para el diagnóstico, si falla, cortamos rápido
        if not datos:
            print("❌ FALLO")
            # Si falla la primera, es probable que fallen todas.
            # Seguimos, pero ya sabemos que hay error.
        else:
             # Valores por defecto (neutros)
            t_real = 0
            t_feel = 0
            viento = 0
            cielo = "Sin datos"
            humedad = 0
            visibilidad = 10000
            sunset_ts = 0
            score = 0
            datos_validos = False

            try:
                main = datos['main']
                wind = datos['wind']
                weather = datos['weather'][0]
                sys = datos['sys']

                t_real = round(main['temp'])
                t_feel = round(main['feels_like'])
                humedad = main['humidity']
                viento = round(wind['speed'] * 3.6)
                cielo = weather['description'].capitalize()
                visibilidad = datos.get('visibility', 10000)
                sunset_ts = sys['sunset']

                # ALGORITMO
                score = 10
                if viento > 20: score -= 2
                if viento > 28: score -= 4
                if viento > 40: score -= 7
                if t_feel < 20: score -= 1
                if t_feel < 17: score -= 3
                if t_feel > 32: score -= 1

                cielo_lower = cielo.lower()
                if "nubes" in cielo_lower:
                    if "dispersas" in cielo_lower or "pocas" in cielo_lower: score -= 1
                    else: score -= 2
                elif "lluvia" in cielo_lower: score -= 10
                
                if visibilidad < 3000: score -= 2
                score = max(0, min(10, score))
                datos_validos = True
                print(f"✅ OK ({t_feel}ºC)")

            except Exception as e:
                print(f"❌ Error procesando: {e}")

        # Guardar resultado (aunque sea vacío para no romper mapa)
        sunset_hora = "Unknown"
        if datos and datos_validos:
             sunset_hora = datetime.fromtimestamp(datos['sys']['sunset']).strftime('%H:%M')
        
        resultados.append({
            "nombre": nombre,
            "municipio": playa["municipio"],
            "zona": playa["zona"],
            "coordenadas": coords,
            "score": score if datos_validos else 0,
            "clima": {
                "t_real": t_real if datos_validos else 0,
                "t_feel": t_feel if datos_validos else 0,
                "viento": viento if datos_validos else 0,
                "cielo": cielo if datos_validos else "Sin datos",
                "humedad": humedad if datos_validos else 0,
                "visibilidad": visibilidad if datos_validos else 10000,
                "sunset": sunset_hora
            },
            "detalles": [cielo if datos_validos else "Sin datos"]
        })
        time.sleep(0.1)

    resultados.sort(key=lambda x: x['score'], reverse=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    procesar_playas()
