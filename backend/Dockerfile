FROM python:3.11-slim

WORKDIR /app

# 의존성 레이어 분리 — requirements.txt 변경 시에만 pip install 재실행
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사 (코드만 바뀌면 이 레이어부터 재실행)
COPY . .

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
