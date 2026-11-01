FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Listen on all interfaces so the API is reachable from outside the container, and print logs right away
ENV FLASK_RUN_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

EXPOSE 5001
CMD ["python", "app.py"]
