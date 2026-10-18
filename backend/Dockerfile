FROM python:3.10-slim

WORKDIR /app

RUN set -e; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
        sed -i 's/security.debian.org/mirrors.aliyun.com\/debian-security/g' /etc/apt/sources.list; \
    fi; \
    if [ -d /etc/apt/sources.list.d ]; then \
        find /etc/apt/sources.list.d -type f \( -name "*.list" -o -name "*.sources" \) -exec sed -i 's/deb.debian.org/mirrors.aliyun.com/g' {} + ; \
        find /etc/apt/sources.list.d -type f \( -name "*.list" -o -name "*.sources" \) -exec sed -i 's/security.debian.org/mirrors.aliyun.com\/debian-security/g' {} + ; \
    fi; \
    apt-get update && apt-get install -y gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*


# 先安装 CPU 版本的 PyTorch（大幅减小镜像体积，避免 CUDA 依赖问题）
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout 120 --retries 5 torch==2.2.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
