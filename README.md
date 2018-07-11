### 1. Introduction

Author : Jude Park

Email: park.jude.96@gmail.com , judepark@kookmin.ac.kr 

실시간 P2P 퀴즈 게임을 위한 백엔드 시스템입니다. Celery, Redis, Socket.io, Python 3.6+ 가 사용되었습니다.

### 2. How It Runs

동작 방식은 굉장히 심플합니다.

Socket.io 에서는 **create_general_game_match** 라는 Event 로 Redis 에 [rpush](https://redis.io/commands/rpush) 라는 명령어를 사용하여 게임 매치 정보를 저장합니다. 

이를 바탕으로 Celery 의 정의된 **tasks.matching_task.matching_task.game_matching_task** 가 5초에 한 번씩 실행됩니다. 

즉, 5초 동안 게임 매치 정보가 Redis 에 쌓이도록 하고, 이를 바탕으로 Celery 를 이용하여 한 번에 매칭을 하도록 한 것 입니다. 

이는 과도한 트래픽 집중으로 인한 서버의 부하를 방지하며 느려질 여지는 존재하지만 확실하게 매칭을 할 수 있도록 의도한 것입니다.

5초 동안 쌓인 매치 정보를 바탕으로 한 Task 당, 매칭할 수 있는 Capacity 는 아래와 같습니다. 

![](http://latex.codecogs.com/gif.latex?q%20%3D%20QuestionaireLength%2C%20p%3DPlayersInQueue%2C%20i%3D2)

라고 가정할 때 기존의 방식은 아래와 같습니다.

![](http://latex.codecogs.com/gif.latex?Capacity%20%3D%20q%2C%20MatchedPeople%3D%20q*i)

이를 다음과 같이 개선할 수 있습니다.

![](http://latex.codecogs.com/gif.latex?Capacity%20%3D%20q%20*%20%28q_p%20/%202%29%2C%20MatchedPeople%20%3D%20Capacity%20*%202)



### 3. Getting Started

먼저, 해당 시스템의 동작을 위해서 환경을 구축할 필요가 있습니다. 각자의 virtualenv 가 있고, Python 3.6+ 이며 Redis 가 설치되어있다는 가정 하에 본 글을 진행하겠습니다.

```shell
pip install -r requirements.txt
```

위의 명령어를 통하여 시스템 동작에 필요한 모든 파이썬 패키지를 설치하였습니다.

다음으로는 Redis 를 실행시켜야합니다.

```shell
redis-server
```

위의 명령어로 Redis 가 실행되며 터미널을 차지하는게 싫으시다면 프로세스에 등록해놓는 것도 하나의 방법입니다.

이제 실시간 P2P 퀴즈 게임에서 가장 중요한 부분인 **플레이어 매칭을 위한 Celery Worker 의 동작 방법**을 진행하겠습니다.

Worker 를 실행시키기 위해서는 Worker 가 존재하는 폴더로 들어가야합니다.

```shell
cd ./tasks
celery -A matching_task worker -P gevent --autoscale=1000,4 --loglevel=info
```

matching_task 를 Celery Worker 로서 실행시키는 명령어입니다. Arugments 를 설명드리자면 Gevent 를 바탕으로 Concurrency 의 Min ~ Max 가 4 ~ 1000 사이이며, Worker 의 Task 수행에 따라 자동으로 Scailling 됨을 의미합니다.

위의 과정을 마쳤다면 Socket.io 서버를 실행시킵니다.

```shell
python app.py

======== Running on http://0.0.0.0:4000 ========
```

성공적으로 실행되었다면 4000 번 포트에서 서버가 돌고 있다는 메시지가 출력됩니다.

만약, Celery 를 모니터링하고 싶으시다면 tasks 폴더에서 다음과 같이 해주시면 됩니다.

```shell
pip install flower // globally
celery -A matching_task flower --port=5555
```

flower 를 설치하고 localhost:5555 로 가시면 모니터링 대시보드가 렌더링됩니다.

감사합니다.