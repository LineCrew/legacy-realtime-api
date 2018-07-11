# -*- coding: utf8 -*-

import requests as rq
from random import choice
from uuid import uuid4
import asyncio
import json

import tasks.matching_task

from raven import Client

base_server_url = 'http://52.230.5.59:3000'
client = Client('https://aff253b644854f918e1ca419806210fa:af931d78cc524718869f7d7456feae3e@sentry.io/1093983')


# def get_question_data(id, limit=5):
#     get_question_rest_api_url = '{}/api/v1/questionaire/{}'.format(base_server_url, id)
#     r = rq.get(get_question_rest_api_url)
#     print(r.status_code)
#     print(r.json())
#
#     return r.json()['message']


def post_answer(user_id, question_item_id, json_={}):
    post_answer_rest_api_url = '{}/api/v1/questionaire/{}/{}/answers'.format(base_server_url, user_id, question_item_id)
    print(post_answer_rest_api_url)

    print(json_)

    r = rq.post(url=post_answer_rest_api_url, json=json_)

    return r.json()['message']


def get_user_info_by_id(me, opponent):
    get_players_info_rest_api_url = '{}/api/v1/user/getPlayers?me={}&opponent={}'.format(base_server_url, me, opponent)

    r = rq.get(url=get_players_info_rest_api_url)
    print(r.status_code)
    print(r.json())

    return r.json()


async def callee_task(sio, frequency=5):
    try:
        while True:
            await sio.sleep(frequency)

            # print('Matching Celery Worker is always running for you ... :)')

            task = tasks.matching_task.game_matching_task.apply_async(())

            # print('Celery Task Id -> {0}'.format(task))

            task_response = task.get()

            # print('Celery Task Response -> {0}'.format(task_response))

            if 'error' in task_response:
                socket_ids = task_response['socket_ids']
                for sid in socket_ids:
                    await sio.emit(event='match_status', data=task_response['error'], room=sid, namespace='/sunapp')

            if task_response is not None:
                for i in task_response['results']:
                    response = dict()
                    sio.enter_room(sid=i['user1Sid'], room=i['roomId'], namespace='/sunapp')
                    sio.enter_room(sid=i['user2Sid'], room=i['roomId'], namespace='/sunapp')

                    response['user1'] = i['user1']
                    response['user2'] = i['user2']
                    response['roomId'] = i['roomId']
                    # response['questionaireId'] = i['questionaireId']
                    # response['questionaire'] = get_question_data(i['questionaireId'])
                    response['question'] = i['questions']

                    await sio.emit(event='match_status', data=response, room=i['roomId'], namespace='/sunapp')

    except Exception as e:
        client.captureException()
        client.captureMessage('Background Error' + str(e))
        await sio.emit(event='match_status', data=e, room=sio, namespace='/sunapp')


async def callee_matching(sio, frequency=5):
    task_ = [callee_task(sio, frequency)]
    await asyncio.wait(task_)
