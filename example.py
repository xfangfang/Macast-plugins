# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Macast Dummy media renderer
#
# Macast Metadata
# <macast.title>Dummy Renderer</macast.title>
# <macast.renderer>DummyRenderer</macast.renderer>
# <macast.platform>darwin,linux,win32</macast.platform>
# <macast.version>0.1</macast.version>
# <macast.author>xfangfang</macast.author>
# <macast.desc>Macast Dummy media renderer</macast.desc>


import os
import time
import threading
import cherrypy
import subprocess
from macast import cli
from macast.renderer import Renderer


class DummyRenderer(Renderer):

    def __init__(self):
        super(DummyRenderer, self).__init__()
        self.start_position = 0
        self.position_thread_running = True
        self.position_thread = threading.Thread(target=self.position_tick, daemon=True)
        self.position_thread.start()

    def position_tick(self):
        while self.position_thread_running:
            time.sleep(1)
            self.start_position += 1
            sec = self.start_position
            position = '%d:%02d:%02d' % (sec // 3600, (sec % 3600) // 60, sec % 60)
            self.set_state_position(position)

    def set_media_stop(self):
        self.set_state_transport('STOPPED')
        cherrypy.engine.publish('renderer_av_stop')

    def set_media_url(self, url):
        self.set_media_stop()
        self.start_position = 0
        print(url)
        self.set_state_transport("PLAYING")
        cherrypy.engine.publish('renderer_av_uri', url)

    def stop(self):
        super(DummyRenderer, self).stop()
        self.set_media_stop()
        print("Dummy stop")
        cherrypy.engine.publish('renderer_av_stop')

    def start(self):
        super(DummyRenderer, self).start()
        print("Dummy start")


if __name__ == '__main__':
    cli(DummyRenderer())
