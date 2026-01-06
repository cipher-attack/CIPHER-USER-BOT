# Python 3.11 ስሪትን ተጠቀም
FROM python:3.11-slim

# ffmpeg እና አስፈላጊ የሆኑ የሲስተም ፓኬጆችን መጫን
# (ca-certificates ለ yt-dlp ኢንተርኔት ኮኔክሽን ይጠቅማል)
RUN apt-get update && \
    apt-get install -y ffmpeg ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# የስራ ቦታ መፍጠር
WORKDIR /app

# Pip ማዘመን (ለደህንነት እና ፍጥነት)
RUN pip install --upgrade pip

# አስፈላጊ ፋይሎችን መገልበጥ
COPY requirements.txt .

# ፓኬጆችን መጫን
RUN pip install --no-cache-dir -r requirements.txt

# ኮዱን መገልበጥ
COPY . .

# ቦቱን ማስጀመር
CMD ["python", "main.py"]