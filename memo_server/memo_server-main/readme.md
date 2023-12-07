# Memo 서버

이 프로젝트는 사용자의 메모를 저장하고 관리하는 간단한 Flask 웹 애플리케이션입니다.

## 실행 방법

1. Python이 설치되어 있어야 합니다.
2. 프로젝트 폴더로 이동합니다.
3. 의존성을 설치합니다.

    ```bash
    pip install -r requirements.txt
    ```

4. Redis와 MongoDB가 설치되어 있어야 합니다.
5. Redis 서버를 실행합니다.
6. MongoDB 서버를 실행합니다.
7. 아래 명령어로 서버를 실행합니다.

    ```bash
    python memo.py
    ```

8. 브라우저에서 `http://localhost:8000`에 접속하여 메모장을 이용할 수 있습니다.

## 엔드포인트

### GET `/health`

- 서버의 상태를 확인하는 엔드포인트입니다.
- HTTP status code 200을 반환합니다.

### GET `/memo`

- 사용자의 메모를 가져오는 엔드포인트입니다.
- 로그인한 사용자만 접근할 수 있습니다.

### POST `/memo`

- 새로운 메모를 작성하는 엔드포인트입니다.
- 요청 바디에 JSON 형식으로 `text` 필드를 포함해야 합니다.

## 사용 기술

- Flask
- Redis
- MongoDB
- HTML, CSS, JavaScript (jQuery)

