import socket
import select
import json
from concurrent.futures import ThreadPoolExecutor


HOST = '127.0.0.1'
PORT = 19150
MAX_WORKERS = 10  # 원하는 worker thread 개수


clients = {}
rooms = {}
room_number_counter = 0  # 방 번호 카운터.


def send_message(client_socket, message):
    serialized = json.dumps(message).encode('utf-8')
    to_send = len(serialized)
    to_send_big_endian = int.to_bytes(to_send, byteorder='big', length=2)
    serialized = to_send_big_endian + serialized

    offset = 0
    while offset < len(serialized):
        num_sent = client_socket.send(serialized[offset:])
        if num_sent <= 0:
            raise RuntimeError('Send failed')
        offset += num_sent


def receive_message(client_socket):
    try:
        length_bytes = client_socket.recv(2)  # 처음 2바이트를 받아옴
        length = int.from_bytes(length_bytes, byteorder='big')  # 바이트를 정수로 변환하여 메시지 길이 파악
        message = b''
        
        while len(message) < length:
            chunk = client_socket.recv(length - len(message))  # 남은 길이만큼 데이터를 추가로 받음
            if not chunk:
                raise RuntimeError("Socket connection broken")
            message += chunk
        
        return json.loads(message.decode('utf-8'))  # JSON 형식의 메시지로 가정
    except Exception as e:
        print(f"Error receiving message: {e}")
        return None


def handle_client(server_socket, client_socket, client_address):
    print(f"New connection from {client_address}")
    clients[client_socket] = {
        'address': client_address,
        'room': None,
        'name': f"{client_address[0]}_{client_address[1]}"  # 기본 이름 설정
    }

    while True:
        try:
            message = receive_message(client_socket)
            if message['type'].startswith('CS'):
                command = message['type']
                handle_command(server_socket, client_socket, command, message)

        except ConnectionResetError:
            print(f"Connection with {client_address} closed.")
            del clients[client_socket]
            break

    client_socket.close()


def handle_command(server_socket, client_socket, command, message):
    if command == 'CSJoinRoom':
        join_room(client_socket, message)
    elif command == 'CSCreateRoom':
        create_room(client_socket, message)
    elif command == 'CSName':
        change_name(client_socket, message)
    elif command == 'CSRooms':
        show_rooms(client_socket)
    elif command == 'CSLeaveRoom':
        leave_room(client_socket)
    elif command == 'CSShutdown':
        shutdown_server(server_socket)
    elif command == 'CSChat' :
        chat_room(client_socket, message)
        

def chat_room(client_socket, message):
    text = message['text']
    current_room = clients[client_socket]['room']

    if not current_room:
        error_message = "현재 대화방에 들어가 있지 않습니다."
        send_message(client_socket, {"type": "SCSystemMessage", "text": error_message})
    else:
        if text:
            client_message = {
                'member': clients[client_socket].get('name', None),
                'type': 'SCChat', 
                'text': text
            }

            # 이 부분 수정
            send_to_room_except_sender(client_socket, clients[client_socket]['room'], client_message)
        else:
            error_msg = "No text"
            send_message(client_socket, {"type": "SCSystemMessage", "text": error_msg})

def shutdown_server(server_socket):
    message = {
                "type" : "SCSystemMessage",
                "text": "채팅 서버가 닫힙니다."}
    for client_socket in clients:
        send_message(client_socket, message)
        client_socket.close()

    server_socket.close()
    exit()

def leave_room(client_socket):
    current_room = clients[client_socket]['room']

    if not current_room:
        message = {
            "type": "SCSystemMessage",
            "text": "현재 대화방에 들어가 있지 않습니다."
        }
        send_message(client_socket, message)
        return

    room_members = rooms[current_room]['members']
    room_name = rooms[current_room]['title']

    clients[client_socket]['room'] = None

    remaining_clients_in_room = [member_info for member_info in room_members if list(member_info.keys())[0] != client_socket]

    if remaining_clients_in_room:
        rooms[current_room]['members'] = remaining_clients_in_room
        message = {
            "type": "SCSystemMessage",
            "text": f"[{clients[client_socket]['name']}] 님이 퇴장했습니다."
        }
        for member_info in remaining_clients_in_room:    #대화방에 있는 다른 멤버들에게 보내지는 메시지
            member_socket = list(member_info.keys())[0]
            send_message(member_socket, message)
        
        message = {
            "type" : "SCSystemMessage",
            "text": f"[{room_name}] 대화 방에서 퇴장했습니다."
        }
        send_message(client_socket, message)
    else:
        del rooms[current_room]  # 방 삭제
        message = {
            "type": "SCSystemMessage",
            "text": f"[{room_name}] 대화 방에서 퇴장했습니다."
        }
        send_message(client_socket, message)

    
def change_name(client_socket, message):
    new_name = message['name']
    old_name = clients[client_socket].get('name', None)
    
    if new_name:
        clients[client_socket]['name'] = new_name
        
        if old_name:
            send_message = {
                'type' : 'SCSystemMessage', 
                'text' : f" 이름이 {new_name}으로 변경되었습니다."
            }
            send_to_room(client_socket, clients[client_socket]['room'], send_message)

    else:
        error_msg = "Name setting failed. Please provide a valid name."
        send_message(client_socket, {"type" : "SCSystemMessage","text": error_msg})

def send_to_room_except_sender(sender_socket, room_name, message):
    if room_name in rooms:
        room_members = rooms[room_name]['members']
        for client in room_members:
            sock = list(client.keys())[0]
            if sock != sender_socket:
                send_message(sock, message)
    else: 
        send_message(sender_socket, message)


def send_to_room(sender_socket, room_name, message):
    if room_name in rooms:
        room_members = rooms[room_name]['members']
        for client in room_members:
            sock = list(client.keys())[0]
            send_message(sock, message)
    else: 
        send_message(sender_socket, message)


def create_room(client_socket, message):
    args = message['title']
    if clients[client_socket]['room']:
        message = {
            'type': 'SCSystemMessage',
            "text": " 대화 방에 있을 때는 방을 개설할 수 없습니다."
        }
        send_message(client_socket, message)
        return
    
    if args:
        global room_number_counter  # 전역 변수로 방 번호 카운터를 활용합니다.
        room_name = args
        room_number_counter += 1  # 방 번호를 증가시킵니다.
        room_id = f"{room_number_counter}"  # 방 번호로 ID를 설정합니다.
        
        rooms[room_id] = {
            'members': [{client_socket: clients[client_socket]}],
            'title': room_name
        }
        
        clients[client_socket]['room'] = room_id
        message = {
            'type': 'SCSystemMessage',
            'text': f" 방번호 [{room_number_counter}] 방제 [{room_name}] 방에 입장했습니다."
        }
        send_message(client_socket, message)
    else:
        message = {
            'type': 'SCSystemMessage',
            'text': "방제를 입력해주세요."
        }
        send_message(client_socket, message)

        

def join_room(client_socket, args):
    room_number = args['roomId']
    
    if clients[client_socket]['room']:
        message = {
            'type': 'SCSystemMessage',
            'text': "대화 방에 있을 때는 다른 방에 들어갈 수 없습니다."
        }
        send_message(client_socket, message)
        return
    
    if room_number:
        matching_rooms = [room for room in rooms.keys() if room.startswith(f"{room_number}")]
        
        if not matching_rooms:
            message = {
                'type': 'SCSystemMessage',
                'text': "대화방이 존재하지 않습니다."
            }
            send_message(client_socket, message)
            return
        
        room_id = matching_rooms[0]
        clients[client_socket]['room'] = room_id
        room_name = rooms[room_id]['title']
        
        # 클라이언트 정보 추가 - 수정된 부분
        rooms[room_id]['members'].append({client_socket: clients[client_socket]})
        
        message = {
            'type': 'SCSystemMessage',
            'text': f"방제 [{room_name}] 방에 입장했습니다."
        }
        send_message(client_socket, message)
        
        for member in rooms[room_id]['members']:
            sock = list(member.keys())[0]
            if sock != client_socket:
                message = {
                    'type': 'SCSystemMessage',
                    'text': f"[{clients[client_socket]['name']}] 님이 입장했습니다."
                }
                send_message(sock, message)
    else:
        message = {
            'type': 'SCSystemMessage',
            'text': "방 번호를 입력해주세요."
        }
        send_message(client_socket, message)

def show_rooms(client_socket):
    if not rooms:
        message = {
            'type': 'SCRoomsResult',
            'rooms': []
        }
    else:
        room_list = []
        for room_id, room_data in rooms.items():
            members_names = []
            for member_info in room_data['members']:
                member_socket = list(member_info.keys())[0]
                if member_socket in clients and 'name' in clients[member_socket]:
                    member_name = clients[member_socket]['name']
                    members_names.append(member_name)
            room_info = {
                'roomId': room_id,  # 방 번호를 출력하는 부분 수정
                'title': room_data['title'],
                'members': members_names
            }
            room_list.append(room_info)
        
        message = {
            'type': 'SCRoomsResult',
            'rooms': room_list
        }

    send_message(client_socket, message)


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    inputs = [server_socket]

    print(f"Server listening on {HOST}:{PORT}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            readable, _, _ = select.select(inputs, [], [])
            for sock in readable:
                if sock == server_socket:
                    client_socket, client_address = server_socket.accept()
                    executor.submit(handle_client, server_socket, client_socket, client_address)
                else:
                    pass  # 추가 작업 필요시 처리


if __name__ == "__main__":
    main()