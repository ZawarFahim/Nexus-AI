FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project configuration
COPY pyproject.toml ./

# Install dependencies using uv
RUN uv pip install --system -r pyproject.toml

# Install Playwright OS dependencies and Chromium
RUN playwright install-deps chromium
RUN playwright install chromium

# Copy application code
COPY app /app/app
COPY alembic.ini ./
COPY alembic /app/alembic

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
