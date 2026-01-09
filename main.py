import requests
import os
import urllib3

print("\n🚑 INICIANDO DIAGNÓSTICO DE CONEXIÓN AEMET...\n")

# 1. VERIFICAR LA LLAVE
try:
    API_KEY = os.environ["AEMET_API_KEY"]
    # Mostramos los primeros 4 caracteres para ver si la lee bien (sin revelar el resto)
    print(f"🔑 Llave detectada: {API_KEY[:4]}...******")
    print(f"📏 Longitud de la llave: {len(API_KEY)} caracteres")
except KeyError:
    print("❌ ERROR GRAVE: No encuentro la variable AEMET_API_KEY.")
    exit(1)

# 2. PROBAR CONEXIÓN (Playa de Las Teresitas)
id_playa = "3803806"
url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/playa/{id_playa}"

headers = {
    'api_key': API_KEY,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Accept': 'application/json'
}

print(f"\n📡 Contactando con AEMET para playa {id_playa}...")

try:
    # Desactivar avisos SSL para ver limpio el error
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    response = requests.get(url, headers=headers, verify=False, timeout=10)
    
    print(f"\n📊 CÓDIGO DE RESPUESTA: {response.status_code}")
    print(f"📝 MENSAJE DEL SERVIDOR: {response.text}\n")

    if response.status_code == 200:
        print("✅ ¡CONEXIÓN EXITOSA! La llave funciona y AEMET responde.")
        print("El problema podría estar en el bucle de las 60 playas.")
    elif response.status_code == 401:
        print("⛔ ERROR 401: NO AUTORIZADO.")
        print("Causas probables:")
        print("1. La API Key está mal copiada.")
        print("2. Tienes espacios en blanco al principio o final de la llave en GitHub Secrets.")
        print("3. AEMET aún no ha activado la llave nueva (tarda unos minutos).")
    elif response.status_code == 403 or response.status_code == 429:
        print("🚫 ERROR 403/429: BLOQUEADO.")
        print("AEMET ha bloqueado temporalmente la IP de GitHub.")
    else:
        print("⚠️ ERROR DESCONOCIDO.")

except Exception as e:
    print(f"💥 ERROR DE PYTHON: {e}")

print("\n🏁 DIAGNÓSTICO FINALIZADO.")
