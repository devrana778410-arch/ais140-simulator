# AIS-140 Simulator & Telematics Socket Gateway Container
FROM python:3.11-slim

WORKDIR /app

# Copy full simulator source tree
COPY . /app

EXPOSE 8080

CMD ["python", "web/server.py", "8080"]
