FROM python:3.11-slim
WORKDIR /app
RUN pip install flask requests --no-cache-dir
COPY main.py .
EXPOSE 8000
CMD ["python3", "main.py"]