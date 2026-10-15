FROM python:3.12-slim

WORKDIR /app

# Test extras stay in this image so a judge can run pytest in the same
# container they start. No env file is copied into the image.
COPY requirements.txt requirements-dev.txt pytest.ini ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY src/ ./src/
COPY tests/ ./tests/

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
