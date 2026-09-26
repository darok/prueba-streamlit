# HANDOFF — Radar Inmobiliario CABA

> Resumen autocontenido para seguir en otra sesión (en tu compu).
> Fecha: 2026-09-26 · Documento largo con todo el detalle: `docs/plan_app_propiedades_caba.md`

---

## 0. Cómo usar este archivo

1. Copialo a la carpeta del proyecto nuevo en tu compu.
2. Abrí una sesión de Claude Code ahí y pegale el **prompt de arranque** (sección 8).
3. Primer trabajo: correr la **validación** (sección 5). Eso define qué fuentes andan antes
   de escribir la app.

---

## 1. Qué es la app

App personal que:
- scrapea **avisos de venta en CABA** (Argenprop y Zonaprop primero, otros después);
- guarda **snapshots periódicos** (diarios) para reconstruir la historia de cada aviso;
- calcula: **días en el mercado, historial de precio, bajas de precio, bajas de aviso
  (probable venta), republicaciones, stock y precio/m² por barrio**;
- estima un **precio justo** con comparables, pone un **score** por aviso según perfiles
  configurables y manda **alertas**.

Uso personal, sin fines comerciales. La arquitectura **todavía no se decidió** (ver sección 7).

---

## 2. Estado de la investigación

Hecha desde un entorno cloud **sin acceso a los portales** (la red bloqueaba zonaprop,
argenprop, mercadolibre y apify). Todo sale de repos open source, documentación y búsquedas.
Cada punto lleva su nivel de confianza:

- ✅ confirmado por varias fuentes
- 🟡 probable, falta verificar
- ❓ desconocido

---

## 3. Hallazgos por fuente

### 3.1 Argenprop (empezar por acá)
- Dueño: AGEA S.A. (Grupo Clarín). Absorbió Inmuebles Clarín. Dice tener más de 530.000 avisos en el país. ✅
- HTML renderizado en el servidor: alcanza con HTTP + parser, sin navegador. ✅
- URLs semánticas: `/departamentos/venta/palermo?pagina-2`, con filtros en el path. 🟡 (confirmar el formato exacto)
- **Tope de ~40 páginas por búsqueda**: hay que segmentar por barrio × tipo × rango de precio. ✅
- Protección **AWS WAF**. Un bloqueo se ve como `403`, o `202` + header `x-amzn-waf-action: challenge`. ✅
- Lo que anda según los repos: `curl_cffi` con `impersonate="chrome"`, y cuando sale el
  desafío JS, fallback a navegador real (`nodriver` / Playwright) para sacar el token. ✅
- Campos del listado: precio, moneda, expensas, m², ambientes, dormitorios, baños,
  dirección/barrio, inmobiliaria, destacado. ✅
- Campos de la ficha: descripción, fotos, antigüedad, amenities, cochera, apto crédito,
  coordenadas. ✅ Fecha de publicación: 🟡
- Tiene app móvil (`com.argenprop`): su API interna podría ser más fácil que la web. ❓
- Referencia: el repo `maxiguaymas/scraper-argenprop-final` sincroniza cada 2 horas y hace matching con Zonaprop.

### 3.2 Zonaprop
- Dueño: Navent, comprado por **QuintoAndar** (Brasil) en diciembre de 2021. Es el portal más grande (~218.000 avisos). ✅
- HTML renderizado en el servidor. Las tarjetas se identifican por atributos `data-qa`. **30 avisos por página.** ✅
- URLs con slug: `departamentos-venta-palermo-2-ambientes-pagina-2.html`. ✅
- **No devuelve 404 si el slug no existe**: hay que validar el `<h1>` contra lo pedido. ✅
- **NUEVO:** existe un filtro por antigüedad en la URL, por ejemplo
  `inmuebles-publicado-hace-menos-de-1-dia.html`. Permite hacer una **corrida diaria
  incremental** (solo los nuevos) y dejar el barrido completo para 1–2 veces por semana.
  Así se baja muchísimo la cantidad de requests. ✅ (la URL aparece indexada; confirmar
  que se combina con `departamentos-venta-capital-federal`)
- Protección **Cloudflare** (antes DataDome) y **bloqueo de IPs de datacenter**: tiene
  que correr en la compu de casa (IP residencial). ✅
- Lo que anda (`Foquitos/zonaprop`, agosto de 2026): Playwright con el **Chrome
  instalado** (`channel="chrome"`), **perfil persistente**, entrar primero a la home,
  captcha a mano si aparece (la cookie dura un tiempo). ✅
- Hay APIs JSON internas: la web usa un endpoint de postings ("rplis") y la app móvil
  usa `bsre.zonaprop.com.ar/v3/postings` y `/v4/postings/{id}`. Los scrapers comerciales
  de Apify las usan. **Es la opción ideal si se puede reproducir con las cookies del
  navegador** (datos limpios, con lat/lon). 🟡
- Campos de la ficha: antigüedad, orientación, disposición, luminosidad, descripción,
  galería (patrón `resizeUrl1200x1200`), coordenadas. ✅
- Fragilidad: cambios en los `data-qa` y en el patrón de las fotos. ✅

### 3.3 Otras fuentes
| Fuente | Estado |
|---|---|
| MercadoLibre Inmuebles | La API pública `sites/MLA/search` responde **403 sin autenticación** desde 2025. Con token OAuth de una app propia: ❓. Categoría inmuebles: `MLA1459`. Fase tardía. |
| Remax | Muchos avisos exclusivos. Hay varios scrapers comerciales, o sea que se puede. La SPA probablemente consume una API JSON: mirar en Network. ❓ |
| Properati | Poco volumen en Argentina. Baja prioridad. |
| Roomix y otros agregadores | Referencia, no fuente. |

### 3.4 Datos abiertos y APIs gratis para enriquecer (sin scraping) ✅
| Qué | Dónde |
|---|---|
| Precio USD/m² de venta por barrio (GCBA, armado sobre Argenprop) | `data.buenosaires.gob.ar/dataset/mercado-inmobiliario` |
| Precio de publicación USD/m² por barrio y ambientes, trimestral desde 2017 | IEyC CABA, `estadisticaciudad.gob.ar/eyc/?cat=129` |
| Muestra de avisos de venta de departamentos | `data.buenosaires.gob.ar/dataset/departamentos-venta` |
| Barrios / Comunas en GeoJSON | `data.buenosaires.gob.ar/dataset/barrios`, `/dataset/comunas` |
| Estaciones y líneas de subte en GeoJSON | `data.buenosaires.gob.ar/dataset/subte-estaciones` |
| **Normalizar y geocodificar direcciones de CABA** (oficial, gratis) | USIG: `servicios.usig.buenosaires.gob.ar/normalizar` + API Geocodificador (`data.buenosaires.gob.ar/dataset/api-geocodificador-direcciones-caba`) |
| Dólar hoy (oficial, blue, MEP, CCL) | `dolarapi.com` (`/v1/dolares/bolsa`, etc.) |
| Dólar histórico | `api.argentinadatos.com/v1/cotizaciones/dolares/{oficial,blue,bolsa,contadoconliqui}` |
| Escrituras mensuales (demanda real) | Colegio de Escribanos CABA (informe mensual; agosto de 2026: 6.055 escrituras, −4,9% interanual) |

---

## 4. Reglas de juego (legales / éticas)
- Los términos de uso de los portales prohíben el scraping. Uso personal, baja frecuencia,
  sin republicar ni vender datos.
- **No guardar teléfonos, mails ni nombres de particulares** (Ley 25.326). Como mucho, la inmobiliaria.
- Una corrida por día (incremental), barrido completo 1–2 veces por semana, pausas
  aleatorias de 3 a 10 segundos, sin paralelismo agresivo.
- Fotos: guardar URL + hash perceptual, no descargar galerías (salvo favoritos).
- Leer los `robots.txt` (no se pudo desde acá).

---

## 5. Validación a correr primero (en tu compu)

### 5.1 Checklist
1. [ ] Argenprop con `requests` común → ¿200 con avisos?
2. [ ] Argenprop con `curl_cffi` (impersonate chrome) → ¿200?
3. [ ] Argenprop: ¿cuántas páginas da "departamentos venta capital federal"? ¿El tope es 40?
4. [ ] Argenprop: ¿la ficha muestra fecha de publicación? ¿Coordenadas?
5. [ ] Zonaprop con Playwright + Chrome + perfil persistente → ¿captcha? ¿Cuánto dura la cookie?
6. [ ] Zonaprop: DevTools → Network → XHR al paginar/filtrar → anotar endpoint, método,
       body y headers del JSON de postings. ¿Se puede repetir con `curl_cffi` usando las cookies?
7. [ ] Zonaprop: ¿anda `departamentos-venta-capital-federal-publicado-hace-menos-de-1-dia.html`?
8. [ ] Zonaprop: ¿la ficha/tarjeta muestra "publicado hace X días"?
9. [ ] Remax: DevTools → Network → ¿API JSON abierta?
10. [ ] Leer los `robots.txt` de cada sitio.
11. [ ] Anotar la cantidad total de avisos de deptos+PH en venta en CABA por portal.

### 5.2 Script de prueba (`probe_portales.py`)

```python
"""
Prueba rápida de acceso a portales. Guarda el HTML en ./probe_out para inspeccionarlo.
pip install requests curl_cffi playwright
(Playwright usa tu Chrome instalado: no hace falta 'playwright install')
"""
import pathlib, re, time
import requests
from curl_cffi import requests as creq

OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

URLS = {
    "argenprop_listado": "https://www.argenprop.com/departamentos/venta/capital-federal",
    "argenprop_p2":      "https://www.argenprop.com/departamentos/venta/capital-federal?pagina-2",
    "zonaprop_listado":  "https://www.zonaprop.com.ar/departamentos-venta-capital-federal.html",
    "zonaprop_nuevos":   "https://www.zonaprop.com.ar/departamentos-venta-capital-federal-publicado-hace-menos-de-1-dia.html",
    "argenprop_robots":  "https://www.argenprop.com/robots.txt",
    "zonaprop_robots":   "https://www.zonaprop.com.ar/robots.txt",
}

# Marcadores para diagnosticar (son heurísticos: revisar el HTML guardado)
MARKERS = {
    "cloudflare": r"Just a moment|cf-challenge|challenge-platform",
    "datadome":   r"datadome|captcha-delivery",
    "aws_waf":    r"awswaf|aws-waf-token|challenge\.js",
    "zp_cards":   r'data-qa="posting',
    "ap_cards":   r"listing__item",
    "publicado":  r"[Pp]ublicado hace",
}

def diagnose(name, status, headers, text):
    hits = {k: len(re.findall(p, text)) for k, p in MARKERS.items()}
    waf = headers.get("x-amzn-waf-action")
    print(f"{name:22} {status}  {len(text):>8}B  waf={waf}  {hits}")
    (OUT / f"{name}.html").write_text(text, encoding="utf-8")

def probe_http():
    for lib, get in [("requests", lambda u: requests.get(u, headers={"User-Agent": UA}, timeout=30)),
                     ("curl_cffi", lambda u: creq.get(u, impersonate="chrome", timeout=30))]:
        print(f"\n== {lib}")
        for name, url in URLS.items():
            try:
                r = get(url)
                diagnose(f"{lib}_{name}", r.status_code, r.headers, r.text)
            except Exception as e:
                print(f"{lib}_{name:15} ERROR {e}")
            time.sleep(4)

def probe_browser():
    """Zonaprop con navegador real. Si aparece captcha, resolvelo a mano."""
    from playwright.sync_api import sync_playwright
    xhrs = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            ".perfil-chrome", channel="chrome", headless=False, locale="es-AR")
        page = ctx.new_page()
        page.on("request", lambda req: xhrs.append((req.method, req.url))
                if req.resource_type in ("xhr", "fetch") else None)
        page.goto("https://www.zonaprop.com.ar/", wait_until="domcontentloaded")
        input("Si hay captcha, resolvelo. Enter para seguir...")
        page.goto(URLS["zonaprop_listado"], wait_until="domcontentloaded")
        time.sleep(5)
        diagnose("browser_zonaprop", 200, {}, page.content())
        print("h1:", page.locator("h1").first.inner_text())
        ctx.close()
    print("\nXHR/fetch vistos (buscar 'posting'):")
    for m, u in xhrs:
        if "posting" in u.lower() or "rplis" in u.lower():
            print(" ", m, u)

if __name__ == "__main__":
    probe_http()
    probe_browser()
```

Qué mirar: ¿status 200 y `zp_cards` / `ap_cards` > 0? → anda. ¿`cloudflare` / `aws_waf` > 0
o status 403/202? → bloqueado con ese método. En `probe_out/` queda el HTML para armar los
selectores reales.

---

## 6. Alcance funcional (resumen; el detalle está en el plan largo)

**Datos derivados (el núcleo):** primera/última vez visto, días en el mercado,
historial de precio, bajas y subas, aviso dado de baja (N corridas sin verlo),
republicaciones (mismo inmueble con ID nuevo), dedup entre portales (dirección
normalizada por USIG + coordenadas + m² + ambientes + precio ± tolerancia + hash de
fotos), stock y absorción por barrio.

**Normalización:** USD con MEP (configurable), precio/m² (cubiertos / totales /
homogeneizados), expensas, barrio oficial, geocodificación, distancia al subte y a
puntos propios, atributos sacados de la descripción (apto crédito, "escucha ofertas",
contrafrente, a reciclar, ocupado, etc.), flags de datos dudosos, separar emprendimientos
de pozo.

**Inteligencia:** precio justo (modelo hedónico) + comparables + explicación; score
0–100 con pesos por perfil (vivir / inversión / reciclar / crédito); filtros duros vs
preferencias.

**Vistas:** Dashboard · Explorador (tabla + filtros) · Mapa (capas y polígono) ·
Ficha (historial de precio, comparables, costos de compra) · Mercado por barrio ·
Tendencias y cohortes · Seguimientos (kanban) · Comparador · Alertas · Admin de scrapers.

**Configuración:** perfiles de búsqueda, pesos del score, tipo de dólar, base de m²,
umbral de baja, tolerancias del dedup, costos de compra, fuentes / frecuencia /
profundidad del scraping, canales y umbrales de las alertas, columnas y vistas guardadas.

**Roadmap:** 0 Validación → 1 MVP con Argenprop + snapshots + explorador →
2 Zonaprop + dedup + mapa → 3 precio justo + score + mercado → 4 alertas + CRM →
5 extras (Remax/ML, alquileres, LLM, aprendizaje de preferencias).
**Arrancar a guardar snapshots cuanto antes: la historia no se recupera para atrás.**

---

## 7. Decisiones pendientes (para la sesión en tu compu)
1. ¿Solo compra o también alquiler (para la rentabilidad)?
2. ¿Qué tipos: deptos + PH solamente, o también casas, cocheras y locales?
3. ¿Dónde corre el scraper? (Zonaprop pide IP residencial: tu PC, una Raspberry o un proxy residencial.)
4. Canal de alertas (Telegram es el más simple).
5. Stack. Opciones para discutir, **sin decidir**: Python + Playwright/curl_cffi para
   scrapear; SQLite o DuckDB para arrancar (Postgres/Supabase si después va a la nube);
   Streamlit como UI inicial, que ya usás en este repo (hay un precedente: Nilton94 usa
   Streamlit + Folium + DuckDB para esto mismo).
6. Qué reutilizar de tu app **Sentidos** (no estaba en los repos accesibles desde la sesión cloud).

---

## 8. Prompt de arranque para la nueva sesión

```
Leé HANDOFF_radar_inmobiliario.md (y plan_app_propiedades_caba.md si está).
Quiero construir la app "Radar Inmobiliario CABA" descrita ahí.
Paso 1: ayudame a correr la validación de la sección 5 (el script probe_portales.py
y la checklist), interpretemos los resultados juntos y actualicemos el HANDOFF
con lo confirmado. Después decidimos stack/arquitectura (sección 7) y arrancamos
por el MVP de la fase 1. Todo en español.
```

---

## 9. Fuentes
- Scrapers: [Foquitos/zonaprop](https://github.com/Foquitos/zonaprop) · [maxiguaymas/scraper-argenprop-final](https://github.com/maxiguaymas/scraper-argenprop-final) · [Nilton94/Web_Scraping_Arg](https://github.com/Nilton94/Web_Scraping_Arg) · [Sotrosca/zona-prop-scraper](https://github.com/Sotrosca/zona-prop-scraper) · [LeoArtaza/Scraper-Argenprop](https://github.com/LeoArtaza/Scraper-Argenprop) · [pomber/depto_scraper](https://github.com/pomber/depto_scraper) · [rodrigouroz/housing_scrapper](https://github.com/rodrigouroz/housing_scrapper)
- APIs de Zonaprop (terceros): [Apify memo23](https://apify.com/memo23/zonaprop-scraper) · [Apify ocrad](https://apify.com/ocrad/zonaprop-property-scraper/api) · [Anakin](https://anakin.io/catalog/zonaprop)
- Filtro por antigüedad de Zonaprop: [publicado hace menos de 1 día](https://www.zonaprop.com.ar/inmuebles-publicado-hace-menos-de-1-dia.html)
- Anti-bot: [Scrapfly AWS WAF](https://scrapfly.io/blog/posts/how-to-bypass-aws-waf-when-web-scraping) · [curl_cffi (Bright Data)](https://brightdata.com/blog/web-data/web-scraping-with-curl-cffi)
- MercadoLibre: [API 403 (DEV)](https://dev.to/devil_scrapes/we-doubled-mercado-libres-scraper-memory-and-clearance-went-from-50-to-90-with-zero-code-33p0) · [Developers inmuebles](https://developers.mercadolibre.com.ar/es_ar/localizar-inmuebles)
- Dueños: [QuintoAndar compra Navent (LexLatin)](https://lexlatin.com/noticias/quintoandar-se-expande-america-latina-compra-negocio-inmobiliario-navent) · [Argenprop en App Store (AGEA)](https://apps.apple.com/ar/app/argenprop-alquiler-y-venta/id400300356)
- Datos abiertos: [Mercado inmobiliario GCBA](https://data.buenosaires.gob.ar/dataset/mercado-inmobiliario) · [IEyC](https://www.estadisticaciudad.gob.ar/eyc/?cat=129) · [Barrios GeoJSON](https://data.buenosaires.gob.ar/dataset/barrios) · [Subte](https://data.buenosaires.gob.ar/dataset/subte-estaciones) · [USIG normalizador](https://servicios.usig.buenosaires.gob.ar/normalizar) · [Geocodificador CABA](https://data.buenosaires.gob.ar/dataset/api-geocodificador-direcciones-caba)
- Dólar: [DolarApi](https://dolarapi.com/docs/argentina/) · [ArgentinaDatos](https://api.argentinadatos.com)
- Mercado: [Roomix portales 2026](https://roomix.ai/blog/top-portales-inmobiliarios-argentina-2026)
