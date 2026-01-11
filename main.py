import requests
import json
import time
import os
from datetime import datetime

print("\n🌍 INICIANDO ROBOT v13.0 - DETECTOR DE PELIGROS (MEDUSAS/OBRAS)\n")

try:
    API_KEY = os.environ["AEMET_API_KEY"]
except KeyError:
    print("⚠️ Nota: Sin API Key de OpenWeather (funcionará solo con datos oficiales).")
    API_KEY = ""

INPUT_FILE = 'playas.json'
OUTPUT_FILE = 'data.json'

# --- ENLACE OFICIAL DE TU CAPTURA (YA PUESTO) ---
URL_OFICIAL_BANDERAS = "https://idecan.grafcan.es/servicios/rest/services/Costas/Playas_Zonas_Bano/MapServer/0/query?f=json&where=1%3D1&returnGeometry=false&outFields=*"
# ------------------------------------------------

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
        headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', 'Referer': 'https://visor.grafcan.es/' }
        res = requests.get(URL_OFICIAL_BANDERAS, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            # En Grafcan los datos suelen venir en 'features'
            return data.get('features', [])
    except Exception as e:
        print(f"❌ Error conexión gobierno: {e}")
    return []

def normalizar(texto):
    if not texto: return ""
    return texto.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').strip()

def detectar_avisos(propiedades):
    """Escanea todo el texto oficial buscando peligros"""
    avisos = []
    # Convertimos todos los valores del gobierno a un solo texto gigante en mayúsculas
    texto_completo = str(propiedades.values()).upper()
    
    if "MEDUSA" in texto_completo: avisos.append("medusas")
    if "OBRA" in texto_completo: avisos.append("obras")
    if "VERTIDO" in texto_completo or "FECAL" in texto_completo or "CONTAMINA" in texto_completo or "MICROALGA" in texto_completo or "E.COLI" in texto_completo: avisos.append("contaminacion")
    if "DERRUMBE" in texto_completo or "DESPRENDI" in texto_completo: avisos.append("derrumbes")
    if "CERRADA" in texto_completo or "PROHIBIDO" in texto_completo: avisos.append("cerrada")
    
    return list(set(avisos)) # Eliminar duplicados

def procesar_playas():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        mis_playas = json.load(f)

    features_gobierno = obtener_datos_oficiales()
    
    # Mapeo rápido
    mapa_gobierno = {}
    for item in features_gobierno:
        try:
            # Grafcan usa 'attributes' normalmente
            props = item.get('attributes', item.get('properties', {}))
            # Buscamos el nombre en varios campos posibles
            nombre = props.get('NOMBRE', props.get('DENOMINACION', props.get('TOPONIMO', '')))
            if nombre: mapa_gobierno[normalizar(nombre)] = props
        except: continue

    resultados = []
    print(f"🚀 Analizando {len(mis_playas)} playas...")

    for playa in mis_playas:
        nombre = playa['nombre']
        coords = playa.get('coordenadas')
        nombre_norm = normalizar(nombre)
        
        bandera_color = "gray"
        estado_texto = "Info no disponible"
        avisos_detectados = []
        
        # 1. Buscar en Gobierno (Coincidencia aproximada)
        encontrado = False
        for nombre_gob, props in mapa_gobierno.items():
            if nombre_norm in nombre_gob or nombre_gob in nombre_norm:
                # Detectar Bandera
                valores = str(props.values()).upper()
                if "ROJA" in valores: bandera_color = "red"
                elif "AMARILLA" in valores: bandera_color = "yellow"
                elif "VERDE" in valores: bandera_color = "green"
                elif "NEGRA" in valores: bandera_color = "black"
                
                # Detectar Avisos (Medusas, Obras...)
                avisos_detectados = detectar_avisos(props)
                
                estado_texto = "Oficial"
                encontrado = True
                break
        
        # 2. Plan B (Clima) si no hay dato oficial
        if not encontrado or bandera_color == "gray":
            datos_owm = obtener_clima_owm(coords[0], coords[1])
            t_real, t_feel, viento, cielo = "--", "--", "--", "Sin datos"
            
            if datos_owm:
                viento = round(datos_owm['wind']['speed'] * 3.6)
                t_real = round(datos_owm['main']['temp'])
                t_feel = round(datos_owm['main']['feels_like'])
                cielo = datos_owm['weather'][0]['description'].capitalize()
                
                if viento > 35: bandera_color = "red"
                elif viento > 20: bandera_color = "yellow"
                else: bandera_color = "green"
                estado_texto = "Estimado (Clima)"
        else:
            # Rellenar clima básico aunque tengamos bandera oficial
            t_real, t_feel, viento, cielo = "--", "--", "--", estado_texto

        # Puntuación final (Si hay medusas o caca, bajamos a 0)
        score = 5
        if bandera_color == "green": score = 10
        elif bandera_color == "yellow": score = 6
        elif bandera_color == "red": score = 2
        elif bandera_color == "black": score = 0
        
        if avisos_detectados: score = 0 # Penalización máxima por peligros

        print(f"[{'⚠️' if avisos_detectados else '✅'}] {nombre} -> {bandera_color} {avisos_detectados}")

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
            "clima": {
                "t_real": t_real, "t_feel": t_feel, "viento": viento, "cielo": cielo,
                "humedad": 0, "visibilidad": 10000, "sunset": "--:--"
            },
            "detalles": [estado_texto]
        })

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print("\n✨ FINALIZADO.")

if __name__ == "__main__":
    procesar_playas()
