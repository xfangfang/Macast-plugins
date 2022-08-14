# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Using IINA as DLNA media renderer
#
# Macast Metadata
# <macast.title>波澜播放器-IINA</macast.title>
# <macast.renderer>BolanIINARenderer</macast.renderer>
# <macast.platform>darwin</macast.platform>
# <macast.version>0.32</macast.version>
# <macast.host_version>0.7</macast.host_version>
# <macast.author>xfangfang&小棉袄&Reborn</macast.author>
# <macast.desc>IINA echanced support for Macast offical IINA Renderer. Echancement: support headers</macast.desc>


import os
import json
import time
import socket
import threading
import cherrypy
import subprocess
import gettext
import logging
from queue import Queue
from macast import RendererSetting, Setting, gui
from macast_renderer.mpv import MPVRenderer
from urllib.parse import unquote

IINA_PATH = '/Applications/IINA.app/Contents/MacOS/iina-cli'

logger = logging.getLogger("BolanIINARenderer")
logger.setLevel(logging.DEBUG)


class BolanIINARenderer(MPVRenderer):
    def __init__(self):
        super(BolanIINARenderer, self).__init__(gettext.gettext, IINA_PATH)
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
                if not self.running:
                    return
                if not self.is_iina_start:
                    break
                command = self.commond_queue.get()
                error_time = 10
                while error_time > 0:
                    error_time -= 1
                    print("send command: " + str(command))
                    msg = json.dumps({"command": command}) + '\n'
                    try:
                        self.ipc_sock.sendall(msg.encode())
                        self.commond_queue.task_done()
                        time.sleep(0.05)
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

    def parse_header(self, url):
        header_map = {}
        data = url.split("##|", 1)
        if len(data) < 2:
            return url, header_map
        url = data[0]
        headers = data[1].split("&")
        for h in headers:
            item = h.split("=", 1)
            if len(item) < 2:
                continue
            header_map[item[0]] = unquote(item[1], 'utf-8')
        return url, header_map

    def set_media_url(self, url, start='0'):
        """ data : string
        """

        def position_to_second(position: str) -> int:
            pos = position.split(':')
            if len(pos) < 3:
                return 0
            return int(pos[0]) * 3600 + int(pos[1]) * 60 + int(pos[2])

        try:
            start = int(start)
        except:
            start = position_to_second(start)

        url, header_map = self.parse_header(url)
        agent = "Mozilla/5.0 (Linux; Android 11; Mi 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.152 Mobile Safari/537.36"
        if 'User-Agent' in header_map:
            agent = header_map['User-Agent']
            del header_map['User-Agent']
        header = ','.join([f'{i}: {header_map[i]}' for i in header_map])
        # UA要放最后，否则不正常
        header = f'User-Agent: {agent}' if len(header) == 0  else f'{header},User-Agent: {agent}'
        header = header.replace('+', ' ')

        if not self.is_iina_start:
            self.set_media_stop()
            self.start_iina(url, header, start)
            self.ipc_thread = threading.Thread(target=self.start_ipc, name="IINA_IPC_THREAD")
            self.ipc_thread.start()
        else:
            self.send_command(['loadfile', url, 'replace', f'start={start}'])

        # self.send_command(['set_property', '--mpv-http-header-fields', header])
        cherrypy.engine.publish('renderer_av_uri', url)

    def send_command(self, command):
        """Sending command to iina
        """
        if self.is_iina_start:
            print("put command to queue: {}".format(command))
            self.commond_queue.put(command)

    def set_observe(self):
        super(BolanIINARenderer, self).set_observe()
        self.set_media_volume(100)

    def start_iina(self, url, header, start=0):
        """Start iina thread
        """
        print("url: {}".format(url))
        print("header: {}".format(header))
        self.is_iina_start = True
        if len(header) == 0:
            params = [
                self.path,
                '--keep-running',
                f'--mpv-input-ipc-server={self.mpv_sock}',
                f'--mpv-start={start}',
                f'{url}',
            ]
        else:
            params = [
                self.path,
                '--keep-running',
                f'--mpv-input-ipc-server={self.mpv_sock}',
                f'--mpv-start={start}',
                f'--mpv-http-header-fields={header}',
                f'{url}',
            ]
        # start iina
        logger.info(' '.join([f'{i}' for i in params]))
        print("iina starting")
        cherrypy.engine.publish('mpv_start')
        self.iina = subprocess.Popen(
            params,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=Setting.get_system_env())

    def start_ipc(self):
        """Start ipc thread
        Communicating with mpv
        """
        if self.ipc_running:
            logger.error("mpv ipc is already runing")
            return
        self.ipc_running = True
        error_time = 0
        internal = 0.5
        while self.ipc_running and self.running and self.mpv_thread.is_alive():
            try:
                time.sleep(internal)
                logger.error("mpv ipc socket start connect")
                self.ipc_sock = socket.socket(socket.AF_UNIX,
                                              socket.SOCK_STREAM)
                self.ipc_sock.connect(self.mpv_sock)
                cherrypy.engine.publish('mpvipc_start')
                cherrypy.engine.publish('renderer_start')
                self.ipc_once_connected = True
                internal = 0.5
                self.set_observe()
            except Exception as e:
                error_time += 1
                if error_time > 20:
                    internal = 2
                if self.iina is not None and self.iina.poll() is not None:
                    self.is_iina_start = False
                    self.ipc_running = False
                    self.set_state_stop()
                logger.error("mpv ipc socket reconnecting: {}".format(str(e)))
                continue
            res = b''
            msgs = None
            while self.ipc_running:
                try:
                    data = self.ipc_sock.recv(1048576)
                    if data == b'':
                        break
                    res += data
                    if data[-1] != 10:
                        continue
                except Exception as e:
                    logger.debug(e)
                    break
                try:
                    msgs = res.decode().strip().split('\n')
                    for msg in msgs:
                        self.update_state(msg)
                except Exception as e:
                    logger.error("decode error: {}".format(e))
                    logger.error(f"decode error data: {msg}")
                    logger.error(f"decode error data list: {msgs}")
                finally:
                    res = b''
            self.ipc_sock.close()
            logger.error("mpv ipc stopped")

    def start(self):
        super(MPVRenderer, self).start()
        logger.info("starting BolanIINARenderer")
        self.mpv_thread = threading.Thread(target=self.command_send_thread, daemon=True, name="COMMAND_SEND")
        self.mpv_thread.start()

    def stop(self):
        super(MPVRenderer, self).stop()
        logger.info("stoping BolanIINARenderer")
        self.set_media_stop()


if __name__ == '__main__':
    Setting.load()
    gui(BolanIINARenderer())
