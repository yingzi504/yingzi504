ARG PYTHON_IMAGE=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.12-slim
FROM ${PYTHON_IMAGE}

ARG APT_MIRROR=http://mirrors.aliyun.com/debian
ARG APT_SECURITY_MIRROR=http://mirrors.aliyun.com/debian-security

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i \
            -e "s#http://deb.debian.org/debian#${APT_MIRROR}#g" \
            -e "s#http://deb.debian.org/debian-security#${APT_SECURITY_MIRROR}#g" \
            -e "s#http://security.debian.org/debian-security#${APT_SECURITY_MIRROR}#g" \
            /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i \
            -e "s#http://deb.debian.org/debian#${APT_MIRROR}#g" \
            -e "s#http://deb.debian.org/debian-security#${APT_SECURITY_MIRROR}#g" \
            -e "s#http://security.debian.org/debian-security#${APT_SECURITY_MIRROR}#g" \
            /etc/apt/sources.list; \
    fi; \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        fontconfig \
        fonts-dejavu \
        fonts-wqy-microhei \
        fonts-wqy-zenhei \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libreoffice \
        libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
RUN if [ -n "$PIP_INDEX_URL" ]; then pip config set global.index-url "$PIP_INDEX_URL"; fi \
    && python -m pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/default-data /app/default-templates /app/data /app/uploads /app/output /app/templates \
    && cp -a /app/data/. /app/default-data/ 2>/dev/null || true \
    && cp -a /app/templates/. /app/default-templates/ 2>/dev/null || true \
    && sed -i 's/\r$//' /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
