# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Using IINA as DLNA media renderer
#
# Macast Metadata
# <macast.title>IINA Renderer</macast.title>
# <macast.renderer>IINARenderer</macast.renderer>
# <macast.platform>darwin</macast.platform>
# <macast.version>0.1</macast.version>
# <macast.author>xfangfang</macast.author>
# <macast.desc>IINA support for Macast</macast.desc>


import os
import time
import threading
import subprocess
from macast import cli
from macast.renderer import Renderer

IINA_PATH = '/Applications/IINA.app/Contents/MacOS/iina-cli'


class IINARenderer(Renderer):

    def __init__(self):
        super(IINARenderer, self).__init__()
        self.start_position = 0
        self.position_thread_running = True
        self.position_thread = threading.Thread(target=self.position_tick, daemon=True)
        self.position_thread.start()
        self.iina = None

    def position_tick(self):
        while self.position_thread_running:
            time.sleep(1)
            self.start_position += 1
            sec = self.start_position
            position = '%d:%02d:%02d' % (sec // 3600, (sec % 3600) // 60, sec % 60)
            self.set_state_position(position)

    def set_media_stop(self):
        try:
            if self.iina is not None:
                self.iina.terminate()
            os.waitpid(-1, 1)
        except Exception as e:
            print(str(e))
        self.set_state_transport('STOPPED')

    def set_media_url(self, url):
        self.set_media_stop()
        self.start_position = 0
        self.iina = subprocess.Popen([IINA_PATH, '--keep-running', '--no-stdin', url])
        self.set_state_transport("PLAYING")

    def stop(self):
        super(IINARenderer, self).stop()
        self.set_media_stop()
        print("IINA stop")

    def start(self):
        super(IINARenderer, self).start()
        print("IINA start")


if __name__ == '__main__':
    cli(IINARenderer())
