# -*- coding: utf8 -*-

import json
import time
from itertools import groupby
from random import choice
from uuid import uuid4
import requests as rq
from raven import Client

import redis
from celery import Celery

base_server_url = 'http://52.230.5.59:3000'

client = Client('https://aff253b644854f918e1ca419806210fa:af931d78cc524718869f7d7456feae3e@sentry.io/1093983')

# Redis Configuration
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# Celery Configuration
app = Celery('matching_tasks', backend='redis://localhost:6379/0', broker='redis://localhost:6379/0')
app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=100,
    CELERY_TASK_SERIALIZER='json',
    CELERY_RESULT_SERIALIZER='json',
    CELERY_ENABLE_UTC=True
)

match_queue_key_name = 'game_match_queue'


class BaseTask(app.Task):
    abstract = True

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        client.captureException(exc)
        super(BaseTask, self).on_retry(exc, task_id, args, kwargs, einfo)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        client.captureException(exc)
        super(BaseTask, self).on_failure(exc, task_id, args, kwargs, einfo)


def get_question_data(id, limit=5):
    get_question_rest_api_url = '{}/api/v1/questionaire/{}'.format(base_server_url, id)
    r = rq.get(get_question_rest_api_url)
    print(r.status_code)
    print(r.json())

    return r.json()['message']


def get_players_info(me, opponent):
    get_players_info_rest_api_url = '{}/api/v1/user/getPlayers?me={}&opponent={}'.format(base_server_url, me, opponent)

    r = rq.get(url=get_players_info_rest_api_url)
    print(r.status_code)
    print(r.json())

    return r.json()


def get_players(queue):
    player_1 = choice(queue)
    player_2 = choice(queue)

    while player_1['user_id'] is player_2['user_id']:
        player_1 = choice(queue)
        player_2 = choice(queue)

    return player_1, player_2, queue.index(player_1), queue.index(player_2)


@app.task(
    name='tasks.matching_task.matching_task.game_matching_task',
    max_retries=3,
    soft_time_limit=5,
    base=BaseTask
)
def game_matching_task():
    response = dict()
    response['results'] = []

    if r.llen(match_queue_key_name) > 1:
        match_queue = r.lrange(name=match_queue_key_name, start=0, end=r.llen(match_queue_key_name))
        converted_queue = []

        for i in match_queue:
            converted_queue.append(json.loads(i))

        for k, _ in groupby(converted_queue, lambda x: (x['questionaire_id'])):
            queue_by_questionaire_id = list(_)

            # Key 가 QuestionaireId 인 리스트의 길이가 2 * n 일 때, For 문으로 해당 2 * n 만큼의 매칭 요청을 수행하게 만들 필요가 있긴 하다.
            try:
                if len(queue_by_questionaire_id) > 1:
                    # SocketId, UserId, QuestionaireId
                    player_1, player_2, player_1_index, player_2_index = get_players(queue_by_questionaire_id)

                    redis_data = r.lindex(match_queue_key_name, index=player_1_index)
                    redis_data_ = r.lindex(match_queue_key_name, index=player_2_index)

                    r.lrem(match_queue_key_name, count=player_1_index, value=redis_data)
                    r.lrem(match_queue_key_name, count=player_2_index, value=redis_data_)

                    room_id = str(uuid4())

                    print('Room Id -> {0}'.format(room_id))

                    players_info = get_players_info(player_1['user_id'], player_2['user_id'])['message']

                    result_message = dict()
                    result_message['user1'] = players_info[0]
                    result_message['user2'] = players_info[1]
                    result_message['user1Sid'] = player_1['socket_id']
                    result_message['user2Sid'] = player_2['socket_id']
                    result_message['roomId'] = room_id
                    # result_message['questionaireId'] = k
                    result_message['questions'] = get_question_data(k)

                    response['results'].append(result_message)

            except Exception as e:
                client.captureMessage(e)
                return "Error Exception -> " + str(e)
                pass
    else:
        response['status'] = 'NO_PLAYERS_IN_QUEUE'
        return response

    return response
