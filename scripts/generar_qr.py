"""
Genera un codigo QR por cada producto listado en data/data.json.
Cada QR apunta a la pagina fija comparativa.html con el parametro ?sku=

IMPORTANTE: Este script se ejecuta UNA sola vez por producto nuevo.
Los QR no cambian cada semana; lo que cambia es data/data.json.

Uso:
    python3 generar_qr.py

Requiere:
    pip install qrcode[pil]
"""
from pathlib import Path
import json
import qrcode

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BASE_DIR / "data" / "data.json"
QR_DIR = BASE_DIR / "qr_codes"

# URL definitiva (Railway).
BASE_URL = "https://bestprice-production-15ee.up.railway.app/comparativa.html"


def main():
    if not JSON_PATH.exists():
        raise SystemExit(f"No se encontró {JSON_PATH}. Corre primero generar_datos.py")

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    QR_DIR.mkdir(exist_ok=True)

    for producto in data["productos"]:
        sku = producto["sku"]
        url = f"{BASE_URL}?sku={sku}"

        img = qrcode.make(url)
        destino = QR_DIR / f"{sku}.png"
        img.save(destino)
        print(f"SKU {sku} -> {url}  =>  {destino.name}")

    print(f"\nListo. Se generaron {len(data['productos'])} QR en {QR_DIR}")
    print(f"Recuerda actualizar BASE_URL en este script cuando definan la URL definitiva.")


if __name__ == "__main__":
    main()
