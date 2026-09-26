# Radar Inmobiliario CABA — Planning

App personal para analizar y recomendar propiedades en venta en la Ciudad de Buenos Aires,
a partir de snapshots periódicos de los portales (Zonaprop, Argenprop y otros), con
historia de precios, antigüedad de publicaciones y métricas de mercado por zona.

> Este documento cubre **(1) qué se puede scrapear y cómo** y **(2) funcionalidades,
> vistas y configuración**. La arquitectura queda para después, a propósito.

---

## 1. Factibilidad de scraping

### 1.0 Aviso importante sobre este relevamiento

Desde el entorno donde se escribió este plan **no se pudo acceder a los portales**: la
política de red del contenedor bloquea `zonaprop.com.ar`, `argenprop.com` y
`mercadolibre.com.ar`. Todo lo que sigue sale de scrapers open source recientes,
documentación pública y del conocimiento general de cómo están armados estos sitios.
**Hay que validarlo desde tu compu** con la checklist de la sección 1.7 antes de
arrancar a construir.

### 1.1 Resumen

| Portal | Volumen CABA | Protección anti-bot | Dificultad | Recomendación |
|---|---|---|---|---|
| **Argenprop** | Alto | AWS WAF (desafío JS a veces) | Media-baja | **Empezar por acá** |
| **Zonaprop** | El más alto (~218k avisos en todo el país) | Cloudflare + DataDome antes; bloquea IPs de datacenter | Alta | Segunda fuente, con navegador real y desde IP residencial |
| **MercadoLibre Inmuebles** | Alto | API pública de búsqueda cerrada (403) desde 2025; el HTML está protegido | Alta | Fase 3, opcional |
| **Remax** | Medio (solo sus oficinas) | Sitio SPA con API JSON propia (a verificar) | Baja-media | Buena fuente extra, poco solapamiento |
| **Properati** | Bajo en Argentina | Baja | Baja | Poco valor hoy |
| Datos abiertos GCBA / IEyC | Agregados | Ninguna | Trivial | **Sí**, como referencia (benchmark de precio/m² por barrio) |

### 1.2 Argenprop

**Cómo está armado**
- Listados **renderizados del lado del servidor** (HTML con los datos adentro): alcanza
  con HTTP + parser (BeautifulSoup / selectolax), no hace falta navegador para la mayoría
  de los requests.
- URLs semánticas, por ejemplo:
  `https://www.argenprop.com/departamentos/venta/palermo/2-dormitorios?pagina-2`
  (tipo / operación / barrio / filtros, con la paginación como query). Se pueden combinar
  filtros de precio, ambientes, moneda y orden en la URL.
- **Tope de ~40 páginas por búsqueda.** Para cubrir toda CABA hay que **segmentar**
  (barrio × tipo × rango de precio) de modo que cada segmento quede por debajo del
  tope. Así lo resuelve uno de los scrapers relevados (`maxiguaymas/scraper-argenprop-final`),
  que sincroniza miles de avisos cada 2 horas.

**Protección**
- Está detrás de **AWS WAF**. Un bloqueo se ve como `403`, o `202` con el header
  `x-amzn-waf-action: challenge`.
- Lo que funciona hoy según los repos: **`curl_cffi` imitando el fingerprint TLS de
  Chrome**, y cuando sale el desafío JS, **fallback a navegador real** (`nodriver` /
  Playwright) para conseguir el token y seguir con HTTP.

**Datos disponibles**
- *En la tarjeta del listado:* precio + moneda, expensas, m² (cubiertos/totales),
  ambientes, dormitorios, baños, dirección/barrio, inmobiliaria, destacado/premium,
  foto principal, ID del aviso (en la URL).
- *En la ficha del aviso:* descripción completa, todas las fotos, antigüedad del
  edificio, disposición, orientación, amenities, cochera, apto crédito, **coordenadas**
  (mapa embebido) y, según el aviso, **fecha o antigüedad de publicación**.
- **Contactos (teléfono/WhatsApp):** técnicamente se pueden sacar, pero **no conviene
  guardarlos** (son datos personales, ver 1.6).

### 1.3 Zonaprop

**Cómo está armado**
- También SSR, con tarjetas que se identifican por atributos `data-qa` (lo más estable
  para parsear). **30 avisos por página.**
- URLs semánticas con slug, por ejemplo:
  `https://www.zonaprop.com.ar/departamentos-venta-palermo-2-ambientes-pagina-2.html`
- **Ojo: no devuelve 404 si el slug no existe**, te muestra otros resultados. Hay que
  validar el `<h1>` de la página contra lo que se pidió (así lo hace `Foquitos/zonaprop`).
- Por detrás hay endpoints JSON internos (la web usa un endpoint de *postings*; la app
  móvil usa `.../v3/postings` y `.../v4/postings/{id}`). Varios scrapers comerciales de
  Apify pegan directo a esa API y sacan lat/lon, inmobiliaria, etc. **Es la opción más
  limpia si se puede reproducir con la sesión/cookies del navegador.**

**Protección**
- **Cloudflare** (antes **DataDome**) y **bloqueo de IPs de datacenter**. Es decir:
  desde un servidor en la nube (AWS, GCP, Railway, etc.) no anda sin proxies
  residenciales pagos.
- Lo que funciona según `Foquitos/zonaprop` (actualizado en agosto de 2026):
  **Playwright con el Chrome instalado** (no el Chromium de Playwright), **perfil
  persistente** que guarda las cookies de Cloudflare, entrar primero a la home, y si
  aparece el captcha resolverlo **a mano una vez** (queda la cookie por un tiempo).
- Conclusión práctica: **el scraper de Zonaprop tiene que correr en tu compu (IP
  residencial)**, con navegador real, a ritmo humano.

**Datos disponibles**
- *Listado:* precio, moneda, expensas, m² totales/cubiertos, ambientes, baños,
  cocheras, dirección, barrio, inmobiliaria, extracto de la descripción, ID.
- *Ficha:* antigüedad, orientación, disposición (frente/contrafrente/interno),
  luminosidad, descripción completa, galería, coordenadas, "publicado hace X días"
  (a verificar si sigue visible) y a veces un indicador de baja de precio.
- **Costo:** entrar a cada ficha es caro (lento y más riesgo de bloqueo). Estrategia:
  **el listado todos los días, la ficha solo para avisos nuevos, avisos que cambiaron o
  favoritos**.

### 1.4 Otras fuentes

- **MercadoLibre Inmuebles:** `api.mercadolibre.com/sites/MLA/search` responde `403`
  sin autenticación desde 2025. Con una app registrada y un token OAuth *puede* que
  ande para la categoría inmuebles (MLA1459), pero no es seguro. El HTML tiene protección
  fuerte. Mucho solapamiento con los otros dos portales, así que **queda para después**.
- **Remax:** publica muchas propiedades exclusivas; el sitio es una SPA que se alimenta
  de una API JSON. Vale la pena mirarla en la pestaña Network del navegador: si la API
  es abierta, es la fuente más fácil de todas.
- **Properati:** bajo volumen hoy en Argentina.
- **Agregadores (Roomix y parecidos):** ya juntan varios portales, pero usarlos es
  depender de un tercero. Sirven como referencia.
- **Datos abiertos (sin scraping):**
  - GCBA *Mercado inmobiliario* (`data.buenosaires.gob.ar/dataset/mercado-inmobiliario`):
    precio de venta USD/m² por barrio, usado/a estrenar, 2 y 3 ambientes (armado sobre
    datos de Argenprop), además de escrituras e hipotecas.
  - IEyC CABA: precio promedio de publicación USD/m² por barrio y ambientes, trimestral
    desde 2017.
  - Colegio de Escribanos: escrituras mensuales (el termómetro de la demanda real).
  - Cotización del dólar (MEP/blue/oficial) para pasar a una sola moneda los avisos en ARS.
  - Barrios y comunas en GeoJSON (BA Data) y líneas y estaciones de subte/tren (para
    medir distancias).

### 1.5 Lo que solo se consigue guardando snapshots (el corazón de la app)

Los portales muestran la foto de hoy. La película la tenés que armar vos:

| Métrica | Cómo se obtiene |
|---|---|
| **Días en el mercado** | `hoy - primera vez visto` (y lo contrastás con la fecha que muestra el portal, cuando está) |
| **Historial de precio** | Precio en cada snapshot → bajas, subas, cantidad de cambios, % total |
| **Baja (probable venta / reserva)** | El aviso deja de aparecer N snapshots seguidos → estado "dado de baja" y su precio final |
| **Republicación** | Mismo inmueble con ID nuevo (misma dirección, m², ambientes y fotos parecidas) → suma su historia anterior. Las inmobiliarias republican para "resetear" la antigüedad |
| **Stock por zona** | Cantidad de avisos activos por barrio/segmento en el tiempo |
| **Absorción** | Bajas por mes / stock activo → meses de oferta por barrio |
| **Mismo inmueble en varios portales** | Dedup cross-portal: dirección normalizada + coordenadas + m² + ambientes + precio ± tolerancia + similitud de fotos (hash perceptual) |

### 1.6 Legales y buenas prácticas

- Los términos de uso de los portales **prohíben el scraping**. Para uso **personal**,
  con **baja frecuencia**, sin republicar los datos y sin usarlo comercialmente, el riesgo
  práctico es bajo, pero **existe**. Si algún día pensás hacerlo producto, hay que
  replantearlo (convenios o feeds oficiales).
- **Ley 25.326 (datos personales):** no guardar teléfonos, mails ni nombres de
  particulares. Guardar como mucho el nombre de la inmobiliaria.
- **Ritmo:** una pasada por día (máximo dos), con pausas aleatorias de varios segundos
  entre requests, sin concurrencia agresiva, en horarios normales.
- Respetar `robots.txt` en lo posible (no se pudo leer desde acá: verificarlo).
- Fotos: guardar la URL y un hash. No descargar galerías completas salvo de favoritos.

### 1.7 Checklist de validación (hacer desde tu compu, ~1 hora)

1. `curl` a un listado de Argenprop → ¿200 con datos, 403 o 202-challenge?
2. Lo mismo con `curl_cffi` (`impersonate="chrome"`).
3. Zonaprop con Playwright + perfil persistente → ¿aparece captcha? ¿cuánto dura la cookie?
4. En DevTools → Network de Zonaprop, filtrar XHR al paginar/filtrar → identificar el
   endpoint JSON de postings y qué headers/cookies necesita.
5. Ver en una ficha de cada portal si está la **fecha de publicación** y las **coordenadas**.
6. Contar cuántos avisos da "departamentos venta CABA" en cada portal, para dimensionar
   (esperable: decenas de miles).
7. Remax: pestaña Network → ¿API JSON abierta?
8. Leer los `robots.txt`.

---

## 2. Funcionalidades

### 2.1 Recolección (scrapers)
- Fuentes activables una por una (Argenprop, Zonaprop, Remax, etc.).
- **Búsquedas guardadas = segmentos a scrapear:** tipo (depto/PH/casa), barrios,
  rango de precio, ambientes. Por defecto: "toda CABA, deptos y PH en venta".
- Frecuencia por fuente (diaria por defecto) y horario.
- Profundidad: solo listado / listado + ficha de nuevos / ficha completa de favoritos.
- **Log de corridas:** avisos vistos, nuevos, cambiados, dados de baja, errores,
  bloqueos, duración.
- **Salud del parser:** alerta si una corrida trae muchos menos avisos de lo normal o
  si faltan muchos campos (señal de que el portal cambió el HTML).
- Botón de "correr ahora".

### 2.2 Normalización y enriquecimiento
- **Moneda única:** avisos en ARS pasados a USD con la cotización (MEP por defecto,
  configurable) del día en que se publicó o se vio el aviso.
- **Precio/m²** sobre m² cubiertos, totales o **"m² homogeneizados"** (cubiertos +
  50% semicubiertos + 25%–30% descubiertos, con coeficientes configurables).
- **Expensas en USD** y como % anual del precio.
- Barrio y comuna normalizados (el portal a veces dice "Palermo Hollywood", "Palermo
  Soho"… → barrio oficial + subbarrio comercial).
- **Geocodificación** cuando no hay coordenadas (con la dirección).
- **Distancias:** al subte más cercano, a líneas de tren/metrobús, a puntos que vos
  elijas (tu trabajo, la casa de tus viejos, etc.).
- **Extracción de atributos desde el texto de la descripción** (reglas y/o LLM):
  apto crédito, a estrenar, a reciclar, balcón/terraza, luminoso, contrafrente, piso,
  ascensor, cochera, amenities, "dueño directo", "urgente", "escucha ofertas",
  sucesión, ocupado/con inquilino, apto profesional.
- **Dedup cross-portal** y detección de republicaciones (ver 1.5).
- **Flags de calidad:** precio sospechoso (ej. USD 1 o precio de alquiler cargado como
  venta), m² incoherentes, aviso de emprendimiento "desde USD X" (se separa del resto).

### 2.3 Análisis de mercado
- Precio/m² **mediano** y percentiles (P25–P75) por barrio, tipo, ambientes, antigüedad
  (a estrenar / hasta 10 años / 10–30 / más de 30), con y sin cochera.
- **Evolución temporal:** precio/m² mediano, stock, avisos nuevos y bajas por semana/mes.
- **Días en el mercado** (mediana y distribución) por zona.
- **Descuentos:** % de avisos con baja de precio, baja promedio, tiempo hasta la primera baja.
- **Absorción / meses de oferta** por barrio (se calcula con las bajas de avisos).
- Contraste **precio publicado (tus datos) vs precio de escritura/referencia** (datos
  abiertos) como estimación de la brecha de negociación.
- Contexto macro: escrituras mensuales, hipotecas, dólar.

### 2.4 Valuación ("¿está caro o barato?")
- **Precio justo estimado** por aviso: modelo hedónico (regresión o gradient boosting)
  con barrio/coordenadas, m², ambientes, antigüedad, piso, cochera, amenities, estado,
  disposición, balcón, etc., entrenado con tus propios snapshots.
- **Desvío** = precio publicado vs precio justo, en % y en USD, con un intervalo de
  confianza (no un número mágico).
- **Comparables:** los N avisos más parecidos (activos y dados de baja) con su precio/m²
  y días en el mercado.
- Explicación del estimado: "+8% por cochera, −5% por contrafrente, …".

### 2.5 Recomendador / scoring
Un **score 0–100 por aviso**, combinando componentes con pesos que ajustás vos:

| Componente | Qué mide |
|---|---|
| Precio | Desvío vs precio justo y vs mediana de la zona |
| Oportunidad de negociación | Días en el mercado, bajas de precio acumuladas, palabras como "escucha ofertas" |
| Ubicación | Barrios preferidos, distancia a subte y a tus puntos de interés |
| Producto | Ambientes, m², luminosidad, piso, balcón, cochera, antigüedad, amenities |
| Costos | Expensas (absolutas y relativas) |
| Financiable | Apto crédito, precio dentro de tu presupuesto + margen |
| Riesgo | Datos inconsistentes, ocupado, sucesión, a reciclar, pocas fotos |

- **Filtros duros** (descartan) vs **preferencias** (suman/restan puntos).
- **Perfiles de búsqueda** con pesos distintos (ej.: "para vivir", "para inversión /
  renta", "para reciclar").
- Modo inversión: **rentabilidad bruta estimada** (alquiler estimado del barrio ×12 /
  precio) si también se scrapea alquiler.
- **Aprendizaje de tus gustos:** los favoritos y descartados ajustan los pesos con el
  tiempo (opcional, fase posterior).

### 2.6 Seguimiento personal (mini-CRM)
- Estados por aviso: *nuevo → interesante → contactado → visita agendada → visitado →
  ofertado → descartado*.
- Notas, fotos propias de la visita, checklist de visita (humedad, orientación real,
  ruido, estado del edificio, expensas reales, etc.).
- Etiquetas libres.
- Motivo de descarte (sirve para el aprendizaje de preferencias).
- **"Oculto para siempre"** (incluso si lo republican con otro ID, gracias al dedup).
- Comparador lado a lado de 2 a 4 propiedades.

### 2.7 Alertas
- Aviso nuevo que cumple un perfil y supera un score X.
- **Baja de precio** en un favorito o en cualquier aviso del perfil (con umbral en %).
- Favorito dado de baja (probablemente vendido o reservado).
- Aviso "subvaluado" (más de X% por debajo del precio justo).
- Republicación de un aviso que tenías visto.
- Resumen diario o semanal por mail/Telegram/WhatsApp: nuevos, bajas de precio, top 10.
- Alerta técnica: un scraper falló o trajo datos raros.

### 2.8 Exportar
- CSV/Excel de cualquier tabla filtrada.
- Ficha PDF de una propiedad con comparables (para mandarle a alguien o llevar a la visita).
- Links directos al aviso en cada portal donde aparece.

---

## 3. Vistas

### 3.1 Inicio / Dashboard
- KPIs: avisos activos, nuevos hoy/semana, bajas de precio hoy, dados de baja, precio/m²
  mediano de tu perfil (con variación mensual).
- **Top oportunidades** de tu perfil activo (por score).
- Movimientos en tus favoritos (cambios de precio, bajas).
- Estado de la última corrida de cada scraper.

### 3.2 Explorador (tabla + filtros)
- Tabla con todos los avisos, con columnas configurables: foto, barrio, dirección,
  precio, USD/m², desvío vs precio justo, expensas, m², ambientes, días en el mercado,
  bajas de precio, score, portales donde aparece, estado personal.
- **Filtros laterales:** portal, barrio/comuna (multi), tipo, ambientes, dormitorios,
  baños, rango de precio y de USD/m², m² mín/máx, expensas máx, antigüedad, piso,
  cochera, balcón/terraza, apto crédito, a estrenar, días en el mercado, "tuvo baja de
  precio", score mínimo, estado (activo/dado de baja), distancia máx a subte o a un punto,
  búsqueda por texto en la descripción ("luminoso", "sin expensas", …).
- Orden por cualquier columna. Filtros guardables como **vistas**.
- Toggle "incluir dados de baja" (sirve para ver a cuánto se fueron los parecidos).

### 3.3 Mapa
- Puntos coloreados por **score**, **desvío vs precio justo**, **USD/m²** o **días en
  el mercado** (a elección).
- Capas: barrios/comunas, **heatmap de USD/m²**, subte/tren, tus puntos de interés,
  radio de X minutos a pie.
- Dibujar un polígono a mano → se convierte en filtro ("solo esta zona").
- Click en punto → mini-ficha.

### 3.4 Ficha de propiedad
- Fotos, datos, descripción, atributos extraídos.
- **Gráfico del historial de precio** (con cada cambio marcado) y línea de tiempo:
  primera vez visto, republicaciones, cambios, baja.
- Portales donde aparece (con el precio en cada uno: a veces difieren).
- **Precio justo** + explicación + **comparables** (tabla y mapa chico).
- Posición vs su barrio (percentil de USD/m² y de días en el mercado).
- Desglose del score.
- Tu seguimiento: estado, notas, checklist de visita, etiquetas.
- Costos estimados de compra: escritura, sellos, honorarios de la inmobiliaria,
  escribano (con porcentajes configurables) → **costo total real**.

### 3.5 Mercado por barrio
- Ranking de barrios: USD/m² mediano, variación 1/3/6/12 meses, stock, días en el
  mercado, % con baja de precio, meses de oferta.
- Drill-down a un barrio: evolución de cada métrica, distribución de precios (histograma
  / boxplot por ambientes), antigüedad del stock.
- Comparar 2–4 barrios en los mismos gráficos.

### 3.6 Tendencias
- Series temporales de CABA y de tu perfil: USD/m², stock, altas, bajas, bajas de precio.
- Contraste con datos oficiales (escrituras, precio de referencia de GCBA/IEyC) y con
  el dólar.
- Cohortes: "de los avisos publicados en mes X, cuántos siguen activos a los 30/60/90
  días y con qué descuento".

### 3.7 Mis seguimientos (kanban)
- Columnas por estado (interesante / contactado / visita / ofertado / descartado).
- Arrastrar tarjetas, ver cambios recientes en cada una.

### 3.8 Comparador
- 2–4 propiedades lado a lado: todos los atributos, precio justo, score, costos, mapa.

### 3.9 Alertas y notificaciones
- Bandeja de alertas disparadas (leídas/no leídas) y administración de reglas.

### 3.10 Admin / Scrapers
- Corridas (historial, métricas, errores), salud de cada parser, cobertura por
  segmento, botón "correr ahora", revisión de duplicados dudosos (unir/separar a mano).

---

## 4. Opciones de configuración

**Perfiles de búsqueda** (varios, uno activo)
- Presupuesto (mín/máx, en USD) y margen de tolerancia.
- Barrios incluidos/excluidos, o polígono propio.
- Tipos de propiedad, ambientes, m² mínimos, antigüedad máxima, piso mínimo.
- Obligatorios vs deseables (cochera, balcón, apto crédito, ascensor, luminoso…).
- Expensas máximas.
- Puntos de interés con peso y distancia máxima.
- Pesos de cada componente del score (sliders), con presets: *para vivir*, *inversión*,
  *reciclar*, *primera vivienda con crédito*.

**Cálculo y datos**
- Tipo de dólar para convertir ARS (MEP / oficial / blue).
- Base de m² para precio/m² (cubiertos / totales / homogeneizados + coeficientes).
- Umbral de días sin ver un aviso para darlo de baja (ej. 3 corridas).
- Tolerancias del dedup (distancia, % de m², % de precio).
- Qué cuenta como "oportunidad" (ej. más de 10% bajo el precio justo).
- Costos de compra (% escritura, sellos, honorarios, escribano).
- Si se incluyen o no emprendimientos/pozo.

**Scraping**
- Fuentes activas, frecuencia, horario, profundidad (listado/ficha), segmentos a cubrir,
  pausas entre requests, máximo de páginas por corrida.

**Alertas**
- Canales (mail / Telegram / WhatsApp / solo in-app), frecuencia del resumen, umbrales
  (score mínimo, % de baja de precio), silencio nocturno.

**Visualización**
- Columnas visibles y orden por defecto del explorador, vistas guardadas, métrica por
  defecto del mapa, moneda de visualización, tema claro/oscuro.

---

## 5. Roadmap funcional sugerido

| Fase | Contenido | Resultado |
|---|---|---|
| **0. Validación** | Checklist 1.7 | Saber qué anda de verdad |
| **1. MVP** | Scraper de Argenprop (solo listado, diario) + snapshots + días en el mercado + historial de precio + explorador con filtros + ficha básica | Ya ves cómo se mueven los precios |
| **2. Zonaprop + dedup** | Scraper de Zonaprop (navegador, local) + dedup cross-portal + republicaciones + mapa | Cobertura casi completa |
| **3. Inteligencia** | Precio justo, comparables, score con perfiles, mercado por barrio, tendencias | Recomendador real |
| **4. Uso diario** | Alertas, resumen diario, kanban, comparador, costos de compra, exportar | Herramienta para la búsqueda |
| **5. Extras** | Remax/MercadoLibre, alquileres (rentabilidad), extracción con LLM de la descripción, aprendizaje de preferencias, datos oficiales | Más fino |

> Consejo: **arrancar a guardar snapshots cuanto antes**, aunque sea solo con Argenprop y
> una tabla simple. La historia no se puede reconstruir para atrás, y es lo que más vale
> de toda la app.

---

## 6. Preguntas abiertas
1. ¿Solo compra o también alquiler (para calcular rentabilidad)?
2. ¿Deptos y PH únicamente, o también casas, cocheras y locales?
3. ¿Dónde va a correr el scraper? (Zonaprop exige una IP residencial: tu compu, una
   Raspberry o un proxy residencial pago.)
4. ¿Canal de alertas preferido?
5. ¿Qué querías reutilizar de la app *Sentidos*? (No la encontré en los repos a los
   que tengo acceso.)

---

## Fuentes consultadas
- [Foquitos/zonaprop](https://github.com/Foquitos/zonaprop): Playwright, Cloudflare/DataDome, bloqueo de IPs de datacenter, `data-qa`, 30 avisos por página, validación del `<h1>`
- [maxiguaymas/scraper-argenprop-final](https://github.com/maxiguaymas/scraper-argenprop-final): AWS WAF, `curl_cffi` + `nodriver`, tope de 40 páginas, segmentación, matching con Zonaprop
- [Sotrosca/zona-prop-scraper](https://github.com/Sotrosca/zona-prop-scraper), [pablol314/scraper-zonaprop](https://github.com/pablol314/scraper-zonaprop)
- [LeoArtaza/Scraper-Argenprop](https://github.com/LeoArtaza/Scraper-Argenprop), [Nilton94/Web_Scraping_Arg](https://github.com/Nilton94/Web_Scraping_Arg) (Streamlit + mapa), [pomber/depto_scraper](https://github.com/pomber/depto_scraper)
- Scrapers de Zonaprop en Apify (API de postings): [memo23](https://apify.com/memo23/zonaprop-scraper), [jungle_synthesizer](https://apify.com/jungle_synthesizer/zonaprop-scraper)
- [Scrapfly: AWS WAF](https://scrapfly.io/blog/posts/how-to-bypass-aws-waf-when-web-scraping)
- [API de búsqueda de MercadoLibre, 403 (DEV)](https://dev.to/devil_scrapes/we-doubled-mercado-libres-scraper-memory-and-clearance-went-from-50-to-90-with-zero-code-33p0), [MercadoLibre Developers: inmuebles](https://developers.mercadolibre.com.ar/es_ar/localizar-inmuebles)
- [BA Data: Mercado inmobiliario](https://data.buenosaires.gob.ar/dataset/mercado-inmobiliario), [IEyC CABA: mercado inmobiliario](https://www.estadisticaciudad.gob.ar/eyc/?cat=129)
- [Roomix: portales 2026](https://roomix.ai/blog/top-portales-inmobiliarios-argentina-2026)
