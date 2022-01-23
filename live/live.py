# mpv-based live plugin for macast
#
# Macast Metadata
# <macast.title>Live Renderer</macast.title>
# <macast.renderer>LiveRenderer</macast.renderer>
# <macast.platform>win32,darwin,linux</macast.platform>
# <macast.version>0.2</macast.version>
# <macast.host_version>0.7</macast.host_version>
# <macast.author>dushan555</macast.author>
# <macast.desc>Live support for Macast,It developed based on MPVRenderer,Can be used to watch live TV.</macast.desc>
import gettext
import os
import sys
import cherrypy
import logging
import requests
from macast import Setting, MenuItem, gui, App
from macast_renderer.mpv import MPVRenderer, MPVRendererSetting
from macast.utils import SETTING_DIR, RENDERER_DIR

logger = logging.getLogger("LiveRenderer")
logger.setLevel(logging.INFO)

live_text = None
RENDERER_PATH = os.path.join(SETTING_DIR, RENDERER_DIR)
LIVE_PATH = os.path.join(RENDERER_PATH, 'macast_live.m3u8')

if not os.path.exists(LIVE_PATH):
    r = requests.get('http://notag.cn/live/macast_live.m3u8')
    with open(LIVE_PATH, 'wb') as f:
        f.write(r.content)

if os.path.exists(LIVE_PATH):
    with open(LIVE_PATH, 'r', encoding='UTF-8') as f:
        live_text = str(f.read())
        logger.info(f'live {f.name}')

LIVE_LIST = None if (live_text is None) else live_text.split('#EXTINF:-1 ,')


def get_base_path(path="."):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.getcwd()
    return os.path.join(base_path, path)


def get_lang():
    locale = Setting.get_locale()
    i18n_path = get_base_path('i18n')
    if not os.path.exists(os.path.join(i18n_path, locale, 'LC_MESSAGES', 'macast.mo')):
        locale = locale.split("_")[0]
    logger.error("Live Loading Language: {}".format(locale))
    try:
        lang = gettext.translation('macast', localedir=i18n_path, languages=[locale])
        lang.install()
    except Exception:
        import builtins
        builtins.__dict__['_'] = gettext.gettext
        logger.error("Live Loading Default Language en_US")


class LiveRenderer(MPVRenderer):
    def __init__(self, path=Setting.mpv_default_path):
        get_lang()
        super(LiveRenderer, self).__init__(lang=_, path=path)
        self.renderer_setting = LiveRendererSetting()


class LiveRendererSetting(MPVRendererSetting):
    def __init__(self):
        super(LiveRendererSetting, self).__init__()
        live_items = []
        for live_item in LIVE_LIST:
            if live_item.startswith('#EXTM3U'):
                live_menu_2 = MenuItem(_('PlayList'), self.on_start_click, data=LIVE_PATH)
            else:
                item_attr = live_item.split('\n')
                live_menu_2 = MenuItem(item_attr[0], self.on_start_click, data=item_attr[1])
            live_items.append(live_menu_2)
        self.liveItem = MenuItem(_('LiveList'), children=live_items)
        self.lastItem = None

    def build_menu(self):
        live_menu = [MenuItem('live v0.2', enabled=False), self.liveItem]
        for menu_item in super(LiveRendererSetting, self).build_menu():
            live_menu.append(menu_item)
        return live_menu

    @property
    def renderer(self):
        renderers = cherrypy.engine.publish('get_renderer')
        if len(renderers) == 0:
            logger.error("Unable to find an available renderer.")
            return None
        return renderers.pop()

    @property
    def protocol(self):
        protocols = cherrypy.engine.publish('get_protocol')
        if len(protocols) > 0:
            return protocols.pop()

    def on_start_click(self, item):
        if self.lastItem and self.lastItem.data == item.data:
            return
        logger.info(f'text: {item.text} data: {item.data}')
        self.renderer.set_media_title(item.text)
        self.renderer.set_media_url(item.data)
        self.protocol.set_state_url(item.data)

        if self.lastItem:
            self.lastItem.checked = False
        item.checked = True
        self.lastItem = item


if __name__ == '__main__':
    gui(LiveRenderer(path='bin/mpv.exe'))
