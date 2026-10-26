# Changelog

Todos los cambios notables de career-mode se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/), y este proyecto sigue el [Versionado Semántico](https://semver.org/lang/es/).

[English](CHANGELOG.md)

## [Unreleased]

### Añadido

- **`/sync-aiapply`:** lee las notificaciones de AIApply.io en Gmail y registra cada respuesta positiva de una empresa (una invitación a entrevista, un assessment, un seguimiento) como una application web, una sola vez, con la empresa como agency o como client. Sus avisos "Not this time" pasan a la papelera cuando ya no queda nada por registrar de ellos.
- **`/reply-rejected`:** busca los rechazos que las empresas enviaron al Gmail del usuario y responde a cada uno, una sola vez, agradeciendo y diciendo que seguirán en contacto, archiva el mail y registra el rechazo en el Calendar.
- **`/check-email`:** ordena el Gmail reciente y ejecuta `/sync-aiapply`, `/reply-rejected` y `/reply-recruiter` sobre lo que encuentra.

### Cambiado

- **Empresa en cada evento nuevo:** el formulario de Update, el de New application y la sincronización con Google Calendar piden una sola Empresa, con una etiqueta Agency (por defecto) o Client al lado. Un client tiene un campo opcional A través de una agency. Al escribir el nombre de una empresa que ya existe se elige esa, y su etiqueta la sigue. Un nombre que ya existe con la otra etiqueta se rechaza, así no se crea una empresa dos veces.
- **Mensajes pasivos:** un mensaje pasivo necesita una agency o un client, así que el recruiter de una empresa que contrata directo se registra en el client. Las bases de datos existentes se migran al arrancar.
- **`/reply-recruiter`:** registra al empleador directo como client, y a una agency como agency.
- **`/apply-pending`:** un JD Post se descarta cuando se actualizó por última vez hace un mes o más, y ninguna tecnología descarta un post: lo que cuenta es Python o JavaScript, y las otras herramientas se pueden aprender.
- **Salida de los skills:** `/sync-aiapply`, `/reply-rejected`, `/check-email`, `/reply-recruiter` y `/apply-pending` ya no cuentan qué hicieron, salvo que el comando lleve `--verbose`. Los fallos, lo que necesita al usuario y los borradores de respuesta se muestran siempre.
- **Una empresa, una API:** las agencies y los clients son una sola lista de empresas, cada una agency o client (`companyType`), con el nombre único sea cual sea: el mismo nombre ya no se puede crear dos veces, ni por la API ni por un formulario. Un evento tiene un `companyId` (su client, o su agency si no hay client) y un `viaCompanyId` (la agency por la que llegó un client). El estado de una empresa se deriva de sus eventos en lugar de guardarse. La página de Companies, Follow Up, los formularios, la sincronización con Google Calendar, los backups (`companies.csv` tiene una columna `company_type`, y los archivos de backup anteriores se siguen cargando) y los skills lo usan. Las bases de datos existentes se migran al arrancar.

### Eliminado

- `/api/agencies` y `/api/clients`: usa `/api/companies`, con `?companyType=agency` o `client` para quedarte con un tipo, y `?companyId=` en `/api/events` en lugar de `?agencyId=` y `?clientId=`.

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

[Unreleased]: https://github.com/victormarcias/career-mode/compare/0.1.1...HEAD
[0.1.1]: https://github.com/victormarcias/career-mode/compare/0.1...0.1.1
[0.1]: https://github.com/victormarcias/career-mode/releases/tag/0.1
