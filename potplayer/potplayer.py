# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Using potplayer as DLNA media renderer
#
# Macast Metadata
# <macast.title>PotPlayer Renderer</macast.title>
# <macast.renderer>PotplayerRenderer</macast.title>
# <macast.platform>win32</macast.title>
# <macast.version>0.4</macast.version>
# <macast.host_version>0.7</macast.host_version>
# <macast.author>xfangfang</macast.author>
# <macast.desc>PotPlayer support for Macast, this is a simple plugin that only supports play and stop.</macast.desc>


import os
import time
import logging
import cherrypy
import threading
import subprocess
import win32api, win32con
from enum import Enum
from contextlib import contextmanager

from macast import gui, Setting
from macast.renderer import Renderer
from macast.utils import SETTING_DIR

POTPLAYER_PATH_64 = r'C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe'
POTPLAYER_PATH_32 = r'C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe'

logger = logging.getLogger("PotPlayer")
subtitle = os.path.join(SETTING_DIR, r"macast.ass")

class SettingProperty(Enum):
    Potplayer_Path = 0

@contextmanager
def win32_reg_open(key, access=None, hive=None):
    if access is None:
        access = win32con.KEY_SET_VALUE
    if hive is None:
        hive = win32con.HKEY_CURRENT_USER
    handle = win32api.RegOpenKey(
        hive,
        key,
        0,
        access)
    yield handle
    win32api.RegCloseKey(handle)

def get_potplayer_path():
    # read Windows registry
    try:
        with win32_reg_open(r'Software\DAUM\PotPlayer64', win32con.KEY_SET_VALUE|win32con.KEY_QUERY_VALUE) as key:
            path = win32api.RegQueryValueEx(key, 'ProgramPath')[0]
            if os.path.exists(path):
                return path
    except:
        pass

    try:
        with win32_reg_open(r'Software\DAUM\PotPlayer', win32con.KEY_SET_VALUE|win32con.KEY_QUERY_VALUE) as key:
            path = win32api.RegQueryValueEx(key, 'ProgramPath')[0]
            if os.path.exists(path):
                return path
    except:
        pass

    # read macast configuration
    path = Setting.get(SettingProperty.Potplayer_Path, None)

    # using default location
    if path is None or not os.path.exists(path):
        if os.path.exists(POTPLAYER_PATH_64):
            return POTPLAYER_PATH_64
        elif os.path.exists(POTPLAYER_PATH_32):
            return POTPLAYER_PATH_32

    # cannot find potplayer
    Setting.set(SettingProperty.Potplayer_Path, POTPLAYER_PATH_64)
    return None

class PotplayerRenderer(Renderer):
    def __init__(self):
        super(PotplayerRenderer, self).__init__()
        self.pid = None
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
        if self.pid is not None:
            subprocess.Popen(['taskkill', '/f', '/pid', str(self.pid)], creationflags=subprocess.CREATE_NO_WINDOW).communicate()
        try:
            os.remove(subtitle)
        except:
            pass
        self.pid = None
        self.set_state_transport('STOPPED')
        cherrypy.engine.publish('renderer_av_stop')

    def start_player(self, url):
        path = get_potplayer_path()
        if path is None:
            subprocess.Popen(['notepad.exe', Setting.setting_path], creationflags=subprocess.CREATE_NO_WINDOW)
            cherrypy.engine.publish('app_notify', "Error", "You should modify 'Potplayer_Path' to your local potplayer and restart Macast.")
            logger.error(f'cannot find potplayer at: {Setting.get(SettingProperty.Potplayer_Path, None)}')
            logger.error(f'cannot find potplayer at: {POTPLAYER_PATH_64}')
            logger.error(f'cannot find potplayer at: {POTPLAYER_PATH_32}')
            return
        try:
            proc = subprocess.Popen(f'"{path}" "{url}" /autoplay /sub="{subtitle}"', creationflags=subprocess.CREATE_NO_WINDOW)
            self.pid = proc.pid
            # wait potplayer to stop
            proc.communicate()
            logger.info('Potplayer stopped')
        except Exception as e:
            logger.exception("cannot start potplayer", exc_info=e)
            self.set_media_stop()
            cherrypy.engine.publish('app_notify', "Error", str(e))

    def set_media_url(self, url, start=0):
        self.set_media_stop()
        self.start_position = 0
        threading.Thread(target=self.start_player, daemon=True, kwargs={'url': url}).start()
        self.set_state_transport("PLAYING")
        cherrypy.engine.publish('renderer_av_uri', url)

    def stop(self):
        super(PotplayerRenderer, self).stop()
        self.set_media_stop()
        logger.info("PotPlayer stop")

    def start(self):
        super(PotplayerRenderer, self).start()
        logger.info("PotPlayer start")


if __name__ == '__main__':
    gui(PotplayerRenderer())
    # or using cli to disable taskbar menu
    # from macast import cli
    # cli(PotplayerRenderer())
