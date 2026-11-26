# APEX / LAB · Catálogo de sim racing

**Abre el catálogo público:** [apex-lab-sim-racing.streamlit.app](https://apex-lab-sim-racing.streamlit.app/).

La versión pública funciona en Streamlit Community Cloud. Carga el catálogo de Supabase cuando está disponible y, si falta la conexión o la configuración, conserva las fichas y enlaces mediante una copia editorial pública fechada. Puedes visitarla sin iniciar Python ni dejar este computador encendido. El código está en el [repositorio público de GitHub](https://github.com/Filix248/catalogo-sim-racing).

El catálogo permite explorar hardware, guardar productos durante la sesión, comparar hasta tres opciones y armar una selección inicial por plataforma, simulador, resolución y nivel. El selector de simulador incluye 18 juegos y permite buscar escribiendo su nombre.

## Catálogo actual

La ampliación revisada el 16 de noviembre de 2026 reúne **16 productos de Amazon.com en siete categorías**: seis volantes, dos palancas de cambios, una pedalera, un soporte, un cockpit, dos GPU y tres monitores. Las fichas identifican el modelo o variante, el contenido del conjunto y los requisitos documentados. El kit Logitech G923 existente se mantiene identificado como reacondicionado.

Cada producto tiene descripción editorial, advertencias cuando necesita otro componente, enlaces a fuentes del fabricante y fecha de revisión. Las tarjetas resumen el modelo y sus características principales; **Ver presentación** abre una ficha modal individual. La ficha reúne la vista ampliada, las especificaciones, el contenido del conjunto, los requisitos completos y el enlace de compra de Amazon. Los avisos de compatibilidad y de componentes no incluidos acompañan al botón de compra. No se muestran precios, existencias, puntuaciones ni reseñas.

Las imágenes actuales son ilustraciones originales de categorías y no fotografías exactas de cada modelo. A las cuatro ilustraciones iniciales se añadieron `pedals.svg`, `shifter.svg`, `stand.svg` y `cockpit.svg` para las nuevas categorías. Cada presentación ofrece un enlace para ver el modelo y sus fotos en la web del fabricante. No se copiaron fotografías de fabricantes sin un permiso adecuado.

## Presentación visual

La portada combina tonos tinta con acentos lima y una ilustración original de cockpit sobre un trazado abstracto. Sus contadores de productos, categorías y niveles se calculan a partir del catálogo disponible; no representan visitas, ventas ni otras métricas comerciales.

La navegación rápida por categoría conserva los demás filtros de la selección. **Ver todo el garage** restablece los filtros, y los accesos compactos por nivel permiten explorar las colecciones inicial, intermedia y entusiasta. En **Explorar**, el listado intercala categorías para mostrar más variedad desde las primeras tarjetas; esta presentación no modifica la base de datos ni el motor de compatibilidad y selección.

El catálogo adapta la cuadrícula a tres tarjetas por fila en pantallas amplias, dos en tamaños intermedios y una en móviles. Cada tarjeta separa la marca y el modelo, prioriza la ilustración y destaca los datos principales; la ficha conserva el nombre completo del producto y su variante. La presentación individual permite consultar el detalle sin perder los filtros, los guardados ni la comparación de la sesión.

Las fotos reales podrán integrarse cuando se disponga de una licencia válida para ese uso. Otra vía es el recurso [Images de la API oficial de Amazon](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/api-reference/resources/images), que proporciona imágenes principales y variantes en distintos tamaños. Su incorporación requiere acceso a la API, configuración y cumplimiento de la licencia aplicable; no está activada por el mero hecho de añadir un enlace de afiliado.

Los enlaces de Amazon.com utilizan el identificador público de seguimiento verificado `apexlabsimrac-20`. La web incluye el aviso de afiliación general y otro junto a cada enlace de compra. La condición de la oferta, la disponibilidad, los gastos de envío y la entrega a Chile se consultan en Amazon al comprar.

## Desarrollo local

En **Comparar**, la selección de uno a tres productos se muestra en una tabla visual y se puede descargar con **Descargar comparativa en PDF**. El documento A4 horizontal incluye un resumen y fichas completas paginadas, con los requisitos, advertencias, condición de la oferta y enlaces al catálogo y al fabricante. Los accesos de compra del PDF vuelven a la web; no contiene enlaces de afiliado directos a Amazon. Sustituye a la antigua descarga JSON. La selección se conserva al descargar. El PDF se genera en memoria con ReportLab, sin enviar los productos elegidos a un servicio externo ni guardar un historial. Refleja los datos del catálogo en el momento de generarlo; no verifica precios ni disponibilidad.

Para trabajar en el código de este computador, abre una terminal en la carpeta del proyecto y ejecuta:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abre la dirección local que indica Streamlit, normalmente `http://127.0.0.1:8501/`. Esa dirección funciona únicamente en el computador que está ejecutando el servidor y requiere mantener el proceso activo. Si cierras la terminal o detienes Streamlit, la versión local deja de responder. Para visitar el catálogo desde otro dispositivo, usa el enlace público de arriba.

Para ejecutar las pruebas del catálogo:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Conectar el catálogo

La aplicación usa `SUPABASE_URL` y `SUPABASE_KEY` desde variables de entorno o desde el archivo local `.streamlit/secrets.toml`. Puede reutilizar la configuración existente. No compartas ese archivo ni lo subas a un repositorio. La clave debe tener acceso de lectura al catálogo mediante las políticas de Supabase; no hace falta una clave administrativa.

La consulta lee hasta **500 registros** de la tabla `catalogo_amazon` y los conserva en caché durante **cinco minutos**. La interfaz no modifica la base de datos. Sin configuración o si falla la consulta, utiliza `catalogo_publico.json`: una copia depurada de los **16 productos**, revisada el **16 de noviembre de 2026**, con sus fichas y enlaces de Amazon.com. La interfaz la identifica como **Catálogo de respaldo · revisión 16/11/2026**, aclara que la versión conectada no está disponible y permite **Reintentar conexión** sin esperar a la caché. La fecha corresponde a esa copia, no a una verificación actual de los productos ni a precios, disponibilidad o existencias.

El respaldo solo contiene campos editoriales públicos, fuentes y enlaces de afiliado; no necesita credenciales. Debe actualizarse de forma expresa después de revisar las fichas. Si falta o es inválido, la web muestra una demostración claramente identificada con enlaces de compra desactivados. Una tabla conectada y vacía se muestra vacía: no se sustituye por el respaldo. Los productos con un ASIN documentado que coincide con su enlace de Amazon usan identificadores estables por mercado y ASIN para mantener guardados y comparación al cambiar de fuente.

Columnas del catálogo:

| Columna | Contenido |
| --- | --- |
| `id` | Identificador único y estable, recomendado para guardados y comparación. |
| `nombre` | Nombre y variante exacta del producto. |
| `categoria` | `Volante`, `Palanca de cambios`, `Pedales`, `Soporte`, `Cockpit`, `GPU` o `Monitor`. |
| `nivel_presupuesto` | `Entry`, `Mid-range` o `Enthusiast`. Es una clasificación, no un límite de gasto. |
| `specs_tecnicas` | Objeto JSON con las características documentadas. |
| `url_afiliado` | Enlace HTTPS real de Amazon o enlace corto oficial; puede quedar vacío. |
| `precio_aprox` | Campo heredado opcional. Se conserva al cargar, pero no se muestra como precio vigente. |

En `specs_tecnicas` se guardan características como `tipo`, `fuerza_feedback`, `vram_gb`, `hz`, `resolucion` y `conexion`, además de `asin`, `descripcion_editorial`, `incluye`, `requiere`, `advertencia`, `fuentes_fabricante` y `fecha_revision`. `resolucion` describe el panel del monitor; no es una promesa de rendimiento del equipo. Para evaluar la selección, añade únicamente metadatos comprobados para la variante concreta:

- `plataformas`: lista de valores como `PC`, `PlayStation`, `Xbox` o `Laptop con eGPU`.
- `simuladores`: lista de juegos con soporte o requisitos documentados.
- `resolucion_ideal`: objetivo editorial, por ejemplo `1080p`; orienta el orden de los candidatos y no garantiza rendimiento.

Las listas deben reflejar el soporte documentado. Si faltan, están vacías o tienen un formato incorrecto, la compatibilidad queda **por confirmar**. No se deduce la variante de un volante por su nombre. El soporte para PC tampoco confirma una caja eGPU o un portátil específico. Las GPU de escritorio se excluyen para consola.

Las fichas genéricas iniciales se sustituyeron por modelos concretos y enlaces reales. La validación del formato de una URL no verifica por sí sola el producto, la disponibilidad ni que una compra genere comisión. Los accesorios no reciben soporte universal de PC o consola: una palanca o pedalera puede requerir una base, conexión o firmware específico, y un soporte necesita comprobar su anclaje.

## Alcance actual

Los guardados y la comparación duran durante la sesión de Streamlit; no se sincronizan entre dispositivos. El configurador ofrece como máximo una opción por categoría y puede producir una selección parcial. No calcula FPS, no comprueba todas las conexiones de un equipo y no muestra precios ni existencias en tiempo real. Las compras se realizan en Amazon.

La afiliación corresponde a Amazon.com. Consulta el [contrato del programa](https://affiliate-program.amazon.com/help/operating/agreement) y sus [políticas de contenido](https://affiliate-program.amazon.com/help/operating/policies/). La publicación de la web y los enlaces no garantiza la aprobación definitiva ni ingresos.

## Cuatro ideas para crecer

1. **Colección para espacios pequeños:** soportes plegables, fijación a mesa y medidas verificadas para guardar el equipo después de correr.
2. **Mejoras según lo que te limita:** recorridos por control, postura, espacio o imagen, con una comparación concreta de alternativas de la misma categoría.
3. **Fichas con más evidencia:** ampliar medidas, conexiones y pruebas propias, manteniendo la variante exacta y sus fuentes.
4. **Revisión periódica:** comprobar que los enlaces siguen llevando al modelo previsto y actualizar fuentes cuando cambien las variantes.
