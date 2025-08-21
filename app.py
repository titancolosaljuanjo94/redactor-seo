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
if "content_strategy" not in st.session_state: st.session_state.content_strategy = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {
        "relatedKeywords": "",
        "title": "",
        "tone": "profesional",
        "wordCount": 1500,
    }
if "selected_structure" not in st.session_state: st.session_state.selected_structure = None
if "final_md" not in st.session_state: st.session_state.final_md = ""

# =====================
# FUNCIONES DE NAVEGACIÓN
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
    """Renderiza botones anterior/siguiente MEJORADOS"""
    current_step = st.session_state.step
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_step > 1:
            if st.button("⬅️ Anterior", type="secondary", use_container_width=True):
                st.session_state.step = current_step - 1
                st.rerun()
        else:
            st.write("")  # Espacio vacío
    
    with col2:
        step_names = ["Research", "Inputs", "Estructura", "Redacción"]
        st.markdown(f"<div style='text-align: center;'><strong>Paso {current_step} de 4: {step_names[current_step-1]}</strong></div>", 
                   unsafe_allow_html=True)
    
    with col3:
        can_advance, reason = can_advance_to_next_step()
        
        if current_step < 4:
            if can_advance:
                if st.button("Siguiente ➡️", type="primary", use_container_width=True):
                    st.session_state.step = current_step + 1
                    st.rerun()
            else:
                st.button("Siguiente ➡️", disabled=True, use_container_width=True, help=reason)
        else:
            st.write("")  # Espacio vacío en el último paso

def can_advance_to_next_step() -> tuple[bool, str]:
    """Verifica si se puede avanzar - CORREGIDO"""
    current_step = st.session_state.step
    
    if current_step == 1:
        # Verificamos que exista competitor_data Y que tenga datos válidos
        competitor_data = st.session_state.get("competitor_data")
        if not competitor_data:
            return False, "Completa el análisis de competencia primero"
        if not competitor_data.get("competitors"):
            return False, "No se encontraron competidores válidos"
        return True, ""
        
    elif current_step == 2:
        title = st.session_state.inputs.get("title", "").strip()
        if not title:
            return False, "Ingresa un título para continuar"
        return True, ""
        
    elif current_step == 3:
        if not st.session_state.get("selected_structure"):
            return False, "Selecciona una estructura para continuar"
        return True, ""
    
    return True, ""

# =====================
# Utilidades
# =====================
def get_structure_options(kw: str, strategy: Dict = None) -> List[Dict[str, Any]]:
    """Genera estructuras, opcionalmente optimizadas con strategy"""
    
    # Estructuras base
    base_structures = [
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
    
    # Si tenemos estrategia, agregamos estructura optimizada
    if strategy and strategy.get("suggested_headers"):
        optimized_structure = {
            "id": 4,
            "name": "🎯 Estructura Optimizada (Basada en Competencia)",
            "headers": strategy["suggested_headers"],
            "optimized": True
        }
        base_structures.append(optimized_structure)
    
    return base_structures

# =====================
# DataForSEO helpers
# =====================
def _dfs_auth_header():
    """Cabecera Authorization: Basic user:password (base64)."""
    import base64
    token = base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()
    return {"Authorization": "Basic " + token}

def dataforseo_create_task(keyword: str, location_name: str = "Peru", device: str = "desktop", depth: int = 20) -> str:
    """Crea una tarea SERP en DataForSEO y devuelve task_id."""
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
    """Espera a que la tarea esté lista y obtiene resultados."""
    start = time.time()
    headers = _dfs_auth_header()

    # Esperar a que la tarea aparezca en tasks_ready
    ready_url = "https://api.dataforseo.com/v3/serp/google/organic/tasks_ready"
    while True:
        r = requests.get(ready_url, headers=headers, timeout=60)
        r.raise_for_status()
        jr = r.json()

        if any(t.get("id") == task_id for t in jr.get("tasks", [])):
            break
        if time.time() - start > max_wait_sec:
            break
        time.sleep(2)

    # Obtener resultados
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

def dataforseo_serp_live(keyword: str, location_name: str = "Peru", device: str = "desktop", depth: int = 20):
    """Fallback a endpoint LIVE (sin polling)."""
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
# CONTENT ANALYSIS - NUEVO
# =====================
def analyze_competitor_content(url: str) -> Dict[str, Any]:
    """
    Analiza contenido real de una URL con DataForSEO Content Analysis
    """
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        # Fallback demo
        return {
            "url": url,
            "word_count": 2500,
            "headers": {
                "h1": 1,
                "h2": 12,
                "h3": 8,
                "total": 21
            },
            "title": "Título demo extraído",
            "meta_description": "Meta description demo",
            "keywords_density": {"keyword": 1.2, "related": 0.8},
            "status": "demo"
        }
    
    try:
        headers = _dfs_auth_header()
        headers["Content-Type"] = "application/json"
        
        # Crear tarea de content parsing
        task_url = "https://api.dataforseo.com/v3/on_page/content_parsing/task_post"
        task_data = [{
            "url": url,
            "enable_content_parsing": True,
            "enable_javascript": False,
            "custom_js": None
        }]
        
        response = requests.post(task_url, headers=headers, data=json.dumps(task_data), timeout=60)
        response.raise_for_status()
        
        task_result = response.json()
        if not task_result.get("tasks") or len(task_result["tasks"]) == 0:
            raise Exception("No se pudo crear la tarea de análisis")
            
        task_id = task_result["tasks"][0]["id"]
        
        # Esperar y obtener resultados
        time.sleep(5)  # Esperar procesamiento inicial
        
        get_url = f"https://api.dataforseo.com/v3/on_page/content_parsing/task_get/{task_id}"
        
        max_attempts = 18  # 3 minutos máximo
        for attempt in range(max_attempts):
            result_response = requests.get(get_url, headers=headers, timeout=60)
            result_response.raise_for_status()
            
            result_data = result_response.json()
            
            if result_data.get("tasks") and len(result_data["tasks"]) > 0:
                task = result_data["tasks"][0]
                
                if task.get("status_code") == 20000 and task.get("result"):
                    # Procesar resultados exitosos
                    result = task["result"][0]
                    
                    # Extraer métricas clave
                    content_parsing = result.get("content_parsing", {})
                    
                    return {
                        "url": url,
                        "word_count": content_parsing.get("word_count", 0),
                        "headers": {
                            "h1": content_parsing.get("h1_count", 0),
                            "h2": content_parsing.get("h2_count", 0),
                            "h3": content_parsing.get("h3_count", 0),
                            "total": (content_parsing.get("h1_count", 0) + 
                                     content_parsing.get("h2_count", 0) + 
                                     content_parsing.get("h3_count", 0))
                        },
                        "title": result.get("title", ""),
                        "meta_description": result.get("meta_description", ""),
                        "content_length": len(content_parsing.get("content", "")),
                        "images_count": content_parsing.get("images_count", 0),
                        "internal_links_count": content_parsing.get("internal_links_count", 0),
                        "external_links_count": content_parsing.get("external_links_count", 0),
                        "status": "success"
                    }
                elif task.get("status_code") == 40000:
                    # Tarea en progreso
                    time.sleep(10)
                    continue
                else:
                    # Error en la tarea
                    raise Exception(f"Error en análisis: {task.get('status_message', 'Unknown error')}")
            
            time.sleep(10)
        
        raise Exception("Timeout esperando resultados de análisis de contenido")
        
    except Exception as e:
        # Fallback con análisis básico en caso de error
        return {
            "url": url,
            "word_count": 2000,
            "headers": {"h1": 1, "h2": 10, "h3": 5, "total": 16},
            "title": f"Análisis fallback para {url}",
            "meta_description": "",
            "status": f"error: {str(e)}"
        }

def generate_content_strategy(competitor_analyses: List[Dict], keyword: str) -> Dict[str, Any]:
    """
    Genera estrategia de contenido basada en análisis de competidores
    """
    if not competitor_analyses:
        return {}
    
    # Análisis de métricas
    word_counts = [comp.get("word_count", 0) for comp in competitor_analyses if comp.get("word_count")]
    h2_counts = [comp.get("headers", {}).get("h2", 0) for comp in competitor_analyses]
    h3_counts = [comp.get("headers", {}).get("h3", 0) for comp in competitor_analyses]
    
    # Calcular recomendaciones
    avg_words = sum(word_counts) // len(word_counts) if word_counts else 2000
    min_words = min(word_counts) if word_counts else 1500
    max_words = max(word_counts) if word_counts else 2500
    
    avg_h2 = sum(h2_counts) // len(h2_counts) if h2_counts else 8
    avg_h3 = sum(h3_counts) // len(h3_counts) if h3_counts else 5
    
    # Generar headers sugeridos basados en patrones comunes
    suggested_headers = [
        f"¿Qué es {keyword}? Guía completa 2025",
        f"Beneficios principales de {keyword}",
        f"Cómo implementar {keyword} paso a paso",
        f"Errores comunes con {keyword} (y cómo evitarlos)",
        f"Mejores herramientas para {keyword}",
        f"{keyword} vs alternativas: comparación detallada",
        f"Casos de éxito reales con {keyword}",
        f"Preguntas frecuentes sobre {keyword}",
        f"Conclusión: el futuro de {keyword}",
    ]
    
    # Ajustar cantidad de headers basado en competencia
    target_headers = min(max(avg_h2 + 1, 8), 15)
    suggested_headers = suggested_headers[:target_headers]
    
    return {
        "recommended_word_count": {
            "min": max(min_words - 200, 800),
            "optimal": min(avg_words + 300, 4000),
            "max": max_words + 500
        },
        "recommended_headers": {
            "h2_count": avg_h2 + 1,
            "h3_count": avg_h3 + 2,
            "total": avg_h2 + avg_h3 + 3
        },
        "suggested_headers": suggested_headers,
        "competitor_insights": [
            f"Promedio de palabras en top 3: {avg_words:,}",
            f"Headers H2 promedio: {avg_h2}",
            f"Rango de extensión: {min_words:,} - {max_words:,} palabras",
            f"Tu oportunidad: crear contenido de {avg_words + 300:,} palabras con {avg_h2 + 1} secciones principales"
        ],
        "keywords_opportunities": [
            f"{keyword} en Perú",
            f"guía {keyword}",
            f"tutorial {keyword}",
            f"ejemplos {keyword}",
            f"{keyword} 2025"
        ]
    }

# =====================
# SERP helpers
# =====================
def build_serp_items(items, max_items=10):
    """Devuelve filas {pos, title, url} priorizando orgánicos."""
    if not items:
        return []
    organic = [it for it in items if it.get("type") == "organic" and it.get("url")]
    fallback = [it for it in items if it.get("url")]
    picked = organic or fallback
    picked = sorted(picked, key=lambda it: it.get("rank_group") or it.get("rank_absolute") or 9999)[:max_items]
    
    rows = []
    for it in picked:
        rows.append({
            "pos": it.get("rank_group") or it.get("rank_absolute") or "",
            "title": it.get("title") or it.get("url"),
            "url": it.get("url")
        })
    return rows

def render_serp_cards(rows, header="Vista general del SERP"):
    """Dibuja tarjetas estilo SERP."""
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

# =====================
# Análisis de competidores MEJORADO
# =====================
def analyze_competitors(keyword: str) -> Dict[str, Any]:
    """
    Analiza competencia con DataForSEO SERP + Content Analysis
    """
    # Demo si no hay credenciales
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        demo_comp = [
            {"url": "https://competitor1.com", "title": f"Guía completa de {keyword}", "wordCount": 2500, "headers": 8},
            {"url": "https://competitor2.com", "title": f"Todo sobre {keyword}", "wordCount": 1800, "headers": 6},
            {"url": "https://competitor3.com", "title": f"{keyword}: Manual definitivo", "wordCount": 3200, "headers": 12},
        ]
        serp_list = [{"pos": i+1, "title": c["title"], "url": c["url"]} for i, c in enumerate(demo_comp)]
        return {
            "competitors": demo_comp,
            "content_analyses": [],
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

    # Análisis SERP
    task_id = dataforseo_create_task(keyword=keyword, location_name="Peru", device="desktop", depth=20)
    res_async = dataforseo_get_results(task_id, max_wait_sec=90)
    items = res_async.get("items") or []

    # Fallback a LIVE si no obtuvimos nada útil
    live_json = None
    if not items:
        items, live_json = dataforseo_serp_live(keyword=keyword, location_name="Peru", device="desktop", depth=20)

    # Obtener top 3 orgánicos
    organic = [it for it in items if it.get("type") == "organic" and it.get("url")]
    any_with_url = [it for it in items if it.get("url")]
    picked = organic[:3] if organic else any_with_url[:3]
    
    competitors = []
    content_analyses = []
    
    # Analizar contenido de cada competidor
    for it in picked:
        url = it["url"]
        title = it.get("title") or url
        
        # Análisis básico para compatibilidad
        competitor = {
            "url": url,
            "title": title,
            "wordCount": 2000,  # placeholder inicial
            "headers": 8        # placeholder inicial
        }
        competitors.append(competitor)
        
        # Análisis de contenido real (si está disponible)
        try:
            content_analysis = analyze_competitor_content(url)
            content_analyses.append(content_analysis)
            
            # Actualizar datos del competidor con análisis real
            competitor["wordCount"] = content_analysis.get("word_count", 2000)
            competitor["headers"] = content_analysis.get("headers", {}).get("total", 8)
            competitor["real_title"] = content_analysis.get("title", title)
            competitor["analysis_status"] = content_analysis.get("status", "unknown")
            
        except Exception as e:
            st.warning(f"No se pudo analizar contenido de {url}: {str(e)}")
            content_analyses.append({
                "url": url,
                "status": f"error: {str(e)}",
                "word_count": 2000,
                "headers": {"total": 8}
            })

    # Resto del análisis SERP (igual que antes)
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

    # Insights mejorados con datos reales
    real_word_counts = [ca.get("word_count", 0) for ca in content_analyses if ca.get("word_count", 0) > 0]
    avg_words = sum(real_word_counts) // len(real_word_counts) if real_word_counts else 2000

    insights = [
        f"Total items leídos: {len(items)}",
        f"Orgánicos detectados: {len(organic)}",
        f"Análisis de contenido completados: {len([ca for ca in content_analyses if ca.get('status') != 'error'])}",
        f"Promedio de palabras (análisis real): {avg_words:,}" if real_word_counts else "Promedio de palabras: ~2,000 (estimado)",
        "Enfoque principal: Guías informativas",
    ]

    serp_raw = res_async.get("raw") if res_async.get("raw") else (live_json or {})
    
    return {
        "competitors": competitors,
        "content_analyses": content_analyses,
        "insights": insights,
        "top_organic": top_organic,
        "first_org_rank": first_org_rank,
        "serp_list": serp_list,
        "serp_raw": serp_raw
    }

# =====================
# OpenAI helper MEJORADO
# =====================
def generate_content_with_openai(title: str, keyword: str, structure: Dict[str, Any], tone: str, word_count: int, related_keywords: str, competitor_data: Dict[str, Any], strategy: Dict = None) -> str:
    """
    Redacta con OpenAI, opcionalmente usando strategy para mejorar el prompt
    """
    if not OPENAI_API_KEY:
        headers_list = "\n".join([f"### {h}" for h in structure["headers"]])
        strategy_info = ""
        if strategy:
            strategy_info = f"""
**Estrategia basada en competencia:**
- Extensión recomendada: {strategy.get('recommended_word_count', {}).get('optimal', word_count):,} palabras
- Headers sugeridos: {strategy.get('recommended_headers', {}).get('h2_count', 8)} secciones principales
- Oportunidades de keywords: {', '.join(strategy.get('keywords_opportunities', [])[:3])}
"""
        
        return f"""# {title}

## Introducción
Este artículo completo sobre "{keyword}" ha sido desarrollado específicamente para el mercado peruano, considerando las necesidades locales y tendencias actuales.

{headers_list}

**Palabras relacionadas**: {related_keywords}
**Tono**: {tone} — **Extensión objetivo**: {word_count} palabras

{strategy_info}

## Optimización SEO
- Keyword principal integrada naturalmente
- Headers optimizados para featured snippets
- Estructura pensada para engagement
- Call-to-actions estratégicamente ubicados
"""

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    competitors_txt = "\n".join([f"- {c.get('title')} ({c.get('url')}) - {c.get('wordCount', 0):,} palabras" for c in (competitor_data or {}).get("competitors", [])])
    
    # Información de estrategia para el prompt
    strategy_prompt = ""
    if strategy:
        insights = strategy.get("competitor_insights", [])
        opportunities = strategy.get("keywords_opportunities", [])
        strategy_prompt = f"""
ANÁLISIS DE COMPETENCIA:
{chr(10).join(insights)}

OPORTUNIDADES DE KEYWORDS: {', '.join(opportunities[:5])}
EXTENSIÓN OBJETIVO OPTIMIZADA: {strategy.get('recommended_word_count', {}).get('optimal', word_count):,} palabras
"""

    system = "Eres un redactor SEO senior para el mercado peruano. Redacta en español claro, escaneable, con H2/H3 bien estructurados. Usa datos y ejemplos específicos de Perú cuando sea posible."
    
    prompt = f"""
Genera un artículo **en Markdown** titulado "{title}" para la keyword principal "{keyword}".
Sigue exactamente estos encabezados:
{json.dumps(structure["headers"], ensure_ascii=False, indent=2)}

Tono: {tone}. Extensión objetivo: ~{word_count} palabras.
Incluye naturalmente estas palabras relacionadas: {related_keywords}.

{strategy_prompt}

Referencias competitivas (solo orientación, no copies):
{competitors_txt}

Requisitos:
- H2/H3 bien jerarquizados
- Introducción breve y útil
- Secciones con ejemplos locales (Perú) cuando aplique
- Conclusión con próximos pasos y CTA
- No inventes datos sensibles; si no hay certeza, explica alternativas
- Integra naturalmente las keywords de oportunidad identificadas
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
# UI Principal
# =====================
with st.container():
    render_simple_navigation()
    
st.divider()

with st.container():
    render_navigation_buttons()
    
st.divider()

# =====================
# Paso 1: Research MEJORADO
# =====================
if st.session_state.step == 1:
    st.subheader("Paso 1: Research de Competencia")
    
    kw = st.text_input("Keyword objetivo", value=st.session_state.keyword,
                       placeholder="ej: por qué estudiar enfermería")
    
    # Opción para análisis profundo
    deep_analysis = st.checkbox("🔬 Análisis profundo de contenido (usa Content Analysis API)", 
                               value=True, 
                               help="Analiza el contenido real de competidores para obtener métricas precisas")
    
    go = st.button("🔎 Analizar competencia", type="primary", disabled=not kw.strip())

    if go:
        st.session_state.keyword = kw.strip()
        with st.spinner("Analizando competencia y contenido (esto puede tomar 1-2 minutos)..."):
            try:
                st.session_state.competitor_data = analyze_competitors(st.session_state.keyword)
                
                # Generar estrategia si tenemos análisis de contenido
                if st.session_state.competitor_data.get("content_analyses"):
                    with st.spinner("Generando estrategia de contenido..."):
                        st.session_state.content_strategy = generate_content_strategy(
                            st.session_state.competitor_data["content_analyses"], 
                            st.session_state.keyword
                        )
                
            except Exception as e:
                st.error(f"Error al analizar competencia: {e}")

    # Mostrar resultados si existen
    if st.session_state.competitor_data:
        st.success(f"✅ Análisis completado para \"{st.session_state.keyword}\"")

        # Tabs para organizar información
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Competidores", "🎯 Estrategia", "📈 SERP", "🔧 Debug"])
        
        with tab1:
            st.subheader("Top 3 Competidores Analizados")
            for i, comp in enumerate(st.session_state.competitor_data["competitors"], 1):
                with st.expander(f"#{i} - {comp['title'][:60]}..."):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**URL:** {comp['url']}")
                        st.write(f"**Palabras:** {comp['wordCount']:,}")
                        st.write(f"**Headers:** {comp['headers']}")
                    with col2:
                        if comp.get("analysis_status"):
                            if comp["analysis_status"] == "success":
                                st.success("✅ Análisis completado")
                            else:
                                st.warning(f"⚠️ {comp['analysis_status']}")
                        if comp.get("real_title"):
                            st.write(f"**Título real:** {comp['real_title'][:80]}...")

        with tab2:
            if st.session_state.content_strategy:
                st.subheader("🎯 Estrategia Recomendada")
                
                # Métricas recomendadas
                col1, col2, col3 = st.columns(3)
                strategy = st.session_state.content_strategy
                
                with col1:
                    rec_words = strategy.get("recommended_word_count", {})
                    st.metric("Palabras Óptimas", f"{rec_words.get('optimal', 2000):,}", 
                             f"Rango: {rec_words.get('min', 1500):,}-{rec_words.get('max', 3000):,}")
                
                with col2:
                    rec_headers = strategy.get("recommended_headers", {})
                    st.metric("Headers H2", rec_headers.get('h2_count', 8), 
                             f"H3: {rec_headers.get('h3_count', 5)}")
                
                with col3:
                    insights = strategy.get("competitor_insights", [])
                    if insights:
                        st.metric("Competidores", "3", "analizados")

                # Insights
                st.subheader("💡 Insights Clave")
                for insight in strategy.get("competitor_insights", []):
                    st.write(f"• {insight}")
                
                # Oportunidades de keywords
                st.subheader("🔑 Oportunidades de Keywords")
                opportunities = strategy.get("keywords_opportunities", [])
                if opportunities:
                    st.write("Considera incluir estas variaciones:")
                    for opp in opportunities:
                        st.code(f"• {opp}")
                
                # Headers sugeridos
                st.subheader("📋 Estructura Sugerida")
                suggested = strategy.get("suggested_headers", [])
                if suggested:
                    st.write("Basada en análisis de competencia:")
                    for i, header in enumerate(suggested, 1):
                        st.write(f"{i}. {header}")
            else:
                st.info("Estrategia se generará automáticamente cuando el análisis de contenido esté disponible")

        with tab3:
            # Vista SERP (como antes)
            serp_rows = st.session_state.competitor_data.get("serp_list") or []
            if serp_rows:
                render_serp_cards(serp_rows, header="Vista general del SERP (DataForSEO)")

            # Primer resultado orgánico
            first_rank = st.session_state.competitor_data.get("first_org_rank")
            top_org = st.session_state.competitor_data.get("top_organic") or []
            if first_rank and top_org:
                enlaces = ", ".join([f"[{c['title']}]({c['url']})" for c in top_org])
                st.info(f"**Primer resultado orgánico** (posición {first_rank}): {enlaces}")
            else:
                st.warning("No se detectó resultado orgánico en primeras posiciones (posibles AI Overviews, SGE, etc.)")

        with tab4:
            # Información de debug
            st.subheader("🔧 Información de Debug")
            st.write("**Insights básicos:**")
            for insight in st.session_state.competitor_data["insights"]:
                st.write(f"• {insight}")
            
            # Análisis de contenido detallado
            content_analyses = st.session_state.competitor_data.get("content_analyses", [])
            if content_analyses:
                st.write("**Análisis de contenido detallado:**")
                for analysis in content_analyses:
                    with st.expander(f"Análisis: {analysis.get('url', 'Unknown')}"):
                        st.json(analysis)
            
            # Ver respuesta bruta SERP
            with st.expander("Ver respuesta bruta de DataForSEO SERP"):
                st.json(st.session_state.competitor_data.get("serp_raw", {}))

# =====================
# Paso 2: Inputs MEJORADO
# =====================
elif st.session_state.step == 2:
    st.subheader("Paso 2: Definir Parámetros del Contenido")
    
    # Mostrar recomendaciones de estrategia si están disponibles
    if st.session_state.content_strategy:
        strategy = st.session_state.content_strategy
        rec_words = strategy.get("recommended_word_count", {})
        
        st.info(f"💡 **Recomendación basada en competencia:** "
                f"{rec_words.get('optimal', 2000):,} palabras óptimas "
                f"(rango: {rec_words.get('min', 1500):,}-{rec_words.get('max', 3000):,})")
    
    with st.form("inputs_form"):
        c1, c2 = st.columns(2)
        with c1:
            # Keywords relacionadas con sugerencias
            current_related = st.session_state.inputs["relatedKeywords"]
            if st.session_state.content_strategy and not current_related:
                opportunities = st.session_state.content_strategy.get("keywords_opportunities", [])
                suggested_keywords = ", ".join(opportunities[:5])
                st.info(f"💡 Sugerencia: {suggested_keywords}")
                current_related = suggested_keywords
            
            st.session_state.inputs["relatedKeywords"] = st.text_area(
                "Keywords relacionadas (coma separadas)",
                value=current_related,
                placeholder="ej: carrera enfermería, estudiar enfermería Perú, enfermería UTP",
                height=90
            )
            
            st.session_state.inputs["title"] = st.text_input(
                "Título del artículo",
                value=st.session_state.inputs["title"],
                placeholder=f"Guía Completa: {st.session_state.keyword.title()} en Perú 2025"
            )
            
        with c2:
            st.session_state.inputs["tone"] = st.selectbox(
                "Tono del contenido",
                ["profesional", "casual", "tecnico", "educativo"],
                index=["profesional", "casual", "tecnico", "educativo"].index(st.session_state.inputs["tone"])
            )
            
            # Word count con recomendación
            word_options = [800, 1500, 2500, 3500]
            if st.session_state.content_strategy:
                optimal_words = st.session_state.content_strategy.get("recommended_word_count", {}).get("optimal", 1500)
                # Encontrar la opción más cercana o agregar la recomendada
                closest = min(word_options, key=lambda x: abs(x - optimal_words))
                if abs(closest - optimal_words) > 300:  # Si está muy lejos, agregar la recomendada
                    word_options.append(optimal_words)
                    word_options.sort()
                current_index = word_options.index(closest)
            else:
                current_index = word_options.index(st.session_state.inputs["wordCount"])
            
            st.session_state.inputs["wordCount"] = st.selectbox(
                "Cantidad de palabras",
                word_options,
                index=current_index
            )
            
        submitted = st.form_submit_button("📑 Continuar a Estructuras", type="primary")
        if submitted:
            if not st.session_state.inputs["title"].strip():
                st.warning("⚠️ Ingresa un título para continuar.")
            else:
                st.session_state.step = 3
                st.rerun()

# =====================
# Paso 3: Estructura MEJORADO
# =====================
elif st.session_state.step == 3:
    st.subheader("Paso 3: Seleccionar Estructura")
    
    # Obtener estructuras (incluyendo optimizada si hay estrategia)
    options = get_structure_options(st.session_state.keyword, st.session_state.content_strategy)
    
    # Destacar estructura optimizada si existe
    if any(opt.get("optimized") for opt in options):
        st.success("🎯 ¡Nueva! Estructura optimizada basada en análisis de competencia disponible")

    sel = st.radio(
        "Elige una estructura",
        options=[o["id"] for o in options],
        format_func=lambda oid: next(o["name"] for o in options if o["id"] == oid),
        horizontal=False
    )
    
    chosen = next(o for o in options if o["id"] == sel)
    
    # Mostrar preview de headers
    with st.expander("👀 Ver encabezados de la estructura seleccionada", expanded=True):
        st.write(f"**{chosen['name']}**")
        if chosen.get("optimized"):
            st.success("✨ Esta estructura fue generada analizando a tus competidores")
        
        for i, h in enumerate(chosen["headers"], start=1):
            st.write(f"**H{2 if i == 1 else 2}.** {h}")

    if st.button("✍️ Generar contenido final", type="primary"):
        st.session_state.selected_structure = chosen
        st.session_state.step = 4
        st.session_state.final_md = ""
        st.rerun()

# =====================
# Paso 4: Redacción MEJORADO
# =====================
elif st.session_state.step == 4:
    st.subheader("📝 Contenido Generado")
    
    if not st.session_state.final_md:
        with st.spinner("Redactando con OpenAI (considerando análisis de competencia)..."):
            try:
                st.session_state.final_md = generate_content_with_openai(
                    title=st.session_state.inputs["title"],
                    keyword=st.session_state.keyword,
                    structure=st.session_state.selected_structure,
                    tone=st.session_state.inputs["tone"],
                    word_count=st.session_state.inputs["wordCount"],
                    related_keywords=st.session_state.inputs["relatedKeywords"],
                    competitor_data=st.session_state.competitor_data or {},
                    strategy=st.session_state.content_strategy  # NUEVO: pasamos la estrategia
                )
            except Exception as e:
                st.error(f"Error generando contenido: {e}")

    # Info del proyecto
    kw = st.session_state.keyword
    tone = st.session_state.inputs["tone"]
    wc = st.session_state.inputs["wordCount"]
    structure_name = st.session_state.selected_structure.get('name', 'Desconocida')
    
    st.info(f"**Keyword:** {kw} | **Estructura:** {structure_name} | **Tono:** {tone} | **Palabras:** {wc:,}")
    
    # Mostrar estrategia aplicada si existe
    if st.session_state.content_strategy:
        with st.expander("🎯 Estrategia aplicada en este contenido"):
            strategy = st.session_state.content_strategy
            st.write("**Basado en análisis de competencia:**")
            for insight in strategy.get("competitor_insights", []):
                st.write(f"• {insight}")

    # Contenido
    st.markdown(st.session_state.final_md)

    # Acciones
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        download_md_button(f"{kw.replace(' ', '_') or 'articulo'}.md", st.session_state.final_md)
    with col2:
        if st.button("🔄 Regenerar"):
            st.session_state.final_md = ""
            st.rerun()
    with col3:
        if st.button("📝 Editar inputs"):
            st.session_state.step = 2
            st.rerun()
    with col4:
        if st.button("🆕 Nuevo proyecto"):
            for k in ["step","keyword","competitor_data","content_strategy","inputs","selected_structure","final_md"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
