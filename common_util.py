import hashlib


# 나와 상대방의 정보를 해싱
def unique_room_id_generator(player1, player2):
    secret = str(player1) + str(player2)
    md5 = hashlib.md5()
    md5.update(secret)
    result = md5.hexdigest()

    return result