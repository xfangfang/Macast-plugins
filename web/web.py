# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Using web browser as DLNA media renderer
# This plugin can be used to download media files or get some m3u8 played
#
# Macast Metadata
# <macast.title>Web Renderer</macast.title>
# <macast.renderer>WebRenderer</macast.renderer>
# <macast.platform>darwin,linux,win32</macast.platform>
# <macast.version>0.1</macast.version>
# <macast.author>xfangfang</macast.author>
# <macast.desc>Using web browser as DLNA media renderer</macast.desc>


import os
import sys
import time
import threading
import pyperclip
import cherrypy
import subprocess
import webbrowser
from enum import Enum
from macast import gui, Setting, MenuItem
from macast.renderer import Renderer, RendererSetting


class WebRenderer(Renderer):

    def __init__(self):
        super(WebRenderer, self).__init__()
        self.start_position = 0
        self.position_thread_running = True
        self.position_thread = threading.Thread(target=self.position_tick, daemon=True)
        self.position_thread.start()
        self.renderer_setting = WebRendererSetting()

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
        self.open_browser(url)
        self.set_state_transport("PLAYING")
        cherrypy.engine.publish('renderer_av_uri', url)

    def get_env(self):
        # https://github.com/pyinstaller/pyinstaller/issues/3668#issuecomment-742547785
        env = Setting.get_system_env()
        toDelete = []
        for (k, v) in env.items():
            if k != 'PATH' and 'tmp' in v:
                toDelete.append(k)
        for k in toDelete:
            env.pop(k, None)
        return env

    def open_browser(self, url):
        if self.renderer_setting.setting_autocopy:
            pyperclip.copy(url)
        if sys.platform == 'darwin':
            subprocess.Popen(['open', url])
        elif sys.platform == 'win32':
            webbrowser.open(url)
        else:
            subprocess.Popen(["xdg-open", url], env=self.get_env())

    def stop(self):
        super(WebRenderer, self).stop()
        self.set_media_stop()
        print("Web stop")
        cherrypy.engine.publish('renderer_av_stop')

    def start(self):
        super(WebRenderer, self).start()
        print("Web start")


class SettingProperty(Enum):
    Web_AutoCopy = 1
    Web_AutoCopy_Disable = 0
    Web_AutoCopy_Enable = 1


class WebRendererSetting(RendererSetting):
    def __init__(self):
        Setting.load()
        self.webAutoCopyItem = None
        self.setting_autocopy = Setting.get(SettingProperty.Web_AutoCopy,
                                            SettingProperty.Web_AutoCopy_Enable.value)

    def build_menu(self):
        self.webAutoCopyItem = MenuItem("Auto Copy Url",
                                        self.on_autocopy_clicked,
                                        checked=self.setting_autocopy)
        return [
            self.webAutoCopyItem,
        ]

    def on_autocopy_clicked(self, item):
        item.checked = not item.checked
        self.setting_autocopy = 1 if item.checked else 0
        Setting.set(SettingProperty.Web_AutoCopy, self.setting_autocopy)


if __name__ == '__main__':
    gui(WebRenderer())
