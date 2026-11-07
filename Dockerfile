FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY catalogue ./catalogue
RUN pip install --no-cache-dir .
USER nobody
EXPOSE 8080
CMD ["uvicorn", "--factory", "agriconnect.app:app", "--host", "::", "--port", "8080"]
