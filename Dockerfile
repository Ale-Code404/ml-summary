FROM python:3.12.0-bookworm

RUN apt-get update

RUN apt install chromium chromium-driver -y

WORKDIR /app

COPY requirements.txt /app/

# Install Python dependencies with no cache option
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "python", "./src/main.py" ]
