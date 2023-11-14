from flask import Flask, request, jsonify

app = Flask(__name__)

def calculate(arg1, op, arg2):
    if op == '+':
        return arg1 + arg2
    elif op == '-':
        return arg1 - arg2
    elif op == '*':
        return arg1 * arg2
    else:
        return None

@app.route('/<int:arg1>/<op>/<int:arg2>', methods=['GET'])
def calculate_get(arg1, op, arg2):
    result = calculate(arg1, op, arg2)
    if result is None:
        return '지원하지 않는 연산자 입니다', 400
    else:
        return str(result), 200

@app.route('/', methods=['POST'])
def calculate_post():
    content = request.get_json()
    arg1 = content.get('arg1')
    op = content.get('op')
    arg2 = content.get('arg2')

    if None in (arg1, op, arg2):
        return '데이터 누락이 있습니다', 400

    result = calculate(arg1, op, arg2)
    if result is None:
        return 'Unsupported operation', 400

    return str(result), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=19150)
