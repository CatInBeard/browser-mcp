FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    unzip \
    && apt-get clean

ENV DISPLAY=:99

RUN mkdir -p /app/external/ublock_lite
RUN wget -O /tmp/uBlock.zip https://github.com/gorhill/uBlock/releases/download/1.62.0/uBlock0_1.62.0.chromium.zip && \
    unzip /tmp/uBlock.zip -d /app/external/ && \
    rm /tmp/uBlock.zip

RUN wget -O /app/external/Readability.js https://raw.githubusercontent.com/mozilla/readability/refs/heads/main/Readability.js 

RUN chmod a+r -R /app/external

COPY src/requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install-deps chromium
RUN playwright install chromium

COPY ./src .

EXPOSE 8000

CMD ["bash", "-c", "Xvfb :99 -screen 0 1024x768x24 & sleep 2 && python server.py"]
