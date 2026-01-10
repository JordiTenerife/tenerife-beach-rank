import requests
import json
import time
import os
from datetime import datetime

print("\n🌍 INICIANDO ROBOT v7.0 - OPENWEATHERMAP + ALGORITMO PRO\n")

try:
    API_KEY = os.environ["AEMET_API_KEY"] # Usamos la variable que ya tienes creada
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
    except Exception as e:
        print(f"   ⚠️ Error conexión: {e}")
    return None

def procesar_playas():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        playas = json.load(f)

    resultados = []
    print(f"🚀 Procesando {len(playas)} playas con nuevo algoritmo...")

    for i, playa in enumerate(playas):
        nombre = playa['nombre']
        coords = playa.get('coordenadas')

        if not coords:
            continue

        lat, lon = coords
        print(f"[{i+1}/{len(playas)}] {nombre}...", end=" ", flush=True)

        datos = obtener_clima_owm(lat, lon)
        
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

        if datos:
            try:
                # --- 1. EXTRACCIÓN DE DATOS ---
                main = datos['main']
                wind = datos['wind']
                weather = datos['weather'][0]
                sys = datos['sys']

                t_real = round(main['temp'])
                t_feel = round(main['feels_like']) # ¡Dato clave!
                humedad = main['humidity']
                
                viento = round(wind['speed'] * 3.6) # Convertir m/s a km/h
                
                cielo = weather['description'].capitalize()
                
                visibilidad = datos.get('visibility', 10000) # Metros
                
                sunset_ts = sys['sunset'] # Hora puesta sol (Unix timestamp)

                # --- 2. EL NUEVO ALGORITMO ---
                score = 10

                # A. Factor Viento 💨
                if viento > 20: score -= 2
                if viento > 28: score -= 4
                if viento > 40: score -= 7

                # B. Factor Térmico (Basado en Sensación) 🌡️
                if t_feel < 20: score -= 1
                if t_feel < 17: score -= 3 # <--- TU CAMBIO AQUÍ
                if t_feel > 32: score -= 1 # Calor excesivo

                # C. Factor Cielo ☁️
                cielo_lower = cielo.lower()
                if "nubes" in cielo_lower:
                    # Si es "nubes dispersas" o "pocas nubes" penaliza menos
                    if "dispersas" in cielo_lower or "pocas" in cielo_lower:
                        score -= 1
                    else:
                        score -= 2 # Nublado cerrado
                elif "lluvia" in cielo_lower or "llovizna" in cielo_lower:
                    score -= 10 # Nadie quiere ir a la playa lloviendo
                
                # D. Factor Calima (Visibilidad) 🌫️
                if visibilidad < 3000:
                    score -= 2

                # Limites 0-10
                score = max(0, min(10, score))
                datos_validos = True
                print(f"✅ Nota: {score}/10 | {t_feel}ºC (Sens.) | {viento}km/h")

            except Exception as e:
                print(f"❌ Error procesando: {e}")
        else:
            print("❌ Sin respuesta")

        # Formatear hora puesta de sol (HH:MM)
        sunset_hora = "Unknown"
        if sunset_ts > 0:
            sunset_hora = datetime.fromtimestamp(sunset_ts).strftime('%H:%M')

        # Guardar resultado completo
        resultados.append({
            "nombre": nombre,
            "municipio": playa["municipio"],
            "zona": playa["zona"],
            "coordenadas": coords,
            "score": score if datos_validos else 0,
            "clima": {
                "t_real": t_real,
                "t_feel": t_feel, # Nuevo
                "viento": viento,
                "cielo": cielo,
                "humedad": humedad, # Nuevo
                "visibilidad": visibilidad, # Nuevo
                "sunset": sunset_hora # Nuevo
            },
            "detalles": [cielo, f"Sensación: {t_feel}ºC", f"Viento: {viento}km/h"]
        })
        
        time.sleep(0.2) # OpenWeather es rápido

    # Ordenar ranking
    resultados.sort(key=lambda x: x['score'], reverse=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ FINALIZADO: {len(resultados)} playas actualizadas.")

if __name__ == "__main__":
    procesar_playas()
