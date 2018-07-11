# Author : Jude Park, park.jude.96@gmail.com
# Description : 게임 플레이하기 위한 대기열에 사용자 정보를 저장함.

import json


class SessionModel(object):
    def __init__(self, socket_id, user_id):
        self.socket_id = socket_id
        self.user_id = user_id

    def get_session_model(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def convert_from_string_to_json(self):
        return json.loads(self.get_session_model())

