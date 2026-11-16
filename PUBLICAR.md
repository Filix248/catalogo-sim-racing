# Acceder y publicar APEX / LAB

**Catálogo público:** [apex-lab-sim-racing.streamlit.app](https://apex-lab-sim-racing.streamlit.app/).

Esta es la dirección para visitar el catálogo. Funciona sin arrancar Python en tu computador. La aplicación ya está desplegada en Streamlit Community Cloud con Supabase; el código está en [Filix248/catalogo-sim-racing](https://github.com/Filix248/catalogo-sim-racing), un repositorio público autorizado por el propietario.

La ampliación revisada el 16 de noviembre de 2026 contiene **16 productos y siete categorías**, con enlaces de Amazon.com y la etiqueta pública de seguimiento `apexlabsimrac-20`. Las tarjetas se adaptan a tres, dos o una columna según el ancho de la pantalla. **Ver presentación** abre una ficha modal por producto, con vista ampliada, descripción propia, características, contenido del conjunto y fuentes. La compra de Amazon y los requisitos y avisos completos se consultan dentro de esa ficha.

Las imágenes actuales son ilustraciones originales de categorías, no fotos exactas de los productos. La presentación incluye enlaces para ver las fotos y el modelo en el fabricante. No se copiaron imágenes de fabricantes sin permiso. No se publican precios, stock ni reseñas.

## Usar la versión local

Para desarrollar o probar cambios, ejecuta desde la carpeta del proyecto:

```powershell
python -m streamlit run app.py
```

La dirección `http://127.0.0.1:8501/` solo funciona en el computador que ejecuta ese servidor y mientras el proceso sigue activo. Si el servidor está detenido, abre el enlace público de arriba o inicia de nuevo el comando local. Desde otro dispositivo, usa la dirección pública.

## Actualizar o recuperar la publicación

1. Utiliza el repositorio existente `Filix248/catalogo-sim-racing`. `app.py` debe quedar en su raíz, junto a `catalogo.py`, `styles.css` y `requirements.txt`; conserva las carpetas `assets`, `tests` y `.streamlit`.
2. Al subir archivos, usa solo el código y los recursos preparados. Si utilizas la carpeta `para-subir-a-github`, actualiza primero sus copias con los cambios que quieras publicar. Si utilizas un ZIP, extrae su contenido antes de subirlo a GitHub.
3. Entra a [Streamlit Community Cloud](https://share.streamlit.io/) y abre la aplicación existente para revisar su estado o configuración. Para recuperar un despliegue desde cero, selecciona `Create app` → `Deploy from repo`.
4. Elige el repositorio, la rama `main` y el archivo `app.py`. En `Advanced settings`, usa Python 3.12. La dirección pública configurada es `apex-lab-sim-racing.streamlit.app`.
5. La conexión real a Supabase se configura en `Advanced settings` → `Secrets`. El archivo local `.streamlit/secrets.toml` permanece fuera de GitHub. Sin credenciales, la aplicación muestra datos de demostración identificados como tales.
6. Revisa que la aplicación permita visitas públicas y comprueba su URL sin iniciar sesión. Un repositorio público contiene el código; la dirección `streamlit.app` es la página del catálogo.
7. Después de una actualización, comprueba el número de fichas, sus categorías y la cuadrícula en pantalla amplia, intermedia y móvil. Abre y cierra **Ver presentación** de distintos productos; revisa los avisos completos, los enlaces de Amazon y del fabricante, y que los filtros, guardados y comparación sigan funcionando. La consulta de Supabase conserva datos en caché durante cinco minutos. El contenido de la base de datos se mantiene por separado del código; la interfaz pública solo lo lee.

La carpeta `para-subir-a-github` y el archivo `catalogo-apex-github.zip` contienen únicamente **18 archivos públicos**: código, documentación, ocho SVG originales, configuración visual, requisitos y pruebas. Excluyen credenciales, capturas, logs, JSON de investigación o respaldo, scripts de operaciones locales y cachés. No subas la carpeta completa del proyecto.

La compatibilidad depende de los metadatos documentados de cada ficha. Si falta información, se indica como pendiente; no se deduce soporte de juegos, consolas o accesorios a partir del nombre del producto. La web incluye avisos de afiliación y las compras se realizan en Amazon. La publicación no garantiza la aprobación definitiva del programa ni ingresos.

Para incorporar fotos reales, utiliza imágenes con permiso válido para el catálogo o configura una integración autorizada con la API oficial de Amazon. El recurso [Images](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/api-reference/resources/images) devuelve imágenes principales y variantes en distintos tamaños. Esta integración está sujeta al acceso y la licencia de la API; no forma parte de la publicación actual ni se habilita solo con la etiqueta de afiliado.

Documentación oficial:

- [Repositorios de GitHub](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
- [Desplegar en Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Configurar Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Compartir la aplicación](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)
- [Contrato de Amazon Associates de Estados Unidos](https://affiliate-program.amazon.com/help/operating/agreement)
- [Políticas del programa de Amazon.com](https://affiliate-program.amazon.com/help/operating/policies/)
