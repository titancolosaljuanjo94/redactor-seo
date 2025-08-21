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
# Límite de resultados a mostrar en la vista tipo SERP
SERP_RESULTS_LIMIT = 5


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
# FUNCIONES DE NAVEGACIÓN (AGREGAR AQUÍ)
# =====================

def render_simple_navigation():
    """Renderiza indicador de progreso visual"""
    st.markdown("### 📍 Progreso del Proyecto")
    
    cols = st.columns(4)
    steps = [
        {"name": "Research", "icon": "🔎"},
        {"name": "Inputs", "icon": "📝"}, 
        {"name": "Estructura", "icon": "🏗️"},
        {"name": "Redacción", "icon": "✍️"}
    ]
    
    current_step = st.session_state.step
    
    for i, col in enumerate(cols, start=1):
        with col:
            step = steps[i-1]
            if i < current_step:
                st.success(f"✅ {step['icon']} {step['name']}")
            elif i == current_step:
                st.info(f"🔄 {step['icon']} {step['name']}")
            else:
                st.write(f"⏳ {step['icon']} {step['name']}")

def render_navigation_buttons():
    """Renderiza botones anterior/siguiente"""
    current_step = st.session_state.step
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_step > 1:
            if st.button("⬅️ Anterior", type="secondary", use_container_width=True):
                st.session_state.step = current_step - 1
                st.rerun()
        else:
            st.button("⬅️ Anterior", disabled=True, use_container_width=True)
    
    with col2:
        step_names = ["Research", "Inputs", "Estructura", "Redacción"]
        st.markdown(f"<div style='text-align: center;'><strong>Paso {current_step} de 4: {step_names[current_step-1]}</strong></div>", 
                   unsafe_allow_html=True)
    
    with col3:
        can_advance, reason = can_advance_to_next_step()
        
        if current_step < 4 and can_advance:
            if st.button("Siguiente ➡️", type="primary", use_container_width=True):
                st.session_state.step = current_step + 1
                st.rerun()
        elif current_step < 4:
            st.button("Siguiente ➡️", disabled=True, use_container_width=True, help=reason)

def can_advance_to_next_step() -> tuple[bool, str]:
    """Verifica si se puede avanzar"""
    current_step = st.session_state.step
    
    if current_step == 1:
        return bool(st.session_state.get("competitor_data")), "Completa el análisis de competencia primero"
    elif current_step == 2:
        return bool(st.session_state.inputs.get("title", "").strip()), "Ingresa un título para continuar"
    elif current_step == 3:
        return bool(st.session_state.get("selected_structure")), "Selecciona una estructura para continuar"
    
    return True, ""

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

# =====================
# DataForSEO helpers
# =====================
def _dfs_auth_header():
    """Cabecera Authorization: Basic user:password (base64)."""
    import base64
    token = base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()
    return {"Authorization": "Basic " + token}

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
    headers = _dfs_auth_header()
    headers["Content-Type"] = "application/json"

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    j = r.json()
    return j["tasks"][0]["id"]

def dataforseo_get_results(task_id: str, max_wait_sec: int = 90) -> Dict[str, Any]:
    """
    Espera a que la tarea esté lista usando tasks_ready y luego llama a task_get/{task_id}.
    Tolera 404 temporales mientras la tarea se materializa.
    """
    start = time.time()
    headers = _dfs_auth_header()

    # 1) Esperar a que la tarea aparezca en tasks_ready
    ready_url = "https://api.dataforseo.com/v3/serp/google/organic/tasks_ready"
    while True:
        r = requests.get(ready_url, headers=headers, timeout=60)
        r.raise_for_status()
        jr = r.json()

        if any(t.get("id") == task_id for t in jr.get("tasks", [])):
            break
        if time.time() - start > max_wait_sec:
            # Si no apareció en ready, continuamos igual con task_get.
            break
        time.sleep(2)

    # 2) Obtener resultados con task_get/{id}, tolerando 404 temporal
    get_url = f"https://api.dataforseo.com/v3/serp/google/organic/task_get/{task_id}"
    while True:
        r = requests.get(get_url, headers=headers, timeout=60)
        if r.status_code == 404:
            if time.time() - start > max_wait_sec:
                return {"raw": {"note": "timeout waiting for task_get"}, "items": []}
            time.sleep(2)
            continue

        r.raise_for_status()
        j = r.json()
        try:
            items = j["tasks"][0]["result"][0]["items"]
        except Exception:
            items = []
        return {"raw": j, "items": items}

# =====================
# SERP helpers (render bonito y LIVE fallback)
# =====================
def build_serp_items(items, max_items=10):
    """Devuelve filas {pos, title, url} priorizando orgánicos; si no hay, usa cualquier ítem con URL."""
    if not items:
        return []
    organic = [it for it in items if it.get("type") == "organic" and it.get("url")]
    fallback = [it for it in items if it.get("url")]
    picked = organic or fallback
    picked = sorted(
        picked,
        key=lambda it: it.get("rank_group") or it.get("rank_absolute") or 9999
    )[:max_items]
    rows = []
    for it in picked:
        rows.append({
            "pos": it.get("rank_group") or it.get("rank_absolute") or "",
            "title": it.get("title") or it.get("url"),
            "url": it.get("url")
        })
    return rows

def render_serp_cards(rows, header="Vista general del SERP"):
    """Dibuja tarjetas estilo SERP (posición, título, URL en verde)."""
    if not rows:
        return
    if not st.session_state.get("serp_css_done"):
        st.markdown("""
<style>
.serp-card{border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;margin:10px 0;}
.serp-pos{display:inline-block;width:28px;height:28px;border:2px solid #ef4444;border-radius:6px;
          font-weight:700;text-align:center;line-height:24px;margin-right:10px;color:#ef4444;}
.serp-title a{font-size:16px;text-decoration:none;color:#1a73e8;}
.serp-url{color:#1f8b24;font-size:13px;margin-top:4px;word-break:break-all;}
</style>
        """, unsafe_allow_html=True)
        st.session_state.serp_css_done = True

    st.write(f"**{header}**")
    for r in rows:
        st.markdown(f"""
<div class="serp-card">
  <div>
    <span class="serp-pos">{r['pos']}</span>
    <span class="serp-title"><a href="{r['url']}" target="_blank">{r['title']}</a></span>
  </div>
  <div class="serp-url">{r['url']}</div>
</div>
        """, unsafe_allow_html=True)

def dataforseo_serp_live(keyword: str, location_name: str = "Peru", device: str = "desktop", depth: int = 20):
    """
    Fallback a endpoint LIVE (sin polling): /v3/serp/google/organic/live/advanced
    Devuelve items inmediatamente.
    """
    url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
    payload = [{
        "keyword": keyword,
        "language_code": "es",
        "location_name": location_name,
        "device": device,
        "depth": depth
    }]
    headers = _dfs_auth_header()
    headers["Content-Type"] = "application/json"
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=90)
    r.raise_for_status()
    j = r.json()
    try:
        return j["tasks"][0]["result"][0]["items"], j
    except Exception:
        return [], j

# =====================
# Análisis de competidores
# =====================
def analyze_competitors(keyword: str) -> Dict[str, Any]:
    """
    Analiza competencia con DataForSEO.
    Devuelve: competitors (top3), insights, top_organic (primer orgánico real),
    first_org_rank (posición orgánica mínima), serp_list y serp_raw.
    """
    # ---- Demo si no hay credenciales ----
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        demo_comp = [
            {"url": "https://competitor1.com", "title": f"Guía completa de {keyword}", "wordCount": 2500, "headers": 8},
            {"url": "https://competitor2.com", "title": f"Todo sobre {keyword}", "wordCount": 1800, "headers": 6},
            {"url": "https://competitor3.com", "title": f"{keyword}: Manual definitivo", "wordCount": 3200, "headers": 12},
        ]
        serp_list = [{"pos": i+1, "title": c["title"], "url": c["url"]} for i, c in enumerate(demo_comp)]
        return {
            "competitors": demo_comp,
            "insights": [
                "Promedio de palabras: 2,500",
                "Headers promedio: 8-12",
                "Enfoque principal: Guías completas",
                "Tono dominante: Profesional-educativo",
            ],
            "top_organic": [demo_comp[0]],
            "first_org_rank": 1,
            "serp_list": serp_list,
            "serp_raw": {},
        }

    # ---- Asíncrono con polling ----
    task_id = dataforseo_create_task(keyword=keyword, location_name="Peru", device="desktop", depth=20)
    res_async = dataforseo_get_results(task_id, max_wait_sec=90)
    items = res_async.get("items") or []

    # ---- Fallback a LIVE si no obtuvimos nada útil ----
    live_json = None
    if not items:
        items, live_json = dataforseo_serp_live(keyword=keyword, location_name="Peru", device="desktop", depth=20)

    # Preferimos orgánicos para el top3
    organic = [it for it in items if it.get("type") == "organic" and it.get("url")]
    any_with_url = [it for it in items if it.get("url")]

    picked = organic[:3] if organic else any_with_url[:3]
    competitors = [{
        "url": it["url"],
        "title": it.get("title") or it["url"],
        "wordCount": 2000,  # placeholders
        "headers": 8
    } for it in picked]

    # Primer resultado orgánico real (aunque no sea rank 1 por SGE/IA)
    first_org_rank = None
    if organic:
        ranks = [it.get("rank_group") for it in organic if isinstance(it.get("rank_group"), int)]
        first_org_rank = min(ranks) if ranks else None
    top_organic = []
    if first_org_rank is not None:
        top_organic = [{
            "url": it["url"],
            "title": it.get("title") or it["url"],
            "rank": it.get("rank_group")
        } for it in organic if it.get("rank_group") == first_org_rank]

    serp_list = build_serp_items(items, max_items=SERP_RESULTS_LIMIT)

    insights = [
        f"Total items leídos: {len(items)}",
        f"Orgánicos detectados: {len(organic)}",
        "Enfoque principal (aprox.): Guías informativas",
        "Tono dominante (aprox.): Profesional",
    ]
    # guardamos el JSON crudo que tengamos (async o live) para debug
    serp_raw = res_async.get("raw") if res_async.get("raw") else (live_json or {})
    return {
        "competitors": competitors,
        "insights": insights,
        "top_organic": top_organic,           # lista de primeros orgánicos
        "first_org_rank": first_org_rank,     # su posición real
        "serp_list": serp_list,
        "serp_raw": serp_raw
    }

# =====================
# FUNCIONES DE PRUEBA DATAFORSEO (AGREGAR AQUÍ - LÍNEA ~360-370)
# =====================

def test_dataforseo_content_analysis():
    """
    Prueba si DataForSEO Content Analysis está disponible en tu plan
    """
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        return {"error": "No hay credenciales DataForSEO configuradas"}
    
    # URL de prueba
    test_url = "https://www.example.com"
    
    headers = _dfs_auth_header()
    headers["Content-Type"] = "application/json"
    
    # Test 1: Verificar endpoints disponibles
    st.write("🔍 **Verificando endpoints DataForSEO disponibles...**")
    
    try:
        # Intentar obtener lista de tareas ready
        ready_url = "https://api.dataforseo.com/v3/on_page/content_parsing/tasks_ready"
        response = requests.get(ready_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            st.success("✅ Content Parsing API está disponible")
            data = response.json()
            st.write(f"Status code: {data.get('status_code')}")
            st.write(f"Status message: {data.get('status_message')}")
        elif response.status_code == 401:
            st.error("❌ Error de autenticación - verifica tus credenciales")
            return {"error": "Authentication failed"}
        elif response.status_code == 402:
            st.error("❌ Content Parsing no está incluido en tu plan DataForSEO")
            return {"error": "Content Parsing not available in plan"}
        else:
            st.warning(f"⚠️ Response inesperado: {response.status_code}")
            
    except Exception as e:
        st.error(f"❌ Error conectando con DataForSEO: {str(e)}")
        return {"error": str(e)}
    
    # Test 2: Intentar crear una tarea de prueba
    st.write("🧪 **Probando crear tarea de Content Analysis...**")
    
    try:
        task_url = "https://api.dataforseo.com/v3/on_page/content_parsing/task_post"
        
        task_data = [{
            "url": test_url,
            "enable_content_parsing": True,
            "enable_javascript": False
        }]
        
        response = requests.post(
            task_url,
            headers=headers,
            data=json.dumps(task_data),
            timeout=30
        )
        
        st.write(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            st.success("✅ Tarea creada exitosamente")
            
            # Mostrar información detallada
            st.json(result)
            
            if result.get("tasks") and len(result["tasks"]) > 0:
                task = result["tasks"][0]
                task_id = task.get("id")
                task_status = task.get("status_code")
                task_message = task.get("status_message")
                
                st.write(f"**Task ID:** {task_id}")
                st.write(f"**Status:** {task_status} - {task_message}")
                
                if task_status == 20000:
                    st.success("🎉 ¡Content Analysis funciona perfectamente!")
                    return {
                        "success": True,
                        "task_id": task_id,
                        "message": "Content Analysis disponible"
                    }
                else:
                    st.warning(f"Task creado pero con status: {task_status}")
                    
        elif response.status_code == 402:
            st.error("❌ Content Analysis no está en tu plan DataForSEO")
            st.info("💡 Alternativas disponibles:")
            st.write("- Usar solo SERP API (lo que ya tienes)")
            st.write("- Upgrade de plan DataForSEO")
            st.write("- Usar scraping básico como fallback")
            
        else:
            st.error(f"❌ Error creando tarea: {response.status_code}")
            try:
                error_data = response.json()
                st.json(error_data)
            except:
                st.write(response.text)
                
    except Exception as e:
        st.error(f"❌ Error en prueba: {str(e)}")
        return {"error": str(e)}
    
    return {"test_completed": True}

def test_dataforseo_basic_serp():
    """
    Prueba las funcionalidades SERP que ya sabes que funcionan
    """
    st.write("🔍 **Verificando SERP API (que ya usas)...**")
    
    try:
        # Probar con una keyword simple
        test_keyword = "seo"
        task_id = dataforseo_create_task(test_keyword, location_name="Peru", device="desktop", depth=10)
        
        if task_id:
            st.success(f"✅ SERP task creado: {task_id}")
            st.write("Tu SERP API funciona correctamente")
            return {"serp_works": True}
        else:
            st.error("❌ No se pudo crear SERP task")
            
    except Exception as e:
        st.error(f"❌ Error en SERP test: {str(e)}")
        return {"error": str(e)}

# =====================
# OpenAI helper (AQUÍ CONTINÚA TU CÓDIGO ORIGINAL)
# =====================
def generate_content_with_openai(title: str, keyword: str, structure: Dict[str, Any], tone: str, word_count: int, related_keywords: str, competitor_data: Dict[str, Any]) -> str:
# =====================
    """
    Redacta con OpenAI. Si no hay clave, devuelve contenido demo (paridad con React).
    """
    if not OPENAI_API_KEY:
        headers_list = "\n".join([f"### {h}" for h in structure["headers"]])
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

    competitors_txt = "\n".join([f"- {c.get('title')} ({c.get('url')})" for c in (competitor_data or {}).get("competitors", [])])
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
# Progress con navegación
# =====================
with st.container():
    render_simple_navigation()
    
st.divider()

with st.container():
    render_navigation_buttons()
    
# show_quick_navigation()  # Comentado temporalmente
st.divider()

# =====================
# Paso 1: Research
# =====================
if st.session_state.step == 1:
    st.subheader("Paso 1: Research de Competencia")
if st.session_state.step == 1:
    st.subheader("Paso 1: Research de Competencia")
    
    # SECCIÓN DE PRUEBA (TEMPORAL)
    with st.expander("🧪 Probar APIs DataForSEO"):
        st.write("Verifica qué funcionalidades están disponibles en tu plan:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Probar Content Analysis"):
                with st.spinner("Probando Content Analysis..."):
                    result = test_dataforseo_content_analysis()
        
        with col2:
            if st.button("📊 Probar SERP API"):
                with st.spinner("Probando SERP API..."):
                    result = test_dataforseo_basic_serp()
    
    st.divider()
    
    # Aquí continúa tu código normal...
    kw = st.text_input("Keyword objetivo", value=st.session_state.keyword,
                       placeholder="ej: cómo verificar identidad en Perú")
    go = st.button("🔎 Analizar competencia", type="primary", disabled=not kw.strip())

    if go:
        st.session_state.keyword = kw.strip()
        with st.spinner("Analizando competencia (DataForSEO)…"):
            try:
                st.session_state.competitor_data = analyze_competitors(st.session_state.keyword)
            except Exception as e:
                st.error(f"Error al analizar competencia: {e}")

    if st.session_state.competitor_data:
        st.success(f"¡Perfecto! Encontré competidores para \"{st.session_state.keyword}\"")

        colA, colB = st.columns(2)
        with colA:
            st.write("**Top 3 Competidores:**")
            for c in st.session_state.competitor_data["competitors"]:
                st.markdown(f"- [{c['title']}]({c['url']}) — {c['url']}")

        with colB:
            st.write("**Insights clave:**")
            for i in st.session_state.competitor_data["insights"]:
                st.write(f"- {i}")

        # Vista tipo SERP (posición + título + URL)
        serp_rows = st.session_state.competitor_data.get("serp_list") or []
        if serp_rows:
            render_serp_cards(serp_rows, header="Vista general del SERP (DataForSEO)")

        # Mensaje de primer resultado orgánico real
        first_rank = st.session_state.competitor_data.get("first_org_rank")
        top_org = st.session_state.competitor_data.get("top_organic") or []
        if first_rank and top_org:
            enlaces = ", ".join([f"[{c['title']}]({c['url']})" for c in top_org])
            st.info(f"**Primer resultado orgánico** (posición {first_rank}) para esta keyword según DataForSEO: {enlaces}")
        else:
            st.warning("No se detectó un resultado orgánico en las primeras posiciones (posibles features del SERP como IA/SGE, maps, etc.).")

        # (Opcional) Ver la respuesta bruta para depurar
        with st.expander("Ver respuesta bruta de DataForSEO"):
            st.json(st.session_state.competitor_data.get("serp_raw"))

        # Botón para avanzar
        if st.button("➡️ Continuar al Paso 2", type="primary"):
            st.session_state.step = 2
            st.rerun()

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
