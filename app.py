import os, time, json
import requests
import streamlit as st
from typing import Dict, Any, List

# =====================
# Configuración básica
# =====================
st.set_page_config(page_title="SEO Agent - Redactor", page_icon="🔎", layout="wide")
st.title("SEO Agent - Kmalo")
st.caption("Tu asistente para crear contenido SEO optimizado (Streamlit + DataForSEO + OpenAI)")

# =====================
# Secrets / Env
# =====================
DATAFORSEO_LOGIN = st.secrets.get("DATAFORSEO_LOGIN", os.getenv("DATAFORSEO_LOGIN", ""))
DATAFORSEO_PASSWORD = st.secrets.get("DATAFORSEO_PASSWORD", os.getenv("DATAFORSEO_PASSWORD", ""))
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))

# =====================
# Estado
# =====================
if "step" not in st.session_state: st.session_state.step = 1
if "keyword" not in st.session_state: st.session_state.keyword = ""
if "competitor_data" not in st.session_state: st.session_state.competitor_data = None
if "content_strategy" not in st.session_state: st.session_state.content_strategy = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {
        "relatedKeywords": "",
        "title": "",
        "tone": "profesional",
        "wordCount": 1500,
        "ai_model": "gpt-4o-mini",
        "temperature": 0.6,
        "max_tokens": 2000,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.1,
        "optimization_mode": "Balanced"
    }
if "selected_structure" not in st.session_state: st.session_state.selected_structure = None
if "final_html" not in st.session_state: st.session_state.final_html = ""

# =====================
# FUNCIONES NUEVAS
# =====================
def propose_structures(keyword: str, strategy: Dict = None, ai_model: str = "gpt-4o-mini") -> List[Dict[str, Any]]:
    """
    Usa OpenAI para generar 3 propuestas de estructuras con headers.
    """
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    strategy_info = ""
    if strategy:
        strategy_info = f"""
        Competencia:
        {json.dumps(strategy.get('competitor_insights', []), ensure_ascii=False)}

        Keywords de oportunidad:
        {', '.join(strategy.get('keywords_opportunities', []))}
        """

    prompt = f"""
    Genera 3 propuestas diferentes de estructuras para un artículo SEO con la keyword "{keyword}".
    Devuélvelas en formato JSON con esta forma:
    [
      {{"id": 1, "name": "Nombre de la estructura", "headers": ["h2 uno", "h2 dos", "h2 tres"]}},
      ...
    ]
    No uses markdown ni explicaciones, solo JSON puro.
    Considera esta información de estrategia: {strategy_info}
    """

    resp = client.chat.completions.create(
        model=ai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=600
    )
    raw = resp.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except Exception:
        return [
            {"id": 1, "name": "Fallback Educativa", "headers": [f"¿Qué es {keyword}?", f"Beneficios de {keyword}", f"Conclusión sobre {keyword}"]},
            {"id": 2, "name": "Fallback Comercial", "headers": [f"El problema con {keyword}", "Nuestra solución", "Llamada a la acción"]},
            {"id": 3, "name": "Fallback Comparativa", "headers": [f"{keyword} vs alternativas", f"Ventajas de {keyword}", "Conclusión final"]}
        ]


def generate_content_with_openai_html(title: str, keyword: str, structure: Dict[str, Any],
                                      tone: str, word_count: int, related_keywords: str,
                                      competitor_data: Dict[str, Any], strategy: Dict = None) -> str:
    """
    Genera contenido en HTML semántico (<h1>, <h2>, <p>) en lugar de Markdown.
    """
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    ai_model = st.session_state.inputs.get("ai_model", "gpt-4o-mini")
    temperature = st.session_state.inputs.get("temperature", 0.6)
    max_tokens = st.session_state.inputs.get("max_tokens", 2000)

    headers = json.dumps(structure["headers"], ensure_ascii=False)

    strategy_prompt = ""
    if strategy:
        strategy_prompt = f"""
        Insights de competencia:
        {json.dumps(strategy.get('competitor_insights', []), ensure_ascii=False)}

        Oportunidades de keywords:
        {', '.join(strategy.get('keywords_opportunities', []))}
        """

    prompt = f"""
    Escribe un artículo en HTML titulado "{title}" optimizado para la keyword "{keyword}".
    Sigue exactamente estos encabezados: {headers}.
    Usa etiquetas HTML semánticas (<h1>, <h2>, <h3>, <p>, <ul>, <li>).
    Tono: {tone}. Longitud objetivo: ~{word_count} palabras.
    Incluye naturalmente estas palabras relacionadas: {related_keywords}.
    {strategy_prompt}

    Requisitos:
    - No uses Markdown, solo HTML válido.
    - Incluye <h1> para el título principal y <h2>/<h3> para subsecciones.
    - Usa párrafos claros, listas si aplican y ejemplos locales (Perú).
    """

    resp = client.chat.completions.create(
        model=ai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )

    return resp.choices[0].message.content.strip()


# =====================
# Paso 3: Estructura
# =====================
if st.session_state.step == 3:
    st.subheader("Paso 3: Seleccionar Estructura")

    with st.spinner("Generando propuestas de estructuras..."):
        options = propose_structures(
            st.session_state.keyword,
            st.session_state.content_strategy,
            st.session_state.inputs.get("ai_model", "gpt-4o-mini")
        )

    sel = st.radio(
        "Elige una estructura",
        options=[o["id"] for o in options],
        format_func=lambda oid: next(o["name"] for o in options if o["id"] == oid)
    )
    chosen = next(o for o in options if o["id"] == sel)

    with st.expander("👀 Ver encabezados", expanded=True):
        for h in chosen["headers"]:
            st.write(f"• {h}")

    if st.button("✍️ Generar contenido final", type="primary"):
        st.session_state.selected_structure = chosen
        st.session_state.step = 4
        st.session_state.final_html = ""
        st.rerun()


# =====================
# Paso 4: Redacción
# =====================
elif st.session_state.step == 4:
    st.subheader("📝 Contenido Generado (HTML)")

    if not st.session_state.final_html:
        with st.spinner("Redactando en HTML con OpenAI..."):
            try:
                st.session_state.final_html = generate_content_with_openai_html(
                    title=st.session_state.inputs["title"],
                    keyword=st.session_state.keyword,
                    structure=st.session_state.selected_structure,
                    tone=st.session_state.inputs["tone"],
                    word_count=st.session_state.inputs["wordCount"],
                    related_keywords=st.session_state.inputs["relatedKeywords"],
                    competitor_data=st.session_state.competitor_data or {},
                    strategy=st.session_state.content_strategy
                )
            except Exception as e:
                st.error(f"Error generando contenido: {e}")

    tab1, tab2 = st.tabs(["👀 Vista Previa", "💻 Código HTML"])

    with tab1:
        st.markdown(st.session_state.final_html, unsafe_allow_html=True)

    with tab2:
        st.code(st.session_state.final_html, language="html")
