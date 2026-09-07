FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libenchant-2-dev \
    enchant-2 \
    hunspell-en-us \
    fonts-noto \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
ENV CHROME_PATH=/usr/bin/chromium
ENV CHROMIUM_PATH=/usr/bin/chromium
WORKDIR /app
COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["python3.11", "bot.py"]