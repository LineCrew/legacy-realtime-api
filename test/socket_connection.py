from socketIO_client import SocketIO, BaseNamespace

class Namespace(BaseNamespace):
    def on_aaa_response(self, *args):
        print('on_aaa_response', args)

    def on_reply(*args):
        print(args)

socketIO = SocketIO('127.0.0.1', 8000)
chat_namespace = socketIO.define(Namespace, '/chat')
chat_namespace.emit('chat_message', 'data')
chat_namespace.on('reply', Namespace.on_reply())
socketIO.wait(seconds=10)