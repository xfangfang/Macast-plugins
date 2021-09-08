# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Using potplayer as DLNA media renderer
#

# <macast.title>PotPlayer</macast.title>
# <macast.renderer>PotplayerRenderer</macast.title>
# <macast.author>xfangfang</macast.author>
# <macast.desc>PotPlayer support for Macast</macast.desc>
# <macast.version>0.1</macast.version>
# <macast.platform>win32</macast.title>

import os
import time
import threading
import subprocess
from macast import cli, gui
from macast.renderer import Renderer

# POTPLAYER_PATH = '%HOMEPATH%\\Downloads\\PotPlayer64\\PotPlayermini64.exe'
POTPLAYER_PATH = '"C:\\Program Files\\PotPlayer64\\PotPlayermini64.exe"'


class PotplayerRenderer(Renderer):
    def __init__(self):
        super(PotplayerRenderer, self).__init__()
        self.start_position = 0
        self.position_thread_running = True
        self.position_thread = threading.Thread(target=self.position_tick, daemon=True)
        self.position_thread.start()
        # a thread is started here to increase the playback position once per second
        # to simulate that the media is playing.

    def position_tick(self):
        while self.position_thread_running:
            time.sleep(1)
            self.start_position += 1
            sec = self.start_position
            position = '%d:%02d:%02d' % (sec // 3600, (sec % 3600) // 60, sec % 60)
            self.set_state_position(position)

    def set_media_stop(self):
        subprocess.Popen(['taskkill', '/f', '/im', 'PotPlayerMini64.exe']).communicate()
        self.set_state_transport('STOPPED')

    def set_media_url(self, url):
        self.set_media_stop()
        self.start_position = 0
        subprocess.Popen('{} "{}"'.format(POTPLAYER_PATH, url), shell=True)
        self.set_state_transport("PLAYING")

    def stop(self):
        super(PotplayerRenderer, self).stop()
        self.set_media_stop()
        print("PotPlayer stop")

    def start(self):
        super(PotplayerRenderer, self).start()
        print("PotPlayer start")


if __name__ == '__main__':
    gui(PotplayerRenderer())
    # or using cli to disable taskbar menu
    # cli(PotplayerRenderer())
