FROM python:3.12-slim-bookworm

WORKDIR /app

# Instala unixODBC, tzdata y herramientas necesarias para agregar el repo de Microsoft
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    unixodbc-dev \
    curl \
    gnupg \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configura la zona horaria del contenedor (solo en build, no queda como env var en runtime)
ARG TZ=America/Panama
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Instala el driver ODBC 17 de Microsoft para SQL Server
RUN curl -sSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# Instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

EXPOSE 3000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]