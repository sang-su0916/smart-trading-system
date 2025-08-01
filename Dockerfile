# Docker 배포용 파일
FROM python:3.9-slim

WORKDIR /app

# 시스템 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements_cloud.txt .
RUN pip install --no-cache-dir -r requirements_cloud.txt

# 애플리케이션 파일 복사
COPY streamlit_app.py .
COPY src/ ./src/
COPY config/ ./config/

# 포트 노출
EXPOSE 8501

# Streamlit 실행
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]