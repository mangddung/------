# 베이스 이미지
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요 패키지 설치
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 코드 복사
COPY . .

# ffmpeg 설치
RUN apt-get update && apt-get install -y ffmpeg

# 컨테이너가 시작할 때 실행될 명령어
CMD ["python", "run.py"]
