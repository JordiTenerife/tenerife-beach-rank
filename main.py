import requests
import json
import time
import os
from datetime import datetime

print("\n🌍 INICIANDO ROBOT v16.0 - PUNTUACIÓN HÍBRIDA (CLIMA + OFICIAL)\n")

try:
    API_KEY = os.environ["AEMET_API_KEY"]
except KeyError:
    print("⚠️ Nota: Sin API Key. Usando solo datos oficiales.")
    API_KEY = ""

INPUT_FILE = 'playas.json'
OUTPUT_FILE = 'data.json'

# ENLACE OFICIAL DEL GOBIERNO DE CANARIAS
URL_OFICIAL_BANDERAS = "https://idecan.grafcan.es/servicios/rest/services/Costas/Playas_Zonas_Bano/MapServer/0/query?f=json&where=1%3D1&returnGeometry=false&outFields=*"

MAPA_COLORES = {
    "VERDE": "green", "AMARILLA": "yellow", "ROJA": "red", 
    "NEGRA": "black", "CERRADA": "black", "PROHIBIDO": "red"
}

def obtener_clima_owm(lat, lon):
    if not API_KEY: return None
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=es"
    try:
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def obtener_datos_oficiales():
    try:
        print(f"📡 Conectando con Servidor Gobierno...")
        headers = { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://visor.grafcan.es/' }
        res = requests.get(URL_OFICIAL_BANDERAS, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data.get('features', [])
    except Exception as e:
        print(f"❌ Error conexión gobierno: {e}")
    return []

def normalizar(texto):
    if not texto: return ""
    return texto.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').strip()

def detectar_avisos(propiedades):
    avisos = []
    texto_completo = str(propiedades.values()).upper()
    
    if "MEDUSA" in texto_completo: avisos.append("medusas")
    if "OBRA" in texto_completo: avisos.append("obras")
    if "VERTIDO" in texto_completo or "FECAL" in texto_completo or "CONTAMINA" in texto_completo or "MICROALGA" in texto_completo or "E.COLI" in texto_completo: avisos.append("contaminacion")
    if "DERRUMBE" in texto_completo or "DESPRENDI" in texto_completo: avisos.append("derrumbes")
    if "CERRADA" in texto_completo or "PROHIBIDO" in texto_completo: avisos.append("cerrada")
    
    return list(set(avisos))

def procesar_playas():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        mis_playas = json.load(f)

    features_gobierno = obtener_datos_oficiales()
    
    mapa_gobierno = {}
    for item in features_gobierno:
        try:
            props = item.get('attributes', item.get('properties', {}))
            nombre = props.get('NOMBRE', props.get('DENOMINACION', ''))
            if nombre: mapa_gobierno[normalizar(nombre)] = props
        except: continue

    resultados = []
    print(f"🚀 Analizando {len(mis_playas)} playas...")

    for playa in mis_playas:
        nombre = playa['nombre']
        coords = playa.get('coordenadas')
        nombre_norm = normalizar(nombre)
        
        # Variables Clima
        lat, lon = coords
        datos_owm = obtener_clima_owm(lat, lon)
        
        t_real = 0
        t_feel = 0
        viento = 0
        cielo = "Sin datos"
        visibilidad = 10000
        sunset_ts = 0
        
        if datos_owm:
            t_real = round(datos_owm['main']['temp'])
            t_feel = round(datos_owm['main']['feels_like'])
            viento = round(datos_owm['wind']['speed'] * 3.6)
            cielo = datos_owm['weather'][0]['description'].capitalize()
            visibilidad = datos_owm.get('visibility', 10000)
            sunset_ts = datos_owm['sys']['sunset']

        # Variables Oficiales
        bandera_color = "gray"
        estado_texto = "Info no disponible"
        avisos_detectados = []
        origen = "Estimado"
        
        encontrado = False
        for nombre_gob, props in mapa_gobierno.items():
            if nombre_norm in nombre_gob or nombre_gob in nombre_norm:
                valores = str(props.values()).upper()
                if "ROJA" in valores: bandera_color = "red"
                elif "AMARILLA" in valores: bandera_color = "yellow"
                elif "VERDE" in valores: bandera_color = "green"
                elif "NEGRA" in valores: bandera_color = "black"
                
                avisos_detectados = detectar_avisos(props)
                estado_texto = "Datos Oficiales"
                origen = "Oficial"
                encontrado = True
                break
        
        # Si no hay oficial, estimar bandera por viento
        if not encontrado or bandera_color == "gray":
            if viento > 35: bandera_color = "red"
            elif viento > 20: bandera_color = "yellow"
            else: bandera_color = "green"
            estado_texto = "Estimado por Clima"

        # --- ALGORITMO DE PUNTUACIÓN COMPLETO ---
        score = 10 
        
        # 1. Penalizaciones CLIMÁTICAS (Recuperadas)
        if t_feel < 20: score -= 1
        if t_feel < 18: score -= 3  # Frío
        
        if "nubes" in cielo.lower() or "cubierto" in cielo.lower():
            if "dispersas" in cielo.lower() or "pocas" in cielo.lower(): score -= 1
            else: score -= 2
        if "lluvia" in cielo.lower(): score -= 5 # Lluvia molesta
        
        if visibilidad < 3000: score -= 2 # Calima
        
        if viento > 20: score -= 2
        if viento > 28: score -= 4 # Viento fuerte resta aunque haya bandera verde

        # 2. Penalizaciones OFICIALES (Tu solicitud)
        if bandera_color == "yellow": score -= 5
        if bandera_color == "red": score -= 5
        
        if "medusas" in avisos_detectados: score -= 5
        if "contaminacion" in avisos_detectados: score -= 5
        if "obras" in avisos_detectados: score -= 3 # Molestia, no prohibición
        
        # 3. Penalización ELIMINATORIA (Playa cerrada)
        if "cerrada" in avisos_detectados or bandera_color == "black": 
            score -= 10 # Baja al fondo
            
        # Asegurar rango 0-10
        score = max(0, min(10, score))

        print(f"[{bandera_color.upper()}] {nombre} -> Nota: {score}")

        resultados.append({
            "nombre": nombre,
            "municipio": playa["municipio"],
            "zona": playa["zona"],
            "coordenadas": coords,
            "descripcion": playa.get('descripcion', {}),
            "webcam": playa.get('webcam', None),
            "score": score,
            "bandera": bandera_color,
            "avisos": avisos_detectados,
            "origen": origen,
            "clima": {
                "t_real": t_real,
                "t_feel": t_feel,
                "viento": viento,
                "cielo": cielo,
                "visibilidad": visibilidad,
                "sunset": sunset_ts
            },
            "detalles": [estado_texto]
        })

    # --- ORDENAR: De mayor puntuación a menor ---
    resultados.sort(key=lambda x: x['score'], reverse=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print("\n✨ FINALIZADO.")

if __name__ == "__main__":
    procesar_playas()
