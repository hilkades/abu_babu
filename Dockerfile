FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir -U pip

COPY pyproject.toml /app/pyproject.toml

# Minimal "pip install" without poetry: install deps from PEP621
RUN python -c "import tomllib,sys; p=tomllib.load(open('pyproject.toml','rb')); print('\n'.join(p['project']['dependencies']))" > /tmp/requirements.txt \
  && pip install --no-cache-dir -r /tmp/requirements.txt \
  && pip install --no-cache-dir alembic

COPY . /app

CMD ["python", "-m", "bot.main"]

