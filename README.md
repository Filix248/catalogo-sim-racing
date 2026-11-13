# APEX / LAB · Catálogo de sim racing

Proyecto local en Streamlit para explorar hardware, guardar productos durante la sesión, comparar hasta tres opciones y armar una selección inicial por plataforma, simulador, resolución y nivel. Incluye ilustraciones originales de categorías; no representan el aspecto exacto de cada modelo. **No está publicado.**

## Ejecutar

Desde la carpeta del proyecto, con Python instalado:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abre la dirección local que indica Streamlit. Para ejecutar las pruebas del motor de catálogo:

```powershell
python -m unittest discover -s tests -v
```

## Conectar el catálogo

La aplicación usa `SUPABASE_URL` y `SUPABASE_KEY` desde variables de entorno o desde el archivo local `.streamlit/secrets.toml`. Puede reutilizar la configuración existente. No compartas ese archivo ni lo subas a un repositorio. La clave debe tener acceso de lectura al catálogo mediante las políticas de Supabase; no hace falta una clave administrativa.

La consulta lee hasta **500 registros** de la tabla `catalogo_amazon` y los conserva en caché durante **cinco minutos**. La interfaz no modifica la base de datos. Sin configuración o si falla la consulta, muestra un catálogo de demostración identificado como tal. Una tabla conectada y vacía se muestra vacía.

Columnas del catálogo:

| Columna | Contenido |
| --- | --- |
| `id` | Identificador único y estable, recomendado para guardados y comparación. |
| `nombre` | Nombre y variante exacta del producto. |
| `categoria` | Por ejemplo, `Volante`, `GPU` o `Monitor`. |
| `nivel_presupuesto` | `Entry`, `Mid-range` o `Enthusiast`. Es una clasificación, no un límite de gasto. |
| `specs_tecnicas` | Objeto JSON con las características documentadas. |
| `url_afiliado` | Enlace HTTPS real de Amazon o enlace corto oficial; puede quedar vacío. |
| `precio_aprox` | Campo heredado opcional. Se conserva al cargar, pero no se muestra como precio vigente. |

En `specs_tecnicas` se admiten `tipo`, `fuerza_feedback`, `vram_gb` y `hz`. Para evaluar la selección, añade únicamente metadatos comprobados para la variante concreta:

- `plataformas`: lista de valores como `PC`, `PlayStation`, `Xbox` o `Laptop con eGPU`.
- `simuladores`: lista de juegos con soporte o requisitos documentados.
- `resolucion_ideal`: objetivo editorial, por ejemplo `1080p`; orienta el orden de los candidatos y no garantiza rendimiento.

Las listas deben reflejar el soporte documentado. Si faltan, están vacías o tienen un formato incorrecto, la compatibilidad queda **por confirmar**. No se deduce la variante de un volante por su nombre. El soporte para PC tampoco confirma una caja eGPU o un portátil específico. Las GPU de escritorio se excluyen para consola.

Los cinco registros iniciales aún no incluyen metadatos de compatibilidad. Sus direcciones `/dp/ejemplo1`, `/dp/ejemplo2`, etc. son ejemplos inactivos: los botones de compra permanecen deshabilitados. Reemplázalas por enlaces reales de la variante correcta. La validación del formato de una URL no verifica el producto, la disponibilidad ni que genere comisión.

## Alcance actual

Los guardados y la comparación duran durante la sesión de Streamlit; no se sincronizan entre dispositivos. El configurador ofrece como máximo una opción por categoría y puede producir una selección parcial. No calcula FPS, no comprueba todas las conexiones de un equipo y no muestra precios ni existencias en tiempo real. Las compras se realizan en Amazon.

Antes de activar la afiliación, confirma el marketplace, el identificador de seguimiento y los requisitos de tu programa. Consulta el [contrato de Amazon Afiliados](https://afiliados.amazon.es/help/operating/agreement) y sus [políticas de contenido](https://afiliados.amazon.es/help/operating/policies/); estos enlaces corresponden a España.

## Cuatro ideas para crecer

1. **Colección para espacios pequeños:** soportes plegables, fijación a mesa y medidas verificadas para guardar el equipo después de correr.
2. **Mejoras según lo que te limita:** recorridos por control, postura, espacio o imagen, con una comparación concreta de alternativas de la misma categoría.
3. **Fichas con más evidencia:** fotos propias o autorizadas, medidas y conexiones, variante exacta, fuentes del fabricante y fecha de revisión.
4. **Enlaces reales por mercado:** elegir el país objetivo, incorporar enlaces oficiales con el identificador de seguimiento correcto y revisar que cada botón lleve a su variante. La afiliación no garantiza ingresos.
