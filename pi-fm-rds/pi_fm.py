# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Using pi_fm_rds as DLNA media renderer
# https://github.com/ChristopheJacquet/PiFmRds
#
# Macast Metadata
# <macast.title>PIFMRDS Renderer</macast.title>
# <macast.renderer>PIFMRenderer</macast.renderer>
# <macast.platform>linux</macast.platform>
# <macast.version>0.2</macast.version>
# <macast.host_version>0.7</macast.host_version>
# <macast.author>xfangfang</macast.author>
# <macast.desc>PIFMRDS support for Macast. Only for raspberry pi, visit the plugin repository for more information.</macast.desc>

import os
import time
import threading
import subprocess
from macast import cli
from macast.renderer import Renderer


class PIFMRenderer(Renderer):
    def __init__(self):
        super(PIFMRenderer, self).__init__()
        self.start_position = 0
        self.position_thread_running = True
        self.position_thread = threading.Thread(target=self.position_tick, daemon=True)
        self.position_thread.start()
        self.sox = None
        self.fm = subprocess.Popen(['sudo', 'pi_fm_rds', '-freq', '108', '-audio', '-'],
                                   stdin=subprocess.PIPE,
                                   bufsize=1024)

    def position_tick(self):
        while self.position_thread_running:
            time.sleep(1)
            self.start_position += 1
            sec = self.start_position
            position = '%d:%02d:%02d' % (sec // 3600, (sec % 3600) // 60, sec % 60)
            self.set_state_position(position)

    def set_media_stop(self):
        if self.sox is not None:
            self.sox.terminate()
        os.waitpid(-1, 1)
        self.set_state_transport('STOPPED')

    def set_media_url(self, data, start=0):
        self.start_position = 0
        self.sox = subprocess.Popen(['sox', '-t', 'mp3', data, '-t', 'wav', '-'],
                                    stdout=self.fm.stdin)
        self.set_state_transport("PLAYING")

    def stop(self):
        super(PIFMRenderer, self).stop()
        os._exit()
        # if self.sox is not None:
        #     self.sox.terminate()
        # kill = subprocess.Popen(['sudo', 'killall', 'pi_fm_rds'])
        # kill.communicate()
        # os.waitpid(-1, 1)


if __name__ == '__main__':
    cli(PIFMRenderer())
