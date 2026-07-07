# Best Price — Backend administrativo (Railway)

Panel web para que el equipo de Pricing cargue el Excel, las fotos y el logo
sin depender de TI ni de tocar código. Reemplaza el flujo manual de scripts
que usábamos antes (`../scripts/generar_datos.py`).

## Qué incluye

- `/login` — pantalla de acceso con una clave compartida para todo Pricing.
- `/admin` — panel para:
  - Subir el Excel semanal (SKU, Producto, Marca, Precio Holi, hasta varios competidores).
  - Reemplazar el logo de Holi.
  - Subir la foto de cada producto y de cada competidor.
- `/comparativa.html` — la misma página que abre el cliente al escanear el QR
  (sin cambios), ahora alimentada por este backend en vez de un archivo estático.

## Probarlo en tu computadora

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # y edita la clave dentro de .env
export $(cat .env | xargs)  # carga las variables de entorno
uvicorn main:app --reload --port 8800
# abrir http://localhost:8800/admin
```

## Desplegar en Railway

1. **Sube esta carpeta a un repositorio de GitHub** (puede ser solo `backend/`,
   o todo `BestPrice-QR/` — en el paso 3 le indicas a Railway la carpeta raíz).
2. En [railway.app](https://railway.app), **New Project → Deploy from GitHub repo**
   y selecciona el repositorio.
3. Si subiste todo `BestPrice-QR/`, en **Settings → Root Directory** escribe
   `backend`. Railway detecta automáticamente que es Python (usa el
   `requirements.txt` y el `Procfile`).
4. En **Variables**, agrega:
   - `ADMIN_PASSWORD` → la clave que usará Pricing para entrar a `/admin`.
   - `SECRET_KEY` → cualquier texto largo y aleatorio (para firmar la sesión).
5. **Importante — agrega un Volume** (Settings → Volumes → New Volume) montado
   en `/app/static`. Sin esto, cada vez que Railway vuelva a desplegar (por
   ejemplo, al hacer un cambio de código), se perderían el `data.json`, las
   fotos y el logo ya cargados, porque el sistema de archivos normal de
   Railway es temporal.
6. Railway te da una URL pública (algo como
   `https://tu-proyecto.up.railway.app`). Esa es la URL definitiva.
7. **Actualiza los QR** para que apunten ahí: en tu computadora, edita
   `../scripts/generar_qr.py` y cambia `BASE_URL` a
   `https://tu-proyecto.up.railway.app/comparativa.html`, luego corre
   `python3 generar_qr.py` una vez para regenerar los QR definitivos (ya no
   hace falta volver a correrlo salvo que agreguen un producto nuevo).

## Cómo lo usará Pricing (una vez desplegado)

1. Entrar a `https://tu-proyecto.up.railway.app/admin` con la clave compartida.
2. Subir el Excel actualizado → los precios y la fecha se reflejan al instante.
3. Subir fotos nuevas cuando las tengan (no es obligatorio cada semana; las
   fotos ya cargadas se conservan automáticamente aunque se vuelva a subir el
   Excel).

## Notas de seguridad

- La clave (`ADMIN_PASSWORD`) es compartida para todo el equipo; si alguien
  deja de trabajar ahí, basta con cambiarla en Railway y redeployar.
- Este panel no valida el tipo real de archivo más allá de la extensión;
  está pensado para un equipo interno de confianza, no para uso público.
