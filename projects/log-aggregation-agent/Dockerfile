FROM python:3.12-slim

WORKDIR /workspace
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "runtime.agent"]
