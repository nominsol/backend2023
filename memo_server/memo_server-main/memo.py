from http import HTTPStatus
import random
import requests
import json
import urllib
import redis

from flask import abort, Flask, make_response, render_template, Response, redirect, request
from pymongo import MongoClient


app = Flask(__name__)

naver_client_id = 'OsICvQBx1wTTGo6MQIY9'
naver_client_secret = 'u10esEZo3t'
naver_redirect_uri = 'http://localhost:8000/auth'
   
# name은 redis에 저장하고 가져옴 (키는 client ID)
rdb = redis.Redis(host="localhost", port=6379, db=0)

# 메모는 mongo db에 저장하고 가져옴 (키는 client ID)
client = MongoClient('mongodb://localhost:27017/')
db = client['memo_database']  # 데이터베이스 선택
collection = db['memos']  # 콜렉션 선택

@app.route('/')
def home():
    userId = request.cookies.get('userId', default=None)
    name = None

    if userId:
        name_bytes = rdb.get(userId)
        if name_bytes:
            name = name_bytes.decode('utf-8')  # 바이트를 문자열로 디코딩

    return render_template('index.html', name=name)


@app.route('/login')
def onLogin():
    params = {
        'response_type': 'code',
        'client_id': naver_client_id,
        'redirect_uri': naver_redirect_uri,
        'state': random.randint(0, 10000)
    }
    urlencoded = urllib.parse.urlencode(params)
    url = f'https://nid.naver.com/oauth2.0/authorize?{urlencoded}'
    return redirect(url)


@app.route('/auth')
def onOAuthAuthorizationCodeRedirected():
    params = request.args.to_dict()
    
    authorization_code = params.get("code")
    state = params.get("state")

    params = {
        'grant_type': 'authorization_code',
        'client_id': naver_client_id,
        'client_secret': naver_client_secret,
        'code': authorization_code
    }
    urlencoded = urllib.parse.urlencode(params)
    url = f'https://nid.naver.com/oauth2.0/token?{urlencoded}'
    
    accessToken_request = requests.get(url)
    json_token = accessToken_request.json()
    accessToken = json_token.get("access_token")

    header = {"Authorization": f"Bearer {accessToken}"}
    url = "https://openapi.naver.com/v1/nid/me"
    userInfo_request = requests.get(url, headers=header)

    if userInfo_request.status_code == 200:
        user_info = userInfo_request.json().get('response')
        user_id = user_info.get("id")
        user_name = user_info.get("name")
        rdb.set(user_id, user_name)

        response = redirect('/')
        response.set_cookie('userId', user_id)
        return response
    else:
        print(f"Error Code: {userInfo_request.status_code}")
        return "Authentication failed"


@app.route('/memo', methods=['GET'])
def get_memos():
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    document = collection.find_one({'userId': userId})
    if document:
        result = document.get('memos', [])

        return {'memos': result}
    else:
        return {'memos': []}


@app.route('/memo', methods=['POST'])
def post_new_memo():
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # 데이터가 JSON 형식이 아닌 경우 처리
    if not request.is_json:
        abort(HTTPStatus.BAD_REQUEST)

    data = request.get_json()  # JSON 형식의 데이터를 가져옴
    content = {"text": data.get('text')}  # 'text' 필드를 새로운 딕셔너리 형태로 저장

    # 데이터를 UTF-8로 인코딩하여 저장하지 않고 그대로 저장
    collection.update_one(
        {'userId': userId},
        {'$push': {'memos': content}},
        upsert=True  # 문서가 존재하지 않으면 새로 생성
    )

    return '', HTTPStatus.OK



@app.route('/health', methods=['GET'])
def get_health():
    return '', HTTPStatus.OK

    


if __name__ == '__main__':
    app.run('0.0.0.0', port=8000, debug=True)
