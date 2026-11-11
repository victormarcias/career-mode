# Demo

See it working, with invented data only: **[victormarcias.online/demo/career-mode](https://victormarcias.online/demo/career-mode)**

The demo is career-mode with a made-up person and made-up job search, so it can be shown to anyone:

- **100 invented companies**, half with English names and notes and half Spanish: agencies and clients, some of them through an agency. Nothing in them is real, and every link uses the reserved `.example` domain.
- **Events of every type** (applications, recruiters who wrote first, interviews, offers, rejections, red flags, links in the queue...), all of them in the last two weeks, with every type in the current week. The dates are worked out from today every time the demo starts, so the Calendar always opens on a busy week.
- **An invented profile and messages** (`demo/profile/`: Lucía Marín, her CV facts, and the six outreach messages in Spanish and English).
- **No `.env`**: Settings shows nothing set, so nothing can be read from your computer or sent from it.

## Run it yourself

From the repo root:

```bash
./demo/run-demo.sh
```

It opens at <http://localhost:8334>, next to the real app if that one is running (port 8333). It makes a new database in `demo/data/` (ignored by git) on every start and never touches `data/`, `profile/` or `.env`. To stop it:

```bash
./demo/run-demo.sh stop
```

## What is in this folder

| File | What it is |
|---|---|
| `make_demo.py` | Makes the invented companies and events as `calendar.csv` and `companies.csv`, with the dates around today. Same day, same data. |
| `run-demo.sh` | Makes the data, loads it into a fresh database and starts the server with the demo's own profile and no `.env`. |
| `profile/` | The invented profile (`profile.md`), messages (`outreach.md`) and picture (`photo.png`). |

## Publish it (Cloud Run behind Firebase Hosting)

`serve.py` is the entry for a host: the same app, read-only, under the `/demo/career-mode` prefix (`DEMO_PREFIX` changes it), with the data made when it starts and a fresh start every day, so the dates never go stale. `Dockerfile` copies only what it needs, and `.dockerignore` keeps `data/`, `backup/`, `profile/` and `.env` out of the image and of any cloud build.

1. Build and push the image (replace the project and repository; `--platform` matters on an Apple chip), then deploy it as a public service:

   ```bash
   docker build --platform linux/amd64 -f demo/Dockerfile -t us-east4-docker.pkg.dev/PROJECT/REPO/career-mode-demo .
   docker push us-east4-docker.pkg.dev/PROJECT/REPO/career-mode-demo
   gcloud run deploy career-mode-demo --image us-east4-docker.pkg.dev/PROJECT/REPO/career-mode-demo \
     --region us-east4 --allow-unauthenticated --max-instances 2 --project PROJECT
   ```

2. In the portfolio's `firebase.json`, next to the `/hero-blog` rewrites, send the path to that service:

   ```json
   { "source": "/demo/career-mode", "run": { "serviceId": "career-mode-demo", "region": "us-east4" } },
   { "source": "/demo/career-mode/**", "run": { "serviceId": "career-mode-demo", "region": "us-east4" } }
   ```

3. Before deploying to production, try it in a Firebase preview channel (`firebase hosting:channel:deploy demo-test`). The portfolio's `headers` rule sets a strict `Content-Security-Policy` for every `.js`, `.css`, `.html`... path, and the app loads Tailwind from `https://cdn.tailwindcss.com`: if that header also reaches the demo's files, the page loads unstyled. If it does, give `/demo/career-mode/**` its own `headers` rule with a policy that allows `cdn.tailwindcss.com` and inline styles.

This was run locally (with and without the prefix, read-only, no `.env`) but not deployed: the Cloud Run and Firebase steps are untested.
