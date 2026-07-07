"""
Backend administrativo para Best Price (Holi).

Permite al equipo de Pricing, sin tocar codigo:
- Subir el Excel semanal con SKU, Producto, Marca, Precio Holi y hasta
  varios competidores (tienda + precio).
- Subir la foto de cada producto y de cada competidor.
- Reemplazar el logo de Holi.

El resultado (static/data/data.json) alimenta directamente comparativa.html,
que ya usa el equipo de tienda via el QR impreso.
"""
import io
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import openpyxl
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_JSON_PATH = STATIC_DIR / "data" / "data.json"
IMAGES_DIR = STATIC_DIR / "images"
LOGOS_DIR = STATIC_DIR / "logos"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "bestprice2026")
SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
RE_TIENDA = re.compile(r"^Tienda (\d+)$")

app = FastAPI(title="Best Price - Panel de Pricing")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
LOGOS_DIR.mkdir(parents=True, exist_ok=True)
DATA_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Autenticacion (clave compartida para todo el equipo de Pricing)
# ---------------------------------------------------------------------------

class RedirectToLogin(Exception):
    pass


@app.exception_handler(RedirectToLogin)
def _redirect_to_login(request: Request, exc: RedirectToLogin):
    return RedirectResponse("/login", status_code=303)


def require_login(request: Request):
    if not request.session.get("autenticado"):
        raise RedirectToLogin()
    return True


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
def login_submit(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        request.session["autenticado"] = True
        return RedirectResponse("/admin", status_code=303)
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------------------
# Datos: leer / escribir data.json
# ---------------------------------------------------------------------------

def cargar_data():
    if not DATA_JSON_PATH.exists():
        return {"fecha_comparativa": "", "productos": []}
    import json
    return json.loads(DATA_JSON_PATH.read_text(encoding="utf-8"))


def guardar_data(data):
    import json
    DATA_JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fmt_fecha(valor):
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return f"{MESES_ES[valor.month - 1].capitalize()} {valor.day}, {valor.year}"
    return str(valor).strip()


def detectar_columnas_competidor(encabezados):
    numeros = sorted(int(m.group(1)) for h in encabezados if (m := RE_TIENDA.match(h)))
    return [
        (f"Tienda {n}", f"Producto Competidor {n}", f"Precio Competidor {n}",
         f"Imagen Competidor {n}", f"Fecha Competidor {n}")
        for n in numeros
    ]


def parsear_excel(contenido: bytes):
    wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
    hoja = wb.active

    encabezados = [str(c.value).strip() if c.value else "" for c in hoja[1]]
    col_idx = {nombre: i for i, nombre in enumerate(encabezados)}

    requeridas = ["SKU", "Producto", "Marca", "Precio Holi"]
    faltantes = [c for c in requeridas if c not in col_idx]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias en el Excel: {', '.join(faltantes)}")

    columnas_competidor = detectar_columnas_competidor(encabezados)
    productos = []
    fecha_general = None

    for fila in hoja.iter_rows(min_row=2, values_only=False):
        def val(nombre_col):
            idx = col_idx.get(nombre_col)
            return fila[idx].value if idx is not None else None

        sku = val("SKU")
        if sku is None or str(sku).strip() == "":
            continue

        fecha_fila = fmt_fecha(val("Fecha Comparativa")) if "Fecha Comparativa" in col_idx else None
        if fecha_fila:
            fecha_general = fecha_fila

        competidores = []
        for col_tienda, col_producto, col_precio, col_imagen, col_fecha in columnas_competidor:
            tienda = val(col_tienda)
            precio_comp = val(col_precio)
            if tienda and precio_comp not in (None, ""):
                competidores.append({
                    "tienda": str(tienda).strip(),
                    "producto": str(val(col_producto) or "").strip(),
                    "precio": round(float(precio_comp), 2),
                    "imagen": str(val(col_imagen) or "").strip(),
                    "fecha": fmt_fecha(val(col_fecha)) or fecha_fila,
                })

        productos.append({
            "sku": str(sku).strip(),
            "nombre": str(val("Producto")).strip(),
            "marca": str(val("Marca") or "").strip(),
            "imagen": "",
            "precio_holi": round(float(val("Precio Holi")), 2),
            "competidores": competidores,
        })

    fecha_general = fecha_general or fmt_fecha(datetime.now())
    return fecha_general, productos


def fusionar_imagenes(productos_nuevos, data_anterior):
    """Conserva las imagenes ya subidas (producto y competidores) al reemplazar
    los datos con un Excel nuevo, para que Pricing no pierda fotos cada semana."""
    anteriores_por_sku = {p["sku"]: p for p in data_anterior.get("productos", [])}

    for producto in productos_nuevos:
        anterior = anteriores_por_sku.get(producto["sku"])
        if not anterior:
            continue
        if anterior.get("imagen"):
            producto["imagen"] = anterior["imagen"]

        anteriores_comp_por_tienda = {
            c["tienda"]: c for c in anterior.get("competidores", [])
        }
        for comp in producto["competidores"]:
            comp_anterior = anteriores_comp_por_tienda.get(comp["tienda"])
            if comp_anterior and comp_anterior.get("imagen"):
                comp["imagen"] = comp_anterior["imagen"]

    return productos_nuevos


# ---------------------------------------------------------------------------
# Panel administrativo
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, _=Depends(require_login), msg: str = "", error: str = ""):
    data = cargar_data()
    logo_existe = (LOGOS_DIR / "holi-logo.png").exists()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "data": data,
        "logo_existe": logo_existe,
        "msg": msg,
        "error": error,
    })


@app.post("/admin/excel")
async def admin_subir_excel(request: Request, archivo: UploadFile = File(...), _=Depends(require_login)):
    try:
        contenido = await archivo.read()
        fecha_general, productos_nuevos = parsear_excel(contenido)
        data_anterior = cargar_data()
        productos_nuevos = fusionar_imagenes(productos_nuevos, data_anterior)
        guardar_data({"fecha_comparativa": fecha_general, "productos": productos_nuevos})
        msg = quote(f"Excel cargado: {len(productos_nuevos)} producto(s) actualizados.")
        return RedirectResponse(f"/admin?msg={msg}", status_code=303)
    except Exception as exc:
        return RedirectResponse(f"/admin?error={quote(str(exc))}", status_code=303)


@app.post("/admin/imagen-producto")
async def admin_subir_imagen_producto(
    request: Request, sku: str = Form(...), archivo: UploadFile = File(...), _=Depends(require_login)
):
    data = cargar_data()
    producto = next((p for p in data["productos"] if p["sku"] == sku), None)
    if not producto:
        return RedirectResponse("/admin?error=Producto no encontrado", status_code=303)

    extension = Path(archivo.filename).suffix or ".jpg"
    nombre_archivo = f"{sku}__producto{extension}"
    destino = IMAGES_DIR / nombre_archivo
    destino.write_bytes(await archivo.read())

    producto["imagen"] = f"images/{nombre_archivo}"
    guardar_data(data)
    msg = quote(f"Imagen de producto actualizada para SKU {sku}.")
    return RedirectResponse(f"/admin?msg={msg}", status_code=303)


@app.post("/admin/imagen-competidor")
async def admin_subir_imagen_competidor(
    request: Request,
    sku: str = Form(...),
    indice: int = Form(...),
    archivo: UploadFile = File(...),
    _=Depends(require_login),
):
    data = cargar_data()
    producto = next((p for p in data["productos"] if p["sku"] == sku), None)
    if not producto or indice >= len(producto["competidores"]):
        return RedirectResponse("/admin?error=Producto o competidor no encontrado", status_code=303)

    competidor = producto["competidores"][indice]
    extension = Path(archivo.filename).suffix or ".jpg"
    nombre_archivo = f"{sku}__comp{indice}{extension}"
    destino = IMAGES_DIR / nombre_archivo
    destino.write_bytes(await archivo.read())

    competidor["imagen"] = f"images/{nombre_archivo}"
    guardar_data(data)
    msg = quote(f"Imagen de {competidor['tienda']} actualizada para SKU {sku}.")
    return RedirectResponse(f"/admin?msg={msg}", status_code=303)


@app.post("/admin/logo")
async def admin_subir_logo(request: Request, archivo: UploadFile = File(...), _=Depends(require_login)):
    destino = LOGOS_DIR / "holi-logo.png"
    destino.write_bytes(await archivo.read())
    return RedirectResponse(f"/admin?msg={quote('Logo de Holi actualizado.')}", status_code=303)


# ---------------------------------------------------------------------------
# Sitio publico (comparativa.html, data.json, logos, qr, imagenes)
# ---------------------------------------------------------------------------

@app.get("/")
def home():
    return RedirectResponse("/comparativa.html")


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
