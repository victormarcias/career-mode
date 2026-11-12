# The public demo (see demo/serve.py). Build from the repo root:  docker build -f demo/Dockerfile -t career-mode-demo .
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# only what the demo needs: never data/, backup/, profile/ or .env (see also .dockerignore)
COPY server ./server
COPY public ./public
COPY demo/serve.py demo/make_demo.py ./demo/
COPY demo/profile ./demo/profile
ENV PORT=8080
CMD ["sh", "-c", "exec uvicorn serve:app --app-dir demo --host 0.0.0.0 --port ${PORT}"]
