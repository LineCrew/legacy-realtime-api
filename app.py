# -*- coding: utf8 -*-


from itertools import groupby

import redis
import socketio
import json
from aiohttp import web

from raven import Client
from background_tasks import *
from domain.queue_match_model import QueueMatchModel
from domain.session_model import SessionModel

client = Client('https://aff253b644854f918e1ca419806210fa:af931d78cc524718869f7d7456feae3e@sentry.io/1093983')

sio = socketio.AsyncServer(async_mode='aiohttp')
app = web.Application()
sio.attach(app)

connected_users = []

match_queue_key_name = 'game_match_queue'

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

match_queue_key_name = 'game_match_queue'


# 클라이언트와 소켓 서버 간 연결을 담당한다.
@sio.on('connect', namespace='/sunapp')
async def connect(sid, environ):
    print("connect and pushed to the connection queue", sid)


@sio.on('check_socket_id', namespace='/sunapp')
async def check_socket_id(sid, data):
    await sio.emit(event='notify_socket_id', data={'sid': sid}, room=sid, namespace='/sunapp')


@sio.on('disconnect', namespace='/sunapp')
async def disconnect(sid):
    try:
        data = list(filter(lambda x: x.sid == sid, connected_users))
        if len(data) is not 0:
            connected_users.remove(data)
        await sio.disconnect(sid=sid, namespace='/sunapp')
        print('Client disconnected')
    except Exception as e:
        client.captureMessage(e)
        pass


@sio.on('connection_queue', namespace='/sunapp')
async def push_connection_queue(sid, data):
    user_session = SessionModel(sid, data['userId'])
    connected_users.append(user_session)


@sio.on('request_friend_game_matching', namespace='/sunapp')
async def request_friend_game(sid, data):
    response = dict()
    try:
        friend_entity = next(filter(lambda x: x.user_id == data['friendUserId'], connected_users))
        count = 0

        room_id = str(uuid4())

        response['roomId'] = room_id

        # 친구의 사용자 ID 및 소켓 ID 정보
        response['user1'] = {
            'id': friend_entity.userId,
            'sid': friend_entity.socket_id
        }

        # 나의 사용자 ID 및 소켓 ID 정보
        response['user2'] = {
            'id': data['userId'],
            'sid': sid
        }

        while True:
            await sio.sleep(5)  # 5 초에 한 번 씩 접속 중인 친구에게 게임 요청을 보낸다.
            count += 1

            await sio.emit(event='request_game_match_to_friend', data=response, room=data.socket_id, namespace='/sunapp')

            if count is 11:
                break
    except Exception as e:
        client.captureMessage(e)
        response['status'] = 'NO_FRIEND_IN_CONNECTION_QUEUE'
        await sio.emit(event='request_game_match_to_friend', data=response, room=sid, namespace='/sunapp')
        pass
    pass


# 친구가 게임 플레이 요청을 수락한다.
@sio.on('accept_friend_request', namespace='/sunapp')
async def accept_friend_request(sid, data):
    room_id = data['roomId']

    # 친구와 사용자를 특정 RoomId 로 접속한다.
    sio.enter_room(sid=data['user1']['sid'], room=room_id, namespace='/sunapp')
    sio.enter_room(sid=data['user2']['sid'], room=room_id, namespace='/sunapp')

    response = dict()
    response['user1'] = data['user1']
    response['user2'] = data['user2']
    response['roomId'] = room_id

    await sio.emit(event='created_friend_match', data=response, room=room_id, namespace='/sunapp')


# 일반 게임 매치 플레이 매칭을 요청한다
@sio.on('create_general_game_match', namespace='/sunapp')
async def create_general_game_match(sid, data):
    try:
        queue_session = QueueMatchModel(sid, data['userId'], data['questionaireId'])

        if r.llen(match_queue_key_name) > 0:
            match_queue = r.lrange(name=match_queue_key_name, start=0, end=r.llen(match_queue_key_name))
            converted_queue = []

            for i in match_queue:
                converted_queue.append(json.loads(i))

            duplicated = False

            for j in converted_queue:
                if j['user_id'] == data['userId']:
                    duplicated = True
                    break

            if duplicated:
                await sio.emit(event='match_status', data={'status': 'DUPLICATED_USER_ID'}, room=sid, namespace='/sunapp')
                pass
            elif not duplicated:
                r.rpush('game_match_queue', queue_session.get_session_model())
                pass

        else:
            r.rpush('game_match_queue', queue_session.get_session_model())
            # await sio.emit(event='match_status', data={'status': 'PUSHED_TO_QUEUE'}, room=sid, namespace='/sunapp')
    except Exception as e:
        client.captureMessage(e)


@sio.on('cancel_request_general_match', namespace='/sunapp')
async def cancel_matching(sid, data):
    # TODO -> Redis Queue 에서 데이터 삭제할 것.
    match_queue = r.lrange(name=match_queue_key_name, start=0, end=r.llen(match_queue_key_name))
    converted_queue = []

    for i in match_queue:
        converted_queue.append(json.loads(i))

    try:
        data = next(filter(lambda x: x['socket_id'] == sid, converted_queue))
        redis_data = r.lindex(match_queue_key_name, index=converted_queue.index(data))
        r.lrem(match_queue_key_name, count=converted_queue.index(data), value=redis_data)
        response = dict()
        response['status'] = 'CANCEL_REQUEST_COMPLETE'
        await sio.emit(event='cancel_request_general_match_status', data=response, room=sid, namespace='/sunapp')
    except Exception as e:
        response = dict()
        response['status'] = 'NO_PLAYER_IN_QUEUE'
        client.captureMessage(e)
        await sio.emit(event='cancel_request_general_match_status', data=response, room=sid, namespace='/sunapp')
        pass


# 각 질문지 별, 게임 접속자 수 조회
# {1: 1, 2: 2, 3: 1, 4: 2}
# -> 1번 질문지는 1명, 2번 질문지는 2명, 3명 질문지는 1명, 4명 질문지는 2명이라는 뜻.
@sio.on('get_connection_status', namespace='/sunapp')
async def get_connection_status(sid, data):
    match_queue = r.lrange(name=match_queue_key_name, start=0, end=r.llen(match_queue_key_name))
    converted_queue = []

    for i in match_queue:
        converted_queue.append(json.loads(i))

    response = dict()

    for key, group in groupby(converted_queue, lambda x: x['questionaire_id']):
        result = [x['questionaire_id'] for x in group]
        response[result[0]] = int(len(result))

    await sio.emit(event='connection_status', data=response, room=sid, namespace='/sunapp')


# 게임 플레이에 필요한 문제를 요청한다.
@sio.on('request_question', namespace='/sunapp')
async def get_question_from_api_server(sid, data):
    questions = get_question_data(data['questionaireId'], data['limit'])
    response = {'questions': questions}
    data['questions'] = questions
    # await sio.emit(event='get_match_question', data=response, room=data['roomId'], namespace='/sunapp')
    await sio.emit(event='get_match_question', data=data, room=sid, namespace='/sunapp')


# 플레이를 하고 있는 유저들이 정답을 소켓 서버로 보낸다.
@sio.on('send_answer', namespace='/sunapp')
async def get_answer_from_api_server(sid, data):
    try:
        room_id = data['roomId']

        data_json = {
            'questionItemId': int(data['questionItemId']),
            'answer': int(data['answer']),
            'gameType': data['gameType']
        }

        answer_result = post_answer(data['userId'], data['questionItemId'], json_=data_json)

        response = {
            'user': {
                'id': data['userId'],
                'sid': sid,
                'answer': answer_result
            }
        }

        await sio.emit(event='get_answer_result', data=response, room=room_id, namespace='/sunapp')
    except Exception as e:
        client.captureMessage(e)


# 모든 게임 플레잉 완료 후, 클라이언트는 반드시 이 이벤트를 emit 하여 방을 없앨 것
@sio.on('end_game_playing', namespace='/sunapp')
async def leave_game_room(sid, data):
    await sio.close_room(room=data['roomId'], namespace='/sunapp')


if __name__ == '__main__':
    sio.start_background_task(callee_matching, sio, 5)
    web.run_app(app, port=8000)
