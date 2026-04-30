# Gold Oracle Scalper — Dashboard Público

Dashboard de resultados en tiempo real alojado en GitHub Pages, alimentado automáticamente desde Google Sheets.

---

## 🚀 Instalación paso a paso

### PASO 1 — Crear el repositorio en GitHub

1. Ve a [github.com](https://github.com) → **New repository**
2. Nombre: `gold-oracle-dashboard` (o el que quieras)
3. Visibilidad: **Public** (necesario para GitHub Pages gratis)
4. Click **Create repository**

### PASO 2 — Subir los archivos

Sube estos 4 archivos al repositorio:
```
generate_dashboard.py
requirements.txt
README.md
.github/workflows/update_dashboard.yml
```

La carpeta `.github/workflows/` la tienes que crear manualmente en GitHub:
- Click **Add file → Create new file**
- Escribe como nombre: `.github/workflows/update_dashboard.yml`
- Pega el contenido del archivo

### PASO 3 — Obtener el ID de tu Google Sheet

1. Abre tu Google Sheet
2. Mira la URL: `https://docs.google.com/spreadsheets/d/`**`ESTE_ES_EL_ID`**`/edit...`
3. Copia ese ID

### PASO 4 — Hacer el Sheet público (solo lectura)

1. En Google Sheets → **Compartir** (botón arriba derecha)
2. Click en **"Cambiar a cualquier persona con el enlace"**
3. Permisos: **Lector** (solo ver, no editar)
4. Click **Listo**

> ⚠️ Esto solo permite VER los datos, nadie puede editar tu sheet.

### PASO 5 — Poner tu Sheet ID en el script

1. Abre `generate_dashboard.py` en GitHub
2. Busca la línea:
   ```python
   SHEET_ID = "TU_SHEET_ID_AQUI"
   ```
3. Reemplaza `TU_SHEET_ID_AQUI` por el ID que copiaste en el Paso 3
4. Guarda el archivo (Commit changes)

### PASO 6 — Activar GitHub Pages

1. En tu repositorio → **Settings** → **Pages** (menú izquierdo)
2. Source: **Deploy from a branch**
3. Branch: **main** → carpeta **/ (root)**
4. Click **Save**

GitHub te dará una URL tipo: `https://TU_USUARIO.github.io/gold-oracle-dashboard`

### PASO 7 — Lanzar el primer build

1. Ve a la pestaña **Actions** en tu repositorio
2. Click en **"Update Dashboard"**
3. Click en **"Run workflow"** → **"Run workflow"**
4. Espera ~1 minuto

¡Listo! Tu dashboard estará en la URL de GitHub Pages.

---

## ⚙️ ¿Con qué frecuencia se actualiza?

El workflow está configurado para ejecutarse **cada 30 minutos** automáticamente.
Si quieres más frecuencia, edita esta línea en el workflow:

```yaml
- cron: '*/30 * * * *'   # cada 30 min
- cron: '*/10 * * * *'   # cada 10 min
- cron: '0 * * * *'      # cada hora
```

> GitHub Actions tiene un límite de ~2.000 minutos/mes en cuentas gratuitas.
> Con cada 30 min usas ~1.440 min/mes, dentro del límite.

---

## 🗂️ Estructura de archivos

```
gold-oracle-dashboard/
├── .github/
│   └── workflows/
│       └── update_dashboard.yml   ← Automatización
├── generate_dashboard.py          ← Script principal
├── requirements.txt               ← Dependencias Python
├── index.html                     ← Dashboard generado (auto)
└── README.md
```

---

## ❓ Problemas frecuentes

| Problema | Solución |
|---|---|
| El workflow falla con error 403 | El Sheet no es público, revisa el Paso 4 |
| No aparecen datos en el dashboard | Verifica el SHEET_ID en generate_dashboard.py |
| Los nombres de las hojas no coinciden | En generate_dashboard.py, la variable `SHEETS` debe tener los nombres exactos de tus pestañas |
| GitHub Pages muestra 404 | Espera 2-3 minutos tras activarlo, o verifica que index.html existe en la rama main |
