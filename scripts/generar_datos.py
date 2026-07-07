"""
Convierte la plantilla Excel de Pricing (plantilla_comparativa.xlsx)
en el archivo data/data.json que alimenta la pagina comparativa.html.

Uso:
    python3 generar_datos.py

Requiere:
    pip install openpyxl
"""
import json
import re
from pathlib import Path
from datetime import datetime
import openpyxl

BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = BASE_DIR / "data" / "plantilla_comparativa.xlsx"
JSON_PATH = BASE_DIR / "data" / "data.json"

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

RE_TIENDA = re.compile(r"^Tienda (\d+)$")


def detectar_columnas_competidor(encabezados):
    """Detecta automaticamente cuantos bloques 'Tienda N' hay en el Excel,
    sin importar el numero (permite agregar mas competidores sin tocar el script)."""
    numeros = sorted(
        int(m.group(1)) for h in encabezados if (m := RE_TIENDA.match(h))
    )
    return [(f"Tienda {n}", f"Precio Competidor {n}") for n in numeros]


def fmt_fecha(valor):
    """Convierte una fecha (datetime o texto) al formato 'Julio 6, 2026'."""
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return f"{MESES_ES[valor.month - 1].capitalize()} {valor.day}, {valor.year}"
    return str(valor).strip()


def leer_excel():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    hoja = wb.active

    encabezados = [str(c.value).strip() if c.value else "" for c in hoja[1]]
    col_idx = {nombre: i for i, nombre in enumerate(encabezados)}

    requeridas = ["SKU", "Producto", "Marca", "Precio Holi"]
    faltantes = [c for c in requeridas if c not in col_idx]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias en el Excel: {faltantes}")

    columnas_competidor = detectar_columnas_competidor(encabezados)
    productos = []

    for fila in hoja.iter_rows(min_row=2, values_only=False):
        def val(nombre_col):
            idx = col_idx.get(nombre_col)
            return fila[idx].value if idx is not None else None

        sku = val("SKU")
        if sku is None or str(sku).strip() == "":
            continue

        competidores = []
        for col_tienda, col_precio in columnas_competidor:
            tienda = val(col_tienda)
            precio_comp = val(col_precio)
            if tienda and precio_comp not in (None, ""):
                competidores.append({
                    "tienda": str(tienda).strip(),
                    "precio": round(float(precio_comp), 2),
                })

        productos.append({
            "sku": str(sku).strip(),
            "nombre": str(val("Producto")).strip(),
            "marca": str(val("Marca") or "").strip(),
            "imagen": "",
            "precio_holi": round(float(val("Precio Holi")), 2),
            "competidores": competidores,
        })

    # La fecha de la comparativa siempre es la fecha en que se genera el
    # archivo, no algo que Pricing tenga que llenar en el Excel.
    fecha_comparativa_general = fmt_fecha(datetime.now())

    return fecha_comparativa_general, productos


def fusionar_imagenes(productos_nuevos, data_anterior):
    """Conserva la foto ya subida de cada producto al reemplazar los datos
    con un Excel nuevo, para que Pricing no la vuelva a subir cada semana."""
    anteriores_por_sku = {p["sku"]: p for p in data_anterior.get("productos", [])}
    for producto in productos_nuevos:
        anterior = anteriores_por_sku.get(producto["sku"])
        if anterior and anterior.get("imagen"):
            producto["imagen"] = anterior["imagen"]
    return productos_nuevos


def main():
    if not EXCEL_PATH.exists():
        raise SystemExit(
            f"No se encontró el archivo: {EXCEL_PATH}\n"
            "Copia tu Excel actualizado en la carpeta 'data' con el nombre 'plantilla_comparativa.xlsx'."
        )

    fecha_comparativa, productos = leer_excel()

    data_anterior = {}
    if JSON_PATH.exists():
        data_anterior = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    productos = fusionar_imagenes(productos, data_anterior)

    data = {
        "fecha_comparativa": fecha_comparativa,
        "productos": productos,
    }

    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo. Se generó {JSON_PATH} con {len(productos)} producto(s).")
    print(f"Fecha de la comparativa: {fecha_comparativa}")


if __name__ == "__main__":
    main()
