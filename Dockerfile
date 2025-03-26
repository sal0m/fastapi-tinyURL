FROM python:3.9

RUN mkdir /fastapi_app

WORKDIR /fastapi_app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/fastapi_app

RUN chmod +x /fastapi_app/docker/*.sh

# WORKDIR /fastapi_app/src

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
