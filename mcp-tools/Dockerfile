FROM python:3.12-slim
WORKDIR /app
COPY server.py ./server.py
ENV PYTHONUNBUFFERED=1 PORT=8000
EXPOSE 8000
CMD ["python","server.py"]
