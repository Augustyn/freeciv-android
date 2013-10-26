from tornado import web, websocket, ioloop, httpserver
import subprocess
import threading
import os

PORT = int(os.environ.get('FC_PORT', 8002))

class WSHandler(websocket.WebSocketHandler):
    handlers = []

    def open(self):
        self.handlers.append(self)

    def on_message(self, message):
        self.ctrl_file.write(message + '\n')

    def on_close(self):
        pass

    @classmethod
    def broadcast(self, data):
        for handler in self.handlers:
            if handler.ws_connection:
                handler.write_message(data)

class MainHandler(web.RequestHandler):
    def get(self):
        self.redirect('ws.html')

class MyStaticFileHandler(web.RequestHandler):
    def initialize(self, path):
        self._path = path

    def get(self, name):
        if name in os.listdir(self._path):
            self.write(open(self._path + '/' + name).read())
        else:
            raise Exception('not found')

def stream_data(fdin):
    f = os.fdopen(fdin, 'r', 1)

    print 'read stream'
    while True:
        line = f.readline()
        if not line: break
        ioloop.IOLoop.instance().add_callback(WSHandler.broadcast, line)
    print 'stream finished'

if __name__ == u"__main__":
    streamin, streamout = os.pipe()
    ctrlin, ctrlout = os.pipe()
    inferior = subprocess.Popen(['bash', './main.sh',
                                 'freeciv.main',
                                 '-f:stream.enable', '-f:stream.fd=%d' % streamout,
                                 '-f:ctrl.enable', '-f:ctrl.fd=%d' % ctrlin,
                                 '-f:ui.enable_anim=false', '-f:app.debug=false',
                                 '-f:ui.redraw_fps_limit=3',
                                 '-f:ui.fps_limit=15',
                                 '-f:ui.offscreen',
                                 '-f:app.desktop_size=1280,800',
                                 '-f:app.map_tiles'])
    os.close(streamout)
    os.close(ctrlin)
    WSHandler.ctrl_file = os.fdopen(ctrlout, 'w', 0)
    threading.Thread(target=stream_data, args=[streamin]).start()

    application = web.Application([
        (r'/', MainHandler),
        (r'/ws', WSHandler),
        (r'/(.*)', MyStaticFileHandler, {'path': os.path.dirname(__file__)}),
    ])

    http_server = httpserver.HTTPServer(application)
    http_server.listen(PORT)
    ioloop.IOLoop.instance().start()
