FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema para o MySQL
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as libs do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código
COPY . .

# Variável de ambiente para garantir que o log apareça no terminal
ENV PYTHONUNBUFFERED=1
