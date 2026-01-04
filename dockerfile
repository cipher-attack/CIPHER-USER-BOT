# Python 3.11 ስሪትን ተጠቀም
FROM python:3.11-slim

# ffmpeg እና ሌሎች አስፈላጊ ነገሮችን መጫን
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# የስራ ቦታ መፍጠር
WORKDIR /app

# አስፈላጊ ፋይሎችን መገልበጥ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ቦቱን ማስጀመር (የፋይልህ ስም main.py ካልሆነ ቀይረው)
CMD ["python", "main.py"]
