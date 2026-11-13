# Publicar APEX / LAB

El catálogo está preparado para Streamlit Community Cloud. El repositorio puede ser privado mientras que la aplicación publicada debe ser pública para que Amazon pueda visitarla.

1. Crea un repositorio en tu cuenta de GitHub llamado `catalogo-sim-racing`. Puedes mantenerlo privado. No agregues plantillas de README, licencia ni .gitignore: el proyecto ya incluye sus archivos.
2. Sube el **contenido** de la carpeta `para-subir-a-github`, manteniendo las carpetas `assets`, `tests` y `.streamlit`. `app.py` debe quedar en la raíz del repositorio. No subas el ZIP como un único archivo: primero extrae su contenido si usas el paquete comprimido.
3. Entra a https://share.streamlit.io/, crea o abre tu cuenta y conecta GitHub. Selecciona `Create app` y `Yup, I have an app`.
4. Elige tu repositorio, la rama `main` y el archivo `app.py`. En `Advanced settings`, usa Python 3.12.
5. Para usar los datos reales, copia tu configuración local de Supabase en `Advanced settings` → `Secrets`. El archivo `.streamlit/secrets.toml` queda en tu equipo y no está incluido en la carpeta de subida. También puedes publicar primero en modo de muestra sin añadir credenciales.
6. Publica y revisa `Settings` → `Sharing`: la aplicación debe permitir visitas públicas. Comprueba su URL sin iniciar sesión antes de usarla en la solicitud de Amazon.
7. Completa fichas y contenido editorial propio antes de enviar la solicitud. Una web publicada no garantiza la aprobación de Amazon.

La carpeta de subida incluye únicamente el código, las ilustraciones originales, la configuración visual, los requisitos y las pruebas. Excluye credenciales, capturas y cachés. No se ha creado ningún repositorio ni publicado la aplicación al preparar esta carpeta.

Documentación oficial:

- https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app
- https://affiliate-program.amazon.com/help/node/topic/G8TW5AE9XL2VX9VM
