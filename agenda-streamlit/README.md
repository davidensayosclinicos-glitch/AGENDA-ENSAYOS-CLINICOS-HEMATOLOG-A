# Agenda de Pacientes 2026 (Streamlit)

Aplicación en Streamlit para gestionar visitas de pacientes de ensayos clínicos.

## Ejecutar en local

```bash
streamlit run app.py
```

## Subir a Streamlit Cloud

1. Sube estos archivos a un repositorio de GitHub:
   - `app.py`
   - `agenda_medica_2026.py`
   - `requirements.txt`
2. En Streamlit Cloud, crea una nueva app conectando ese repositorio.
3. En **Main file path**, usa `app.py`.
4. Pulsa **Deploy**.

## Nota sobre datos

La app usa SQLite (`agenda_ensayos.db`) en el sistema de archivos local. En Streamlit Cloud ese almacenamiento es temporal, por lo que los datos pueden perderse en reinicios/redeploys.
