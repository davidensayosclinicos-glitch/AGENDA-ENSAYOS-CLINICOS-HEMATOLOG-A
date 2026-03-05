# Agenda de Pacientes 2026 (Streamlit)

Aplicación en Streamlit para gestionar visitas de pacientes de ensayos clínicos.

## Ejecutar en local

```bash
streamlit run app.py
```

## Subir a Streamlit Cloud

1. Sube este proyecto a GitHub con ambos archivos de dependencias actualizados:
   - `requirements.txt` (raíz del repo)
   - `agenda-streamlit/requirements.txt`
2. En Streamlit Cloud, crea una nueva app conectando ese repositorio.
3. Elige una de estas dos configuraciones:

   **Opción A (recomendada): app en raíz**
   - **Main file path:** `agenda_medica_2026.py`

   **Opción B: app en subcarpeta**
   - **Main file path:** `agenda-streamlit/app.py`

4. Pulsa **Deploy**.

### Importante

- Si cambias dependencias, haz **Clear cache** y luego **Reboot app** en Streamlit Cloud para forzar reinstalación.

## Nota sobre datos

La app usa SQLite (`agenda_ensayos.db`) en el sistema de archivos local. En Streamlit Cloud ese almacenamiento es temporal, por lo que los datos pueden perderse en reinicios/redeploys.
