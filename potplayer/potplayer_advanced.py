# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# Using potplayer as DLNA media renderer
#
# Macast Metadata
# <macast.title>PotPlayer Advanced</macast.title>
# <macast.renderer>PotplayerRenderer</macast.title>
# <macast.platform>win32</macast.title>
# <macast.version>0.4</macast.version>
# <macast.host_version>0.71</macast.host_version>
# <macast.author>xfangfang</macast.author>
# <macast.desc>PotPlayer support for Macast.</macast.desc>


import os
import time
import logging
import cherrypy
import threading
import pyperclip
import subprocess
import webbrowser
import win32process,win32api,win32gui,win32con
from enum import Enum
from contextlib import contextmanager
from macast import SETTING_DIR, Setting
from macast.utils import notify_error, win32_reg_open
from macast.renderer import Renderer

# We will read the potplayer location in the Windows registry first.
# If it does not exist, potplayer location will be set to the value in the macast configuration file.
# If both do not exist, it will be set to POTPLAYER_PATH_64 or POTPLAYER_PATH_32.
# So when it can't find the potplayer automatically, please edit the `Potplayer_Path` in Macast configuration file or advanced setting. 
# Generally, the program will automatically pop up the setting interface.
# Therefore, there is no need to modify the following variables.
POTPLAYER_PATH_64 = r'C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe'
POTPLAYER_PATH_32 = r'C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe'

# This shortcut key helps macast get the length of the video.
# And it's automatically set in the potlayer.
POTPLAYER_HOT_KEY = [('shift+ctrl+alt', ord('1'), 10925)]

logger = logging.getLogger("PotPlayer")
subtitle = os.path.join(SETTING_DIR, "macast.ass")

class SettingProperty(Enum):
    Potplayer_Path = 0

def find_hwnd_by_pid(pid):
    hwnd_title = []
    def get_all_hwnd(hwnd,mouse):
        if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):
            hwnd_title.append((hwnd, win32gui.GetWindowText(hwnd)))
    win32gui.EnumWindows(get_all_hwnd, 0)
    windows = []
    for h, t in hwnd_title:
        if t != '' and win32process.GetWindowThreadProcessId(h)[1] == pid:
            windows.append(h)
            logger.debug(f'pid: {pid} hwnd: {h} title: {t}')
    return windows

def get_child_hwnd(p_hwnd):
    hwnd_title = []
    def get_all_hwnd(hwnd, mouse):
        if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):
            hwnd_title.append((hwnd, win32gui.GetWindowText(hwnd)))
    win32gui.EnumChildWindows(p_hwnd, get_all_hwnd, None)
    logger.debug(f'child_hwnd: {hwnd_title}')
    return hwnd_title

def focus_on_window(hwnd):
    if hwnd is None:
        return
    logger.debug(f"Focus on current hwnd: {hwnd}")
    try:
        win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        logger.exception(f'SetForegroundWindow: {e}')

@notify_error()
def send_key(hwnd, *keys):
    keys = list(keys)
    focus_on_window(hwnd)
    for key in keys:
        win32api.keybd_event(key, 0, 0, 0)
    keys.reverse()
    for key in keys:
        win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)

@notify_error()
def send_text(hwnd, text):
    if hwnd is None:
        return
    win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)
    win32gui.SetForegroundWindow(hwnd)
    win32gui.SendMessage(hwnd, win32con.WM_SETTEXT, None, text)

def second_to_position(second):
    """ second : 0, "0", "00:00:00"
    """
    if isinstance(second, str):
        pos = second.split(':')
        if len(pos) == 1:
            second = int(second)
        elif len(pos) == 2:
            second = int(pos[0]) * 60 + int(pos[1])
        elif len(pos) == 3:
            second = int(pos[0]) * 3600 + int(pos[1]) * 60 + int(pos[2])
        else:
            second = 0
    return second, '%d:%02d:%02d' % (second // 3600, (second % 3600) // 60, second % 60)

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
    else:
        return path

    # cannot find potplayer
    if path is None:
        Setting.set(SettingProperty.Potplayer_Path, POTPLAYER_PATH_64)
    return None

@contextmanager
def get_potplayer_registry():
    path = get_potplayer_path()
    if path is None:
        yield None
        return
    potplayer_base = os.path.basename(path).split(".")[0]
    try:
        key = win32api.RegOpenKey(
            win32con.HKEY_CURRENT_USER,
            rf'Software\DAUM\{potplayer_base}\MainShortCutList',
            0,
            win32con.KEY_SET_VALUE|win32con.KEY_QUERY_VALUE)
    except:
        key = win32api.RegCreateKey(
            win32con.HKEY_CURRENT_USER,
            rf'Software\DAUM\{potplayer_base}\MainShortCutList')
    yield key
    win32api.RegCloseKey(key)

def set_potplayer_hotkey(potplayer_registry_key, func_key, main_key, func_code):
    func_key = func_key.lower()
    func_key_code = 0
    if 'shift' in func_key:
        func_key_code += 1
    if 'ctrl' in func_key:
        func_key_code += 2
    if 'alt' in func_key:
        func_key_code += 4

    hotkey_data = f'{main_key},{func_key_code},{func_code},0'
    logger.debug(f'Set hotkey: {hotkey_data}')
    hotkey_num = win32api.RegQueryInfoKey(potplayer_registry_key)[1]
    logger.debug(f"Current hotkey num: {hotkey_num}")

    for i in range(hotkey_num):
        hotkey = win32api.RegEnumValue(potplayer_registry_key, i)
        logger.debug(f'hotkey: {hotkey}')
        # if already set hotkey
        if f'{main_key},{func_key_code}' in hotkey[1]:
            if hotkey[1] == hotkey_data:
                logger.info(f"Already set hotkey: {hotkey}")
                break
            else:
                # hotkey has been set to another function
                logger.info(f"Override hotkey: {hotkey}")
                win32api.RegSetValueEx(
                    potplayer_registry_key,
                    hotkey[0],
                    0,
                    win32con.REG_SZ,
                    hotkey_data)
                break
    else:
        if hotkey_num > 0:
            hotkey = win32api.RegEnumValue(potplayer_registry_key, hotkey_num-1)
            if hotkey[1] == '':
                hotkey_num -= 1
        win32api.RegSetValueEx(
            potplayer_registry_key,
            str(hotkey_num),
            0,
            win32con.REG_SZ,
            hotkey_data)
        win32api.RegSetValueEx(
            potplayer_registry_key,
            str(hotkey_num+1),
            0,
            win32con.REG_SZ,
            "")
  
class PotplayerRenderer(Renderer):
    def __init__(self):
        super(PotplayerRenderer, self).__init__()
        self.pid = None
        self.hwnd = None

        # a thread is started here to increase the playback position once per second
        # to simulate that the media is playing.
        self.start_position = 0
        self.got_duration = False
        self.position_thread_running = True
        self.is_playing = False
        self.position_thread = threading.Thread(target=self.position_tick, daemon=True, name="POSITION_TICK")
        self.position_thread.start()

        # set potplayer hotkey for macast
        logger.debug(f'POTPLAYER_HOT_KEY: {POTPLAYER_HOT_KEY}')
        with get_potplayer_registry() as registry:
            if registry is not None:
                for func, main, code in POTPLAYER_HOT_KEY:
                    logger.debug(f'Set hotkey: {func}+{main} -> {code}')
                    set_potplayer_hotkey(registry, func, main, code)
            else:
                logger.error(f'cannot find potplayer at: {Setting.get(SettingProperty.Potplayer_Path, None)}')
                logger.error(f'cannot find potplayer at: {POTPLAYER_PATH_64}')
                logger.error(f'cannot find potplayer at: {POTPLAYER_PATH_32}')


    def position_tick(self):
        while self.position_thread_running:
            time.sleep(1)
            if self.is_playing and self.got_duration:
                self.start_position += 1
                sec = self.start_position
                position = '%d:%02d:%02d' % (sec // 3600, (sec % 3600) // 60, sec % 60)
                self.protocol.set_state_position(position)
            
    def set_media_stop(self):
        if self.pid is not None:
            subprocess.Popen(['taskkill', '/f', '/pid', str(self.pid)], creationflags=subprocess.CREATE_NO_WINDOW).communicate()
        # remove subtitle
        try:
            os.remove(subtitle)
        except:
            pass
        self.pid = None
        self.hwnd = None
        self.is_playing = False
        self.protocol.set_state_stop()
    
    def set_media_sub_file(self, data):
        pass
        # send_key(self.hwnd, win32con.VK_CONTROL, win32con.VK_MENU, ord('Y'))

    def set_media_sub_show(self, data: bool):
        send_key(self.hwnd, win32con.VK_MENU, ord('H'))

    def start_player(self, url, start):
        path = get_potplayer_path()
        if path is None:
            # subprocess.Popen(['notepad.exe', Setting.setting_path])
            webbrowser.open(f'http://localhost:{Setting.get_setting_port()}?page=2')
            cherrypy.engine.publish('app_notify', "Error", "You should modify 'Potplayer_Path' to your local potplayer and restart Macast.")
            logger.error(f'cannot find potplayer at: {Setting.get(SettingProperty.Potplayer_Path, None)}')
            logger.error(f'cannot find potplayer at: {POTPLAYER_PATH_64}')
            logger.error(f'cannot find potplayer at: {POTPLAYER_PATH_32}')
            return

        try:
            # clear clipboard
            pyperclip.copy('00')
            # wait the title state to be set
            time.sleep(0.2)
            title = self.protocol.get_state_title()
            if title is None or title == '':
                title = 'Macast'
            # start potplayer
            proc = subprocess.Popen(f'"{path}" "{url}" /autoplay /title="{title}" /seek="{start}" /sub="{subtitle}"', creationflags=subprocess.CREATE_NO_WINDOW)
            logger.info(f'Potplayer pid: {proc.pid}')
            self.pid = proc.pid

            # get window hwnd
            error_time = 20
            while error_time:
                time.sleep(0.5)
                hwnd_list = find_hwnd_by_pid(self.pid)
                if len(hwnd_list) > 0:
                    self.hwnd = hwnd_list[-1]
                    break
                error_time -= 1

            # get video duration
            error_time = 20
            while error_time:
                time.sleep(0.5)
                send_key(self.hwnd,
                    win32con.VK_CONTROL,
                    win32con.VK_MENU,  
                    win32con.VK_SHIFT,
                    ord('1'))  
                duration = pyperclip.paste()
                try:
                    second, position = second_to_position(duration)
                    logger.info(f'Get video duration: {position}')
                    if second != 0:
                        self.got_duration = True
                        self.protocol.set_state_duration(position)
                        break
                except:
                    pass
                error_time -= 1
            else:
                logger.error('Timeout: cannot get video duration')

            self.is_playing = True
            # wait potplayer to stop
            proc.communicate()
            logger.info('Potplayer stopped')
        except Exception as e:
            print(e)
            self.set_media_stop()
            cherrypy.engine.publish('app_notify', "Error", str(e))
  
    def set_media_url(self, url, start=0):
        self.start_position, position_text = second_to_position(start)
        self.got_duration = False
        self.is_playing = True
        self.set_media_stop()
        threading.Thread(
                target=self.start_player,
                daemon=True,
                kwargs={'url': url, 'start': position_text}, name="POTPLAYER").start()
        self.set_state_play()

    def set_media_pause(self):
        self.is_playing = False
        send_key(self.hwnd, win32con.VK_SPACE)
        self.protocol.set_state_pause()

    def set_media_resume(self):
        self.is_playing = True
        send_key(self.hwnd, win32con.VK_SPACE)
        self.protocol.set_state_play()
        
    def set_media_mute(self, data):
        send_key(self.hwnd, ord('M'))

    def set_media_position(self, data):
        logger.info(f'media position: {data}')
        second, position = second_to_position(data)
        self.start_position = second

        send_key(self.hwnd, ord('G'))
        time.sleep(0.5)
        hwnd_list = find_hwnd_by_pid(self.pid)
        h = hwnd_list[0]
        send_text(get_child_hwnd(h)[0][0], data)
        time.sleep(0.5)
        send_key(h, win32con.VK_RETURN)
        send_key(h, win32con.VK_ESCAPE)

    def stop(self):
        super(PotplayerRenderer, self).stop()
        self.set_media_stop()
        self.protocol.set_state_stop()
        logger.info("PotPlayer stop")

    def start(self):
        super(PotplayerRenderer, self).start()
        logger.info("PotPlayer start")


if __name__ == '__main__':
    from macast import gui
    Setting.setup_logger()
    gui(PotplayerRenderer())
