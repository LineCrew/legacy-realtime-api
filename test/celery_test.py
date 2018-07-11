import tasks.matching_task
import redis
from domain.queue_match_model import QueueMatchModel

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)


# for i in range(100):
#     result = tasks.matching_task.add.delay(1, i)
#     print(result.get())

data = {
    'socket_id': 1,
    'user_id': 1,
    'questionaire_id': 1
}

data_ = {
    'socket_id': 2,
    'user_id': 2,
    'questionaire_id': 1
}

r.lpush('game_match_queue', QueueMatchModel(1, 1, 1).get_session_model())
r.lpush('game_match_queue', QueueMatchModel(2, 2, 1).get_session_model())
r.lpush('game_match_queue', QueueMatchModel(3, 3, 1).get_session_model())
r.lpush('game_match_queue', QueueMatchModel(4, 4, 1).get_session_model())

tasks.matching_task.game_matching_task.delay()
