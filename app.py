import os, time, json
import requests
import streamlit as st
from typing import Dict, Any, List

# =====================
# Configuración básica
# =====================
st.set_page_config(page_title="SEO Agent - Kmalo", page_icon="🔎", layout="wide")
st.title("SEO Agent - Kmalo")
st.caption("Tu asistente para crear contenido SEO optimizado (Streamlit + DataForSEO + OpenAI)")

# =====================
# Secrets / Env
# =====================
DATAFORSEO_LOGIN = st.secrets.get("DATAFORSEO_LOGIN", os.getenv("DATAFORSEO_LOGIN", ""))
DATAFORSEO_PASSWORD = st.secrets.get("DATAFORSEO_PASSWORD", os.getenv("DATAFORSEO_PASSWORD", ""))
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))

# =====================
# Estado (equivalente a useState)
# =====================
if "step" not in st.session_state: st.session_state.step = 1
if "keyword" not in st.session_state: st.session_state.keyword = ""
if "competitor_data" not in st.session_state: st.session_state.competitor_data = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {
        "relatedKeywords": "",
        "title": "",
        "tone": "profesional",
        "wordCount": 1500,  # número
    }
if "selected_structure" not in st.session_state: st.session_state.selected_structure = None
if "final_md" not in st.session_state: st.session_state.final_md = ""

# =====================
# Utilidades (paridad con tu React)
# =====================
def get_structure_options(kw: str) -> List[Dict[str, Any]]:
    return [
        {
            "id": 1,
            "name": "Estructura Educativa",
            "headers": [
                f"Introducción: ¿Qué es {kw}?",
                f"Por qué es importante {kw}",
                "Guía paso a paso",
                "Errores comunes a evitar",
                "Herramientas recomendadas",
                "Casos de éxito",
                "Conclusión y próximos pasos",
            ],
        },
        {
            "id": 2,
            "name": "Estructura Comercial",
            "headers": [
                f"El problema con {kw}",
                "La solución definitiva",
                "Beneficios comprobados",
                "Cómo empezar hoy mismo",
                "Preguntas frecuentes",
                "Testimonios y casos",
                "Llamada a la acción",
            ],
        },
        {
            "id": 3,
            "name": "Estructura Comparativa",
            "headers": [
                f"Introducción a {kw}",
                "Método tradicional vs método moderno",
                "Ventajas y desventajas",
                "Cuál elegir según tu situación",
                "Implementación práctica",
                "Resultados esperados",
                "Recomendación final",
            ],
        },
    ]

# ---- DataForSEO helpers ----
def dataforseo_create_task(keyword: str, location_name: str = "Peru", device: str = "desktop", depth: int = 20) -> str:
    """
    Crea una tarea SERP en DataForSEO y devuelve task_id.
    """
    url = "https://api.dataforseo.com/v3/serp/google/organic/task_post"
    payload = [{
        "keyword": keyword,
        "language_code": "es",
        "location_name": location_name,
        "device": device,
        "depth": depth
    }]
    headers = {"Content-Type": "application/json",
               "Authorization": "Basic " + (os.environ.get("DFS_AUTH") or "")}
    # Si no hay DFS_AUTH precomputado, lo generamos on the fly con login:password
    if not os.environ.get("DFS_AUTH") and DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD:
        import base64
        headers["Authorization"] = "Basic " + base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    j = r.json()
    return j["tasks"][0]["id"]

def dataforseo_get_results(task_id: str, max_wait_sec: int = 25) -> Dict[str, Any]:
    """
    Polling simple hasta obtener resultados del task_id.
    """
    get_url = f"https://api.dataforseo.com/v3/serp/google/organic/task_get/{task_id}"
    start = time.time()
    headers = {"Authorization": "Basic " + (os.environ.get("DFS_AUTH") or "")}
    if not os.environ.get("DFS_AUTH") and DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD:
        import base64
        headers["Authorization"] = "Basic " + base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()

    while True:
        r = requests.get(get_url, headers=headers, timeout=60)
        r.raise_for_status()
        j = r.json()
        try:
            items = j["tasks"][0]["result"][0]["items"]
            return {"raw": j, "items": items}
        except Exception:
            if time.time() - start > max_wait_sec:
                return {"raw": j, "items": []}
            time.sleep(2)

def analyze_competitors(keyword: str) -> Dict[str, Any]:
    """
    Analiza competencia con DataForSEO.
    Si no hay credenciales, devuelve datos simulados (como tu React).
    """
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        return {
            "competitors": [
                {"url": "competitor1.com", "title": f"Guía completa de {keyword}", "wordCount": 2500, "headers": 8},
                {"url": "competitor2.com", "title": f"Todo sobre {keyword}", "wordCount": 1800, "headers": 6},
                {"url": "competitor3.com", "title": f"{keyword}: Manual definitivo", "wordCount": 3200, "headers": 12},
            ],
            "insights": [
                "Promedio de palabras: 2,500",
                "Headers promedio: 8-12",
                "Enfoque principal: Guías completas",
                "Tono dominante: Profesional-educativo",
            ],
            "serp_raw": {},
        }

    task_id = dataforseo_create_task(keyword=keyword, location_name="Peru", device="desktop", depth=20)
    res = dataforseo_get_results(task_id)

    competitors = []
    for it in res["items"]:
        if it.get("type") == "organic":
            competitors.append({
                "url": it.get("url"),
                "title": it.get("title"),
                "wordCount": 2000,  # placeholder (DataForSEO no da wordcount)
                "headers": 8
            })
            if len(competitors) >= 3:
                break

    insights = [
        f"Total orgánicos leídos: {len(res['items'])}",
        "Enfoque principal (aprox.): Guías informativas",
        "Tono dominante (aprox.): Profesional",
    ]
    return {"competitors": competitors, "insights": insights, "serp_raw": res["raw"]}

# ---- OpenAI helper ----
def generate_content_with_openai(title: str, keyword: str, structure: Dict[str, Any], tone: str, word_count: int, related_keywords: str, competitor_data: Dict[str, Any]) -> str:
    """
    Redacta con OpenAI. Si no hay clave, devuelve contenido demo (paridad con React).
    """
    if not OPENAI_API_KEY:
        headers_list = "\\n".join([f"### {h}" for h in structure["headers"]])
        return f"""# {title}

## Introducción
Este artículo completo sobre "{keyword}" ha sido desarrollado específicamente para el mercado peruano, considerando las necesidades locales y tendencias actuales.

{headers_list}

**Palabras relacionadas**: {related_keywords}
**Tono**: {tone} — **Extensión objetivo**: {word_count} palabras

## Optimización SEO
- Keyword principal integrada naturalmente
- Headers optimizados para featured snippets
- Estructura pensada para engagement
- Call-to-actions estratégicamente ubicados
"""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    competitors_txt = "\\n".join([f"- {c.get('title')} ({c.get('url')})" for c in (competitor_data or {}).get("competitors", [])])
    system = "Eres un redactor SEO senior para el mercado peruano. Redacta en español claro, escaneable, con H2/H3."
    prompt = f"""
Genera un artículo **en Markdown** titulado "{title}" para la keyword principal "{keyword}".
Sigue exactamente estos encabezados:
{json.dumps(structure["headers"], ensure_ascii=False, indent=2)}

Tono: {tone}. Extensión objetivo: ~{word_count} palabras.
Incluye naturalmente estas palabras relacionadas: {related_keywords}.

Referencias competitivas (solo orientación, no copies):
{competitors_txt}

Requisitos:
- H2/H3 bien jerarquizados
- Introducción breve y útil
- Secciones con ejemplos locales (Perú) cuando aplique
- Conclusión con próximos pasos y CTA
- No inventes datos sensibles; si no hay certeza, explica alternativas.
""".strip()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,
    )
    return resp.choices[0].message.content

def download_md_button(filename: str, content: str):
    st.download_button(
        "⬇️ Descargar contenido (.md)",
        data=content.encode("utf-8"),
        file_name=filename,
        mime="text/markdown"
    )

# =====================
# Progress (paridad con barra de pasos)
# =====================
with st.container():
    cols = st.columns(4)
    labels = ["Research", "Inputs", "Estructura", "Redacción"]
    for i, c in enumerate(cols, start=1):
        with c:
            filled = (st.session_state.step >= i)
            st.metric(label=labels[i-1], value=("✅" if filled else "—"))

st.divider()

# =====================
# Paso 1: Research
# =====================
if st.session_state.step == 1:
    st.subheader("Paso 1: Research de Competencia")
    kw = st.text_input("Keyword objetivo", value=st.session_state.keyword, placeholder="ej: cómo verificar identidad en Perú")
    go = st.button("🔎 Analizar competencia", type="primary", disabled=not kw.strip())

    if go:
        st.session_state.keyword = kw.strip()
        with st.spinner("Analizando competencia (DataForSEO)…"):
            try:
                st.session_state.competitor_data = analyze_competitors(st.session_state.keyword)
                st.session_state.step = 2
                st.rerun()
            except Exception as e:
                st.error(f"Error al analizar competencia: {e}")

    if st.session_state.competitor_data:
        st.success(f"¡Perfecto! Encontré competidores para \"{st.session_state.keyword}\"")
        colA, colB = st.columns(2)
        with colA:
            st.write("**Top 3 Competidores:**")
            for c in st.session_state.competitor_data["competitors"]:
                st.write(f"- {c['url']} — {c['title']}")
        with colB:
            st.write("**Insights clave:**")
            for i in st.session_state.competitor_data["insights"]:
                st.write(f"- {i}")

# =====================
# Paso 2: Inputs
# =====================
elif st.session_state.step == 2:
    st.subheader("Paso 2: Definir Parámetros del Contenido")
    with st.form("inputs_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.inputs["relatedKeywords"] = st.text_area(
                "Keywords relacionadas (coma separadas)",
                value=st.session_state.inputs["relatedKeywords"],
                placeholder="ej: verificar DNI, estafas online, seguridad digital",
                height=90
            )
            st.session_state.inputs["title"] = st.text_input(
                "Título del artículo",
                value=st.session_state.inputs["title"],
                placeholder="Guía Completa: Cómo Verificar Identidad en Perú 2025"
            )
        with c2:
            st.session_state.inputs["tone"] = st.selectbox(
                "Tono del contenido",
                ["profesional", "casual", "tecnico", "educativo"],
                index=["profesional", "casual", "tecnico", "educativo"].index(st.session_state.inputs["tone"])
            )
            st.session_state.inputs["wordCount"] = st.selectbox(
                "Cantidad de palabras",
                [800, 1500, 2500, 3500],
                index=[800, 1500, 2500, 3500].index(st.session_state.inputs["wordCount"])
            )
        submitted = st.form_submit_button("📑 Generar estructuras")
        if submitted:
            if not st.session_state.inputs["title"].strip():
                st.warning("Ingresa un título.")
            else:
                st.session_state.step = 3
                st.rerun()

# =====================
# Paso 3: Estructura
# =====================
elif st.session_state.step == 3:
    st.subheader("Paso 3: Seleccionar Estructura")
    options = get_structure_options(st.session_state.keyword)

    sel = st.radio(
        "Elige una estructura",
        options=[o["id"] for o in options],
        format_func=lambda oid: next(o["name"] for o in options if o["id"] == oid),
        horizontal=True
    )
    chosen = next(o for o in options if o["id"] == sel)
    with st.expander("Ver encabezados"):
        for i, h in enumerate(chosen["headers"], start=1):
            st.write(f"{i}. {h}")

    if st.button("✍️ Generar contenido", type="primary"):
        st.session_state.selected_structure = chosen
        st.session_state.step = 4
        st.session_state.final_md = ""
        st.rerun()

# =====================
# Paso 4: Redacción
# =====================
elif st.session_state.step == 4:
    st.subheader("Contenido Generado")
    if not st.session_state.final_md:
        with st.spinner("Redactando con OpenAI…"):
            try:
                st.session_state.final_md = generate_content_with_openai(
                    title=st.session_state.inputs["title"],
                    keyword=st.session_state.keyword,
                    structure=st.session_state.selected_structure,
                    tone=st.session_state.inputs["tone"],
                    word_count=st.session_state.inputs["wordCount"],
                    related_keywords=st.session_state.inputs["relatedKeywords"],
                    competitor_data=st.session_state.competitor_data or {}
                )
            except Exception as e:
                st.error(f"Error generando contenido: {e}")

    kw = st.session_state.keyword
    tone = st.session_state.inputs["tone"]
    wc = st.session_state.inputs["wordCount"]
    st.info(f"**Keyword:** {kw} | **Estructura:** {st.session_state.selected_structure['name']} | **Tono:** {tone} | **Palabras:** {wc}")

    st.markdown(st.session_state.final_md)

    col1, col2, col3 = st.columns(3)
    with col1:
        download_md_button(f"{kw or 'articulo'}.md", st.session_state.final_md)
    with col2:
        if st.button("🔄 Generar de nuevo"):
            st.session_state.final_md = ""
            st.rerun()
    with col3:
        if st.button("🆕 Empezar nuevo proyecto"):
            for k in ["step","keyword","competitor_data","inputs","selected_structure","final_md"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
