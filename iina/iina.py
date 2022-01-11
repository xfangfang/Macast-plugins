# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Using IINA as DLNA media renderer
#
# Macast Metadata
# <macast.title>IINA Renderer</macast.title>
# <macast.renderer>IINARenderer</macast.renderer>
# <macast.platform>darwin</macast.platform>
# <macast.version>0.3</macast.version>
# <macast.host_version>0.65</macast.host_version>
# <macast.author>xfangfang</macast.author>
# <macast.desc>IINA support for Macast. Because iina is developed based on MPV, this plugin experience is similar to the built-in MPV renderer.</macast.desc>


import os
import json
import time
import threading
import cherrypy
import subprocess
import gettext
import logging
from queue import Queue
from macast import RendererSetting, Setting, gui
from macast_renderer.mpv import MPVRenderer

IINA_PATH = '/Applications/IINA.app/Contents/MacOS/iina-cli'

logger = logging.getLogger("IINARenderer")
logger.setLevel(logging.DEBUG)


class IINARenderer(MPVRenderer):
    def __init__(self):
        super(IINARenderer, self).__init__(gettext.gettext, IINA_PATH)
        self.renderer_setting = RendererSetting()
        self.commond_queue = Queue()
        self.mpv_thread = None
        self.ipc_thread = None
        self.iina = None
        self.is_iina_start = False

    def command_send_thread(self):
        print("command_send_thread start {}".format(self.running))
        while self.running:
            print("check command")
            while not self.commond_queue.empty():
                command = self.commond_queue.get()
                if not self.is_iina_start:
                    self.commond_queue.task_done()
                    continue
                error_time = 10
                while error_time > 0:
                    error_time -= 1
                    print("send command: " + str(command))
                    msg = json.dumps({"command": command}) + '\n'
                    try:
                        self.ipc_sock.sendall(msg.encode())
                        self.commond_queue.task_done()
                        break
                    except Exception as e:
                        logger.error('error sendCommand: ' + str(e))
                        time.sleep(1)
                else:
                    cherrypy.engine.publish("app_notify", "Macast", "Cannot sending msg to iina.")
                    logger.error("iina cannot start")
                    threading.Thread(target=lambda: Setting.stop_service(), name="IINA_STOP_SERVICE").start()
            time.sleep(1)

    def set_media_stop(self):
        try:
            if self.iina is not None:
                self.iina.terminate()
            os.waitpid(-1, 1)
        except Exception as e:
            print(str(e))
        self.iina = None
        self.is_iina_start = False
        self.ipc_running = False
        if self.ipc_thread is not None and self.ipc_thread.is_alive():
            self.ipc_thread.join()
            self.ipc_thread = None
        cherrypy.engine.publish('renderer_av_stop')

    def set_media_url(self, data):
        """ data : string
        """
        if not self.is_iina_start:
            self.set_media_stop()
            self.start_iina(data)
            self.ipc_thread = threading.Thread(target=self.start_ipc, name="IINA_IPC_THREAD")
            self.ipc_thread.start()
        else:
            self.send_command(['loadfile', data, 'replace'])
        cherrypy.engine.publish('renderer_av_uri', data)

    def send_command(self, command):
        """Sending command to iina
        """
        if self.is_iina_start:
            print("put command to queue: {}".format(command))
            self.commond_queue.put(command)

    def set_observe(self):
        super(IINARenderer, self).set_observe()
        self.set_media_volume(100)

    def start_iina(self, url):
        """Start iina thread
        """
        self.is_iina_start = True
        params = [
            self.path,
            '--keep-running',
            '--mpv-input-ipc-server={}'.format(self.mpv_sock),
            url
        ]
        # start iina
        print("iina starting")
        cherrypy.engine.publish('mpv_start')
        self.iina = subprocess.Popen(
            params,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=Setting.get_system_env())

    def start(self):
        super(MPVRenderer, self).start()
        logger.info("starting IINARenderer")
        self.mpv_thread = threading.Thread(target=self.command_send_thread, daemon=True, name="COMMAND_SEND")
        self.mpv_thread.start()

    def stop(self):
        super(MPVRenderer, self).stop()
        logger.info("stoping IINARenderer")
        self.set_media_stop()


if __name__ == '__main__':
    Setting.load()
    gui(IINARenderer())
