# Changelog

Todos los cambios notables de career-mode se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/), y este proyecto sigue el [Versionado Semántico](https://semver.org/lang/es/).

[English](CHANGELOG.md)

## [0.1.1] - 2026-10-20

### Añadido

- **Pendientes:** se pueden encolar varios links a la vez, uno por línea. Cada link se comprueba y se encola en orden, y un resumen dice qué se encoló, qué se omitió y qué falló. Lo que no se pudo encolar se queda en el cuadro.
- **Backups:**
  - `profile.pdf` y `outreach.pdf` en `backup/profile/`, impresos con Chrome o Chromium.
  - Una copia del `.env` en `backup/env/env`, legible solo por el usuario.
  - Los posts diarios, con su log.
  - La carpeta del backup se abre después de ejecutarlo desde una terminal.
  - `restore-backup.sh` restaura el `.env` y los posts diarios, y guarda una copia de seguridad de ambos antes de reemplazarlos.
- **CLI:** comandos `profile-pdf` y `outreach-pdf` en `server/cli.py`.
- **Skills:**
  - `/commit`: hace commit en la rama actual con el autor por defecto y un mensaje de una línea, y nunca hace push.
  - `/write-daily-post` guarda cada post en `profile/daily-posts/` con una línea de tema y un `log.csv` que elige el siguiente tema.
- **Tests y CI:** una suite de pytest para el servidor, una de Node para el front end, `run-tests.sh` y un workflow de GitHub Actions que ejecuta ambas en cada push. Un test falla cuando algo del perfil real aparece en un archivo versionado.
- **Proyecto:** `.github/FUNDING.yml` y una sección de Git en `CLAUDE.md`.

### Cambiado

- **Seguimiento:** los días se cuentan desde la última aplicación en lugar del primer evento. El mensaje de un recruiter cuenta como aplicación, y una empresa sin ninguna usa su último evento.
- **Español:** la interfaz y `README.es.md` usan español neutro.
- **`/apply-pending`:**
  - Busca primero el link, para no aplicar dos veces al mismo JD Post.
  - Elige el canal según lo que dice el JD Post, escribe el asunto del email y elige el mensaje en el idioma del JD Post.
  - Procesa la cola de pendientes cuando se ejecuta sin un link.
  - Lee JD Posts de LinkedIn, primero con WebFetch y después en Claude in Chrome, y abre Chrome para cualquier otra página que no pueda leer.
- **`/apply-email` y `/apply-site`:** ambos informan si la aplicación se envió o por qué se detuvo. `/apply-site` se detiene ante captchas y cuentas por crear, deja el formulario abierto cuando se atasca y responde por sí mismo las preguntas del formulario.
- **`/reply-recruiter`:** una entrada de Calendar por conversación, solo las tecnologías por las que pregunta el recruiter, y sin necesidad de leer otro skill.
- **`/write-daily-post`:** el prompt de la imagen pide ortografía correcta y texto mínimo, el texto del post se muestra junto a la imagen, y una imagen mala se descarta y su tema se reutiliza.
- **`/setup`:** ofrece el `outreach.md` del backup y puede enviar un email de prueba a la dirección del propio usuario.

### Eliminado

- Los ajustes `BACKUP_DIR` y `CAREER_MODE_DB`. La base de datos es siempre `data/career-mode.db` y los backups van siempre a `backup/`. Las líneas antiguas en un `.env` se ignoran.

### Corregido

- `/apply-pending` registraba una aplicación antes de enviarla. Ahora la registra solo cuando ya salió.
- `/read-cv` crea su carpeta de backups con permisos privados.
- Un `.env` restaurado ya no puede mover la base de datos ni terminar en una carpeta que git no ignora.

### Seguridad

- La copia del `.env` en el backup es legible solo por el usuario, y siempre está en `backup/`, que git ignora.

## [0.1] - 2026-10-13

Primera versión.

[0.1.1]: https://github.com/victormarcias/career-mode/compare/0.1...0.1.1
[0.1]: https://github.com/victormarcias/career-mode/releases/tag/0.1
