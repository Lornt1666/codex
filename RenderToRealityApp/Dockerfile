FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --upgrade pip && pip install -r requirements.txt
# Blender is not installed here; for full mesh export, extend this Dockerfile with Blender CLI support
CMD ["python", "main.py"]
