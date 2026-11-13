# 복복복 공개 테스트용 컨테이너 (Render 외의 서비스에 올릴 때 사용)
# 빌드: docker build -t bokbok .
# 실행: docker run -p 8000:8000 bokbok   →  http://localhost:8000
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BOKBOK_MULTI=1 \
    TZ=Asia/Seoul \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 체험 기록은 컨테이너 안 var/ 에 저장되며, 컨테이너가 다시 시작되면 지워집니다.
RUN useradd --create-home bokbok && mkdir -p var && chown -R bokbok var
USER bokbok

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips '*'"]
