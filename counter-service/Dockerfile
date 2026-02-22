FROM python:3.11-slim
WORKDIR /app
RUN pip install flask --no-cache-dir
COPY main.py .
EXPOSE 8002
CMD ["python3", "main.py"]