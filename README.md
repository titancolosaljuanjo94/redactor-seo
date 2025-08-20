# SEO Agent - Kmalo (Streamlit)

Herramienta de 4 pasos para redactar contenido SEO con **DataForSEO** (research SERP) y **OpenAI** (redacción).

## Estructura
- `app.py`: app Streamlit.
- `requirements.txt`: dependencias.
- `.streamlit/secrets.toml` (o Secrets en Streamlit Cloud): credenciales.

## Ejecutar local
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Variables (no subas claves a Git público)
- `DATAFORSEO_LOGIN`
- `DATAFORSEO_PASSWORD`
- `OPENAI_API_KEY`

En **Streamlit Cloud**: usa la sección **Secrets** y pega las claves con esos nombres.

## Notas
- Si no hay credenciales, la app usa **datos simulados** (paridad con tu React).
- El wordCount/headers de competidores son placeholders (DataForSEO no da wordcount).
- Ajusta `depth` y `device` según tu caso de uso.
