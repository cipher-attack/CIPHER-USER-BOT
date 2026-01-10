# python version
FROM python:3.11-slim

# ffmpeg installation
# ca-certificates for yt-dlp
RUN apt-get update && \
    apt-get install -y ffmpeg ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# craete work space
WORKDIR /app

# Pip update and upgrade
RUN pip install --upgrade pip

# copy major files
COPY requirements.txt .

# install pkg 
RUN pip install --no-cache-dir -r requirements.txt

# copy code
COPY . .

# run bot
CMD ["python", "main.py"]