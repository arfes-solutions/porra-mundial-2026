# Porra Mundial 2026

Base nueva para evolucionar la porra del Mundial 2026.

## Arranque local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

La app pública arranca en:

```text
http://127.0.0.1:5000
```

## Estado

La carpeta `app/` contiene la nueva estructura limpia. Los archivos `app.py` y `admin.py` antiguos se mantienen de momento como referencia funcional mientras se migra la logica.

La primera fase busca:

- Dependencias reproducibles.
- Estructura Flask separada.
- Datos del torneo centralizados.
- Servicios de puntuación aislados.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest
```

## Base de datos

La app nueva usa SQLite en `instance/mundial.db`.

Inicializar la base:

```powershell
$env:FLASK_APP="run.py"
.venv\Scripts\flask.exe init-db
```

Migrar datos desde el prototipo antiguo (`participantes.json` y `resultados.txt`):

```powershell
$env:FLASK_APP="run.py"
.venv\Scripts\flask.exe migrate-legacy
```

## Despliegue objetivo

La direccion recomendada para produccion es:

- Vercel para publicar la app.
- Supabase/Postgres para datos persistentes.
- Variables de entorno para credenciales y secretos.

Variables necesarias en Vercel:

```text
SECRET_KEY=...
STORAGE_BACKEND=supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
```

La clave `sb_publishable_...` no se usa en esta app mientras Flask sea quien consulta Supabase desde servidor. La clave `sb_secret_...` debe guardarse solo como variable secreta de entorno.

Durante el desarrollo y los tests se usa SQLite para no depender de credenciales reales. La capa `app/storage/` existe para que produccion use Supabase sin reescribir rutas, templates ni logica de puntuacion.
- Templates y CSS fuera de Python.
