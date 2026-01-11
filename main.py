import requests
import json
import time
import os
from datetime import datetime

print("\n🌍 INICIANDO ROBOT v9.0 - WEBCAMS & ICONOS\n")

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
        elif res.status_code == 401:
            print(f"   ⛔ Error 401: Revisar Clave.")
            return None
        else:
            print(f"   ⚠️ Error API: {res.status_code}")
            return None
    except Exception as e:
        print(f"   ⚠️ Error conexión: {e}")
    return None

def procesar_playas():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        playas = json.load(f)

    resultados = []
    print(f"🚀 Procesando {len(playas)} playas...")

    for i, playa in enumerate(playas):
        nombre = playa['nombre']
        coords = playa.get('coordenadas')
        descripcion = playa.get('descripcion', 'Información no disponible.')
        webcam = playa.get('webcam', None) # <--- CAPTURAMOS WEBCAM

        if not coords: continue

        lat, lon = coords
        print(f"[{i+1}/{len(playas)}] {nombre}...", end=" ", flush=True)

        datos = obtener_clima_owm(lat, lon)
        
        t_real = 0
        t_feel = 0
        viento = 0
        cielo = "Sin datos"
        humedad = 0
        visibilidad = 10000
        score = 0
        datos_validos = False
        sunset_hora = "Unknown"

        if datos:
            try:
                t_real = round(datos['main']['temp'])
                t_feel = round(datos['main']['feels_like'])
                humedad = datos['main']['humidity']
                viento = round(datos['wind']['speed'] * 3.6)
                cielo = datos['weather'][0]['description'] # Minúscula para procesar mejor
                visibilidad = datos.get('visibility', 10000)
                ts = datos['sys']['sunset']
                sunset_hora = datetime.fromtimestamp(ts).strftime('%H:%M')

                # --- ALGORITMO ---
                score = 10
                if viento > 20: score -= 2
                if viento > 28: score -= 4
                if viento > 40: score -= 7
                
                if t_feel < 20: score -= 1
                if t_feel < 18: score -= 3  
                if t_feel > 32: score -= 1

                cielo_lower = cielo.lower()
                if "nubes" in cielo_lower or "nuboso" in cielo_lower or "cubierto" in cielo_lower:
                    if "dispersas" in cielo_lower or "pocas" in cielo_lower or "algo" in cielo_lower: score -= 1
                    else: score -= 2
                elif "lluvia" in cielo_lower or "llovizna" in cielo_lower: 
                    score -= 10
                
                if visibilidad < 3000: score -= 2
                
                score = max(0, min(10, score))
                datos_validos = True
                
                # Capitalizar para mostrar bonito
                cielo_display = cielo.capitalize()
                print(f"✅ OK")

            except Exception as e:
                print(f"❌ Error datos: {e}")
                cielo_display = "Error"
        else:
            print("❌ Sin respuesta")
            cielo_display = "Sin datos"

        resultados.append({
            "nombre": nombre,
            "municipio": playa["municipio"],
            "zona": playa["zona"],
            "coordenadas": coords,
            "descripcion": descripcion,
            "webcam": webcam, # <--- GUARDAMOS WEBCAM
            "score": score,
            "clima": {
                "t_real": t_real,
                "t_feel": t_feel,
                "viento": viento,
                "cielo": cielo_display,
                "humedad": humedad,
                "visibilidad": visibilidad,
                "sunset": sunset_hora
            },
            "detalles": [cielo_display]
        })
        time.sleep(0.1)

    if len(resultados) > 0:
        resultados.sort(key=lambda x: x['score'], reverse=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        print("\n✨ FINALIZADO.")

if __name__ == "__main__":
    procesar_playas()
