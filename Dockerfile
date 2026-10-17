FROM ghcr.io/astral-sh/uv:0.11.18 AS uv
FROM python:3.11-slim
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 DATA_DIR=/data
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app.py chainlit.md menu.json ./
COPY core ./core
COPY public ./public
COPY .chainlit/config.toml ./.chainlit/config.toml
COPY .chainlit/translations/en-US.json ./.chainlit/translations/en-US.json
# Mount persistent storage at /data; configure secrets through environment variables.
RUN useradd --create-home --uid 10001 app && mkdir -p /data && chown -R app:app /app /data
USER app
EXPOSE 8000
CMD ["sh", "-c", ".venv/bin/python -m chainlit run app.py --headless --host 0.0.0.0 --port ${PORT:-8000}"]
