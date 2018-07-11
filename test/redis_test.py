# -*- coding: utf-8 -*-

import redis

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

r.rpush('name', 'hello')
# r.rpush('name', 'world')
# r.rpush('name', 'judepark')

ran = r.llen('name')
print(ran)
print(r.lrange('name', 0, ran))
#
print(r.lrem('name', count=0, value='hello'))

ran = r.llen('name')
print(ran)
print(r.lrange('name', 0, ran))

# print(list(r.smembers("name"))[0])
# print(list(r.smembers("name"))[0] == 'He')
# print(type(r.smembers("name")))ndex

r.hmset()