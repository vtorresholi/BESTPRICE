# Best Price — QR + Comparativa (prototipo TI)

Prototipo para las tareas 4 y 5 del proyecto Best Price:
- Tarea 4: QR modelo asociado a un HTML alimentado con la comparativa.
- Tarea 5: capacitación a Pricing (ver `Guia_Capacitacion_Pricing_BestPrice.docx`).

## Estructura

```
comparativa.html          Página fija que muestra la comparativa (no cambia semana a semana)
data/
  data.json               Datos que consume comparativa.html (se regenera cada semana)
  plantilla_comparativa.xlsx   Plantilla que llena Pricing cada semana
qr_codes/                 QR generados, uno por SKU (se generan una sola vez por producto)
scripts/
  generar_datos.py        Excel -> data.json
  generar_qr.py           data.json -> QR (uno por SKU)
```

## Diseño

Layout de 2 columnas ("Mi producto" | "Comparado con:") con logo real de Holi
(verde/naranja) y badge "BEST PRICE" en magenta (Paleta 4). Por cada competidor,
el sistema calcula automáticamente el monto y porcentaje de diferencia frente al
precio Holi ("por encima" si Holi es más caro, "por debajo" si Holi es más barato).
Las imágenes de producto/competidor son opcionales: si el Excel trae una URL se
muestra la foto, si no, se muestra un ícono genérico de marcador de posición.

## Cómo probarlo localmente

```bash
pip install openpyxl "qrcode[pil]"
cd scripts
python3 generar_datos.py   # Excel -> data.json
python3 generar_qr.py      # data.json -> QR en /qr_codes

cd ..
python3 -m http.server 8000
# abrir http://localhost:8000/comparativa.html?sku=721733005901
```

### Prueba con celular en la misma red WiFi

Mientras no exista hosting definitivo, `BASE_URL` en `scripts/generar_qr.py` puede
apuntar a la IP local de la máquina (ej. `http://192.168.x.x:PUERTO/comparativa.html`)
para escanear los QR generados desde un celular conectado al mismo WiFi.

## Backend administrativo (`/backend`)

El flujo de scripts de arriba fue el prototipo inicial. Para que el equipo de
Pricing cargue el Excel, las fotos y el logo por su cuenta (sin TI y sin tocar
código), ver [`backend/README.md`](backend/README.md) — es una app web
(FastAPI) pensada para desplegar en Railway, con:
- Login con clave compartida para Pricing.
- Carga de Excel (reemplaza `generar_datos.py`, con la misma lógica).
- Carga de fotos de producto y competidores.
- Carga/reemplazo del logo de Holi.

## Pendiente antes de producción

- Desplegar `backend/` en Railway (ver instrucciones en `backend/README.md`)
  y actualizar `BASE_URL` en `scripts/generar_qr.py` a la URL final, para
  regenerar los QR una última vez antes de imprimir.
- Los QR son estáticos: solo se regeneran cuando entra un producto nuevo al programa.
- Conseguir imágenes reales de producto y logos de competidores (ya se pueden
  cargar directamente desde el panel `/admin` del backend).
