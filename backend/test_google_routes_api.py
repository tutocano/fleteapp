"""
Script de diagnostico standalone: prueba tu GOOGLE_MAPS_API_KEY directamente contra
Google Routes API y muestra el error completo si falla (el conector de la app
oculta el detalle a proposito para no romper el calculo, pero aqui si lo mostramos).

Uso:
    GOOGLE_MAPS_API_KEY="tu-key-aqui" python test_google_routes_api.py

No requiere el resto de la app ni base de datos -- solo httpx y tu API key.
"""
import os
import sys

import httpx

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

# Dos puntos de prueba en Bogota (CEDI Norte -> un cliente cualquiera).
ORIGEN = (4.7110, -74.0721)
DESTINO = (4.6467, -74.0631)


def main():
    if not API_KEY:
        print("ERROR: no encontre la variable de entorno GOOGLE_MAPS_API_KEY.")
        print('Corre este script asi: GOOGLE_MAPS_API_KEY="tu-key" python test_google_routes_api.py')
        sys.exit(1)

    print(f"Probando Google Routes API con key que empieza en: {API_KEY[:10]}...")

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
    }
    payload = {
        "origin": {"location": {"latLng": {"latitude": ORIGEN[0], "longitude": ORIGEN[1]}}},
        "destination": {"location": {"latLng": {"latitude": DESTINO[0], "longitude": DESTINO[1]}}},
        "travelMode": "DRIVE",
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=10.0, trust_env=False)
    except Exception as exc:
        print(f"\nERROR DE RED/CONEXION: {exc!r}")
        sys.exit(1)

    print(f"\nHTTP status: {resp.status_code}")
    print("Respuesta completa de Google:")
    print(resp.text)

    if resp.status_code >= 400:
        print("\n--- La llamada FALLO. Causas mas comunes segun el status ---")
        if resp.status_code == 403:
            print(
                "403 = casi siempre significa que 'Routes API' NO esta habilitada para "
                "este proyecto de Google Cloud, o que la API key tiene restricciones "
                "que bloquean esta API/dominio/IP. Ve a Google Cloud Console > APIs y "
                "servicios > Biblioteca > busca 'Routes API' > Habilitar. Tambien revisa "
                "Google Cloud Console > APIs y servicios > Credenciales > tu API key > "
                "'Restricciones de API' (debe incluir Routes API o no tener restriccion)."
            )
        elif resp.status_code == 400:
            print(
                "400 = solicitud mal formada, o el proyecto no tiene facturacion (billing) "
                "activada. Routes API SIEMPRE requiere una cuenta de facturacion asociada "
                "al proyecto de Google Cloud, incluso si usas el credito gratuito. Ve a "
                "Google Cloud Console > Facturacion y confirma que el proyecto de esta key "
                "tiene una cuenta de facturacion activa vinculada."
            )
        elif resp.status_code == 429:
            print("429 = se supero la cuota/limite de peticiones para esta key.")
        else:
            print("Revisa el mensaje de 'error' en la respuesta completa de arriba.")
    else:
        print("\n--- EXITO: la API respondio bien. Revisa que 'routes' venga con datos arriba. ---")


if __name__ == "__main__":
    main()
