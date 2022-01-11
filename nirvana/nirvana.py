# Copyright (c) 2021 by xfangfang. All Rights Reserved.
#
# NVA protocol
#
# Macast Metadata
# <macast.title>NVA Protocol</macast.title>
# <macast.protocol>NVAProtocol</macast.protocol>
# <macast.platform>darwin,win32,linux</macast.platform>
# <macast.version>0.1</macast.version>
# <macast.host_version>0.7</macast.host_version>
# <macast.author>xfangfang</macast.author>
# <macast.desc>NVA protocol support for Macast.</macast.desc>


import re
import os
import urllib
import socket
import cheroot.server
import cherrypy
from cherrypy import _cpnative_server, Tool
import email.utils
import logging
import threading
import struct
import json
import time
from urllib import parse
import errno
import requests
from lxml import etree
import select

from macast.protocol import DLNAProtocol, DLNAHandler, Protocol
from macast.renderer import Renderer
from macast.utils import SETTING_DIR, XMLPath, load_xml, Setting

LF = b'\n'
CRLF = b'\r\n'
TAB = b'\t'
SPACE = b' '
COLON = b':'
SEMICOLON = b';'
EMPTY = b''
ASTERISK = b'*'
FORWARD_SLASH = b'/'
QUOTED_SLASH = b'%2F'
QUOTED_SLASH_REGEX = re.compile(b''.join((b'(?i)', QUOTED_SLASH)))

COMMAND = b'Command'
SEND_CMD = b'\xe0'
RET_CMD = b'\xc0'
PING = b'\xe4'

NVA_SERVICE = """<?xml version="1.0" encoding="UTF-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <actionList>
    <action>
      <name>GetAppInfo</name>
      <argumentList>
        <argument>
          <name>PackageName</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_PackageName</relatedStateVariable>
        </argument>
        <argument>
          <name>AppKey</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_AppKey</relatedStateVariable>
        </argument>
        <argument>
          <name>Signature</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_Signature</relatedStateVariable>
        </argument>
        <argument>
          <name>CurrentSignedIn</name>
          <direction>out</direction>
          <relatedStateVariable>SignedIn</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>LoginWithCode</name>
      <argumentList>
        <argument>
          <name>Code</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>PrepareForMirrorProjection</name>
      <argumentList>
        <argument>
          <name>ScreenWidth</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_ScreenResolution</relatedStateVariable>
        </argument>
        <argument>
          <name>ScreenHeight</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_ScreenResolution</relatedStateVariable>
        </argument>
        <argument>
          <name>PushUrl</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>SetDanmakuSwitch</name>
      <argumentList>
        <argument>
          <name>DesiredSwitch</name>
          <direction>in</direction>
          <relatedStateVariable>DanmakuSwitch</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>AppendDanmaku</name>
      <argumentList>
        <argument>
          <name>Content</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
        <argument>
          <name>Size</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
        <argument>
          <name>Type</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
        <argument>
          <name>Color</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
        <argument>
          <name>DanmakuId</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
        <argument>
          <name>Action</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>GetPlayInfo</name>
      <argumentList>
        <argument>
          <name>Params</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
        <argument>
          <name>Content</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedString</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>GetAccountInfo</name>
      <argumentList>
        <argument>
          <name>VipInfo</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>SwitchQuality</name>
      <argumentList>
        <argument>
          <name>Qn</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_UnlimitedInt</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
  </actionList>
  <serviceStateTable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_UnlimitedString</name>
      <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_PackageName</name>
      <dataType>string</dataType>
      <defaultValue>com.xiaodianshi.tv.yst</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_AppKey</name>
      <dataType>string</dataType>
      <defaultValue>0000000000000000</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_Signature</name>
      <dataType>string</dataType>
      <defaultValue>0000000000000000</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_UnlimitedInt</name>
      <dataType>i4</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_ScreenResolution</name>
      <dataType>ui4</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>SignedIn</name>
      <dataType>boolean</dataType>
      <defaultValue>1</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>DanmakuSwitch</name>
      <dataType>boolean</dataType>
    </stateVariable>
  </serviceStateTable>
</scpd>
""".encode()

logger = logging.getLogger("NVAPRotocol")
logger.setLevel(logging.INFO)


# NVAHTTPServer 替换cherrypy中的 CPHTTPServer 负责适配NVA协议
# 主要适配代码位于 NVAHTTPRequest 中
# 主要修改的内容是，适配NVA的协议头：NVA/1.0（等同HTTP看待）


class NVAHTTPRequest(cheroot.server.HTTPRequest):
    def __init__(self, server, conn, proxy_mode=False, strict_mode=True):
        super(NVAHTTPRequest, self).__init__(server, conn, proxy_mode, strict_mode)
        # NVA PATCH: Add a variable indicating whether it is NVA protocol
        self.is_nva = False

    def read_request_line(self):
        """Read and parse first line of the HTTP request.

                Returns:
                    bool: True if the request line is valid or False if it's malformed.

                """
        # HTTP/1.1 connections are persistent by default. If a client
        # requests a page, then idles (leaves the connection open),
        # then rfile.readline() will raise socket.error("timed out").
        # Note that it does this based on the value given to settimeout(),
        # and doesn't need the client to request or acknowledge the close
        # (although your TCP stack might suffer for it: cf Apache's history
        # with FIN_WAIT_2).
        request_line = self.rfile.readline()

        # Set started_request to True so communicate() knows to send 408
        # from here on out.
        self.started_request = True
        if not request_line:
            return False

        if request_line == CRLF:
            # RFC 2616 sec 4.1: "...if the server is reading the protocol
            # stream at the beginning of a message and receives a CRLF
            # first, it should ignore the CRLF."
            # But only ignore one leading line! else we enable a DoS.
            request_line = self.rfile.readline()
            if not request_line:
                return False

        if not request_line.endswith(CRLF):
            self.simple_response(
                '400 Bad Request', 'HTTP requires CRLF terminators',
            )
            return False

        try:
            method, uri, req_protocol = request_line.strip().split(SPACE, 2)
            # NVA PATCH: Fit for NVA protocol
            if b'NVA' in req_protocol:
                req_protocol = req_protocol.replace(b'NVA/1.0', b'HTTP/1.0')
                self.is_nva = True
                # let the http server forget the socket when first request is done
                self.close_connection = True
                self.conn.linger = True

            if not req_protocol.startswith(b'HTTP/'):
                self.simple_response(
                    '400 Bad Request', 'Malformed Request-Line: bad protocol',
                )
                return False
            rp = req_protocol[5:].split(b'.', 1)
            if len(rp) != 2:
                self.simple_response(
                    '400 Bad Request', 'Malformed Request-Line: bad version',
                )
                return False
            rp = tuple(map(int, rp))  # Minor.Major must be threat as integers
            if rp > (1, 1):
                self.simple_response(
                    '505 HTTP Version Not Supported', 'Cannot fulfill request',
                )
                return False
        except (ValueError, IndexError):
            self.simple_response('400 Bad Request', 'Malformed Request-Line')
            return False

        self.uri = uri
        self.method = method.upper()

        if self.strict_mode and method != self.method:
            resp = (
                'Malformed method name: According to RFC 2616 '
                '(section 5.1.1) and its successors '
                'RFC 7230 (section 3.1.1) and RFC 7231 (section 4.1) '
                'method names are case-sensitive and uppercase.'
            )
            self.simple_response('400 Bad Request', resp)
            return False

        try:
            scheme, authority, path, qs, fragment = urllib.parse.urlsplit(uri)
        except UnicodeError:
            self.simple_response('400 Bad Request', 'Malformed Request-URI')
            return False

        uri_is_absolute_form = (scheme or authority)

        if self.method == b'OPTIONS':
            # TODO: cover this branch with tests
            path = (
                uri
                # https://tools.ietf.org/html/rfc7230#section-5.3.4
                if (self.proxy_mode and uri_is_absolute_form)
                else path
            )
        elif self.method == b'CONNECT':
            # TODO: cover this branch with tests
            if not self.proxy_mode:
                self.simple_response('405 Method Not Allowed')
                return False

            # `urlsplit()` above parses "example.com:3128" as path part of URI.
            # this is a workaround, which makes it detect netloc correctly
            uri_split = urllib.parse.urlsplit(b''.join((b'//', uri)))
            _scheme, _authority, _path, _qs, _fragment = uri_split
            _port = EMPTY
            try:
                _port = uri_split.port
            except ValueError:
                pass

            # FIXME: use third-party validation to make checks against RFC
            # the validation doesn't take into account, that urllib parses
            # invalid URIs without raising errors
            # https://tools.ietf.org/html/rfc7230#section-5.3.3
            invalid_path = (
                    _authority != uri
                    or not _port
                    or any((_scheme, _path, _qs, _fragment))
            )
            if invalid_path:
                self.simple_response(
                    '400 Bad Request',
                    'Invalid path in Request-URI: request-'
                    'target must match authority-form.',
                )
                return False

            authority = path = _authority
            scheme = qs = fragment = EMPTY
        else:
            disallowed_absolute = (
                    self.strict_mode
                    and not self.proxy_mode
                    and uri_is_absolute_form
            )
            if disallowed_absolute:
                # https://tools.ietf.org/html/rfc7230#section-5.3.2
                # (absolute form)
                """Absolute URI is only allowed within proxies."""
                self.simple_response(
                    '400 Bad Request',
                    'Absolute URI not allowed if server is not a proxy.',
                )
                return False

            invalid_path = (
                    self.strict_mode
                    and not uri.startswith(FORWARD_SLASH)
                    and not uri_is_absolute_form
            )
            if invalid_path:
                # https://tools.ietf.org/html/rfc7230#section-5.3.1
                # (origin_form) and
                """Path should start with a forward slash."""
                resp = (
                    'Invalid path in Request-URI: request-target must contain '
                    'origin-form which starts with absolute-path (URI '
                    'starting with a slash "/").'
                )
                self.simple_response('400 Bad Request', resp)
                return False

            if fragment:
                self.simple_response(
                    '400 Bad Request',
                    'Illegal #fragment in Request-URI.',
                )
                return False

            if path is None:
                # FIXME: It looks like this case cannot happen
                self.simple_response(
                    '400 Bad Request',
                    'Invalid path in Request-URI.',
                )
                return False

            # Unquote the path+params (e.g. "/this%20path" -> "/this path").
            # https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
            #
            # But note that "...a URI must be separated into its components
            # before the escaped characters within those components can be
            # safely decoded." https://www.ietf.org/rfc/rfc2396.txt, sec 2.4.2
            # Therefore, "/this%2Fpath" becomes "/this%2Fpath", not
            # "/this/path".
            try:
                # TODO: Figure out whether exception can really happen here.
                # It looks like it's caught on urlsplit() call above.
                atoms = [
                    urllib.parse.unquote_to_bytes(x)
                    for x in QUOTED_SLASH_REGEX.split(path)
                ]
            except ValueError as ex:
                self.simple_response('400 Bad Request', ex.args[0])
                return False
            path = QUOTED_SLASH.join(atoms)

        if not path.startswith(FORWARD_SLASH):
            path = FORWARD_SLASH + path

        if scheme is not EMPTY:
            self.scheme = scheme
        self.authority = authority
        self.path = path

        # Note that, like wsgiref and most other HTTP servers,
        # we "% HEX HEX"-unquote the path but not the query string.
        self.qs = qs

        # Compare request and server HTTP protocol versions, in case our
        # server does not support the requested protocol. Limit our output
        # to min(req, server). We want the following output:
        #     request    server     actual written   supported response
        #     protocol   protocol  response protocol    feature set
        # a     1.0        1.0           1.0                1.0
        # b     1.0        1.1           1.1                1.0
        # c     1.1        1.0           1.0                1.0
        # d     1.1        1.1           1.1                1.1
        # Notice that, in (b), the response will be "HTTP/1.1" even though
        # the client only understands 1.0. RFC 2616 10.5.6 says we should
        # only return 505 if the _major_ version is different.
        sp = int(self.server.protocol[5]), int(self.server.protocol[7])

        if sp[0] != rp[0]:
            self.simple_response('505 HTTP Version Not Supported')
            return False

        self.request_protocol = req_protocol

        # NVA PATCH: Set the correct protocol name to self.response_protocol
        if self.is_nva:
            self.response_protocol = 'NVA/%s.%s' % min(rp, sp)
        else:
            self.response_protocol = 'HTTP/%s.%s' % min(rp, sp)

        return True

    def send_headers(self):  # noqa: C901  # FIXME
        """Assert, process, and send the HTTP response message-headers.

        You must set ``self.status``, and :py:attr:`self.outheaders
        <HTTPRequest.outheaders>` before calling this.
        """
        hkeys = [key.lower() for key, value in self.outheaders]
        status = int(self.status[:3])

        if status == 413:
            # Request Entity Too Large. Close conn to avoid garbage.
            self.close_connection = True
        elif b'content-length' not in hkeys:
            # "All 1xx (informational), 204 (no content),
            # and 304 (not modified) responses MUST NOT
            # include a message-body." So no point chunking.
            if status < 200 or status in (204, 205, 304):
                pass
            else:
                needs_chunked = (
                        self.response_protocol == 'HTTP/1.1'
                        and self.method != b'HEAD'
                )
                if needs_chunked:
                    # Use the chunked transfer-coding
                    self.chunked_write = True
                    self.outheaders.append((b'Transfer-Encoding', b'chunked'))
                else:
                    # Closing the conn is the only way to determine len.
                    self.close_connection = True

        # Override the decision to not close the connection if the connection
        # manager doesn't have space for it.
        if not self.close_connection:
            can_keep = self.server.can_add_keepalive_connection
            self.close_connection = not can_keep

        if b'connection' not in hkeys:
            if self.response_protocol == 'HTTP/1.1':
                # Both server and client are HTTP/1.1 or better
                if self.close_connection:
                    self.outheaders.append((b'Connection', b'close'))
            else:
                # Server and/or client are HTTP/1.0
                if not self.close_connection:
                    self.outheaders.append((b'Connection', b'Keep-Alive'))

        if (b'Connection', b'Keep-Alive') in self.outheaders:
            self.outheaders.append((
                b'Keep-Alive',
                u'timeout={connection_timeout}'.
                    format(connection_timeout=self.server.timeout).
                    encode('ISO-8859-1'),
            ))

        if (not self.close_connection) and (not self.chunked_read):
            # Read any remaining request body data on the socket.
            # "If an origin server receives a request that does not include an
            # Expect request-header field with the "100-continue" expectation,
            # the request includes a request body, and the server responds
            # with a final status code before reading the entire request body
            # from the transport connection, then the server SHOULD NOT close
            # the transport connection until it has read the entire request,
            # or until the client closes the connection. Otherwise, the client
            # might not reliably receive the response message. However, this
            # requirement is not be construed as preventing a server from
            # defending itself against denial-of-service attacks, or from
            # badly broken client implementations."
            remaining = getattr(self.rfile, 'remaining', 0)
            if remaining > 0:
                self.rfile.read(remaining)

        if b'date' not in hkeys:
            self.outheaders.append((
                b'Date',
                email.utils.formatdate(usegmt=True).encode('ISO-8859-1'),
            ))

        if b'server' not in hkeys:
            self.outheaders.append((
                b'Server',
                self.server.server_name.encode('ISO-8859-1'),
            ))

        # NVA PATCH: Returns the NVA protocol name
        if self.is_nva:
            proto = self.response_protocol.encode('ascii')
        else:
            proto = self.server.protocol.encode('ascii')
        buf = [proto + SPACE + self.status + CRLF]
        for k, v in self.outheaders:
            buf.append(k + COLON + SPACE + v + CRLF)
        buf.append(CRLF)
        self.conn.wfile.write(EMPTY.join(buf))


class NVAHTTPConnection(cheroot.server.HTTPConnection):
    RequestHandlerClass = NVAHTTPRequest


class NVAHTTPServer(_cpnative_server.CPHTTPServer):
    ConnectionClass = NVAHTTPConnection


# DanmakuManager 负责处理弹幕下载和渲染
# 通过cid下载xml实时弹幕，转换为ass，保存为本地文件
# todo 实现protobuf实时弹幕下载与转换
# todo 实现弹幕文字大小随视频比例变化


class DanmakuManager:
    @staticmethod
    def get_danmaku(cid: str, file_path: str):
        """

        :param cid:
        :param file_path:
        :param is_portrait:
        :return:
        """
        # http://www.perlfu.co.uk/projects/asa/ass-specs.doc
        api = f'https://comment.bilibili.com/{cid}.xml'
        exist_time = 10
        res_x = 638
        res_y = 447

        lines = res_y // 25  # todo fix
        layers = [[-1 for _ in range(lines)] for _ in range(4)]

        def int2color(color_int):
            """
            :return: string, \c&Hbbggrr&
            """
            if color_int == 16777215:  # default color #FFFFFF
                return 'dark', ''
            color_int = hex(color_int)[2:]
            if len(color_int) < 6:
                color_int = '0' * (6 - len(color_int)) + color_int
            r = int(color_int[0:2], 16)
            g = int(color_int[2:4], 16)
            b = int(color_int[4:6], 16)
            gray = (r * 299 + g * 587 + b * 114) / 1000
            border_style = 'dark'
            if gray < 60:
                border_style = 'light'

            color_str = color_int[4:6] + color_int[2:4] + color_int[0:2]
            return border_style, rf'\c&H{color_str}&'

        def sec2str(t: float) -> str:
            sec = int(t)
            return f'{sec // 3600}:{(sec % 3600) // 60:02d}:{sec % 60:02d}.{int(t * 100) % 100:02d}'

        def create_postion(danmaku_position_type, layer_index, danmaku_text,
                           font_size, danmaku_start_time) -> str:
            if layer_index > 1:  # 是否是字幕层
                layer_index = 1

            y = -100
            if danmaku_position_type == 5:  # 顶部弹幕
                layer_index = 2
                for index, l in enumerate(layers[layer_index]):
                    if danmaku_start_time < l:
                        continue
                    layers[layer_index][index] = danmaku_start_time + exist_time
                    y = index * 25
                    break
                position_str = rf'\an8\pos({int(res_x / 2)},{y})'
            elif danmaku_position_type == 4:  # 底部弹幕
                layer_index = 3
                for index, l in enumerate(layers[layer_index]):
                    if danmaku_start_time < l:
                        continue
                    layers[layer_index][index] = danmaku_start_time + exist_time
                    y = res_y - index * 25
                    break
                position_str = rf'\an2\pos({int(res_x / 2)},{y})'
            else:  # 普通弹幕
                length = len(danmaku_text) * font_size
                for index, l in enumerate(layers[layer_index]):
                    danmaku_text_length = len(danmaku_text) * font_size
                    danmaku_text_time = (res_x * exist_time) / (res_x + danmaku_text_length)

                    if (danmaku_start_time + danmaku_text_time) < l:
                        continue
                    # 找到空位
                    layers[layer_index][index] = danmaku_start_time + exist_time
                    y = index * 25  # fix font size
                    break

                position_str = rf'\move({res_x},{y},{-length},{y})'

            # todo 根据视频大小 动态改变字体大小
            font_size = int(font_size)
            font = ''
            if font_size == 18:
                font = r'\fs18'
            elif font_size == 36:
                font = r'\fs36'

            return position_str + font

        try:
            danmaku = etree.fromstring(requests.get(api).content)
            danmaku = danmaku.xpath("/i/d")
            ass = """[Script Info]
Title: 弹幕
Original Script: """ + api + """
Script Updated By: https://github.com/xfangfang/Macast-Plugin
Update Details: xml to ass
ScriptType: V4.00+
Collisions: Normal

PlayResX: 638
PlayResY: 447
PlayDepth: 8
Timer: 100.0
WrapStyle: 2


[v4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: dark, sans-serif, 25, &H36FFFFFF, &H36FFFFFF, &H36000000, &H36000000, 1, 0, 0, 0, 100, 100, 0.00, 0.00, 1, 1, 0, 7, 0, 0, 0, 0
Style: light, sans-serif, 25, &H36FFFFFF, &H36FFFFFF, &H36FFFFFF, &H36000000, 1, 0, 0, 0, 100, 100, 0.00, 0.00, 1, 1, 0, 7, 0, 0, 0, 0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

            dms = []
            for i in danmaku:
                a = i.attrib['p'].split(',')
                a.append(i.text)
                dms.append(a)

            dms.sort(key=lambda e: float(e[0]))

            for data in dms:
                text = data[-1]
                danmaku_type = int(data[1])
                danmaku_layer = int(data[5])
                if danmaku_type < 7:
                    start_time = float(data[0])
                    end_time = start_time + exist_time
                    position = create_postion(danmaku_type, danmaku_layer, text, int(data[2]), start_time)
                    style, color = int2color(int(data[3]))
                    comment = f'Dialogue: {danmaku_layer},{sec2str(start_time)},{sec2str(end_time)},' + \
                              f'{style},{data[8]},0000,0000,0000,,{{{position}{color}}}{text}\n'
                    ass += comment
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(ass)
        except Exception as e:
            logger.error(f'Error create sub file: {e}')
            cherrypy.engine.publish('app_notify', 'ERROR', f'Error create sub file: {e}')
            return None

        return file_path


# NVAConectionHandler 负责保持每个客户端的长连接
# 解析和处理NVA协议数据，定时发送心跳包


class NVAConectionBaseHandler:

    def __init__(self, conn, req):
        self.sock = conn
        self.sock_lock = threading.Lock()

        self.counter = 0
        self.counter_lock = threading.Lock()

        self.cache = b''
        self.session = req.headers.get('Session', '')

        self.terminated = False
        self.ping_thread_running = False
        self.ping_thread = None

    def start(self):
        self.ping_thread_running = True
        self.ping_thread = threading.Thread(target=self.send_ping_thread,
                                            name='NVA_PING_THREAD',
                                            daemon=False)
        self.ping_thread.start()

    def cmd_from_client(self, method, counter, params=None):
        pass

    def res_from_client(self, counter, params=None):
        pass

    def terminate(self):
        self.ping_thread_running = False
        self.terminated = True
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except:
                pass
            finally:
                self.sock = None
        self.ping_thread.join()

    def send_ping_thread(self, freq=1):
        logger.info("NVA_PING_THREAD START")
        self.sock.setblocking(True)
        while self.ping_thread_running:
            time.sleep(freq)
            self.send_ping()

        logger.info("NVA_PING_THREAD DONE")

    def send_res(self, counter, data=None):
        logger.info(f"SEND_RES{counter} data:{data}")
        if data is None:
            binary = struct.pack(f">cBI", RET_CMD, 0, counter)
        else:
            data = json.dumps(data, separators=(',', ':')).encode()
            length = len(data)
            binary = struct.pack(f">cB2I{length}s", RET_CMD, 1, counter, length, data)
        logger.debug(f'SEND_RES {binary}')
        self.send(binary)

    def send_ping(self):
        logger.info(f'NVA_PING_THREAD send ping {self.counter}')
        with self.counter_lock:
            self.counter += 1
        binary = struct.pack(f">cBI", PING, 0, self.counter)
        self.send(binary)

    def send_cmd(self, cmd, data=None):
        logger.info(f"SEND_CMD{self.counter} cmd:{cmd} data:{data}")
        with self.counter_lock:
            self.counter += 1
        cmd = cmd.encode()
        cmd_length = len(cmd)

        if data is None:
            binary = struct.pack(f">cBI2B7sB{cmd_length}s", SEND_CMD, 2, self.counter, 1, 7, COMMAND, cmd_length, cmd)
        else:
            data = json.dumps(data, separators=(',', ':')).encode()
            length = len(data)
            binary = struct.pack(f">cBI2B7sB{cmd_length}sI{length}s",
                                 SEND_CMD, 3, self.counter, 1, 7, COMMAND, cmd_length,
                                 cmd, length, data)
        logger.debug(f"SEND_CMD {binary}")
        self.send(binary)

    def send(self, data):
        with self.sock_lock:
            try:
                self.sock.sendall(data)
            except Exception as e:
                logger.error(e)
                logger.error(self)
                # we will handle these socket related errors when receiving datas.
                pass

    def parse_request(self, data):
        index = 0
        self.cache += data
        data = self.cache
        length = len(data)
        while index < length:
            if length - index < 6:  # the smallest package length
                break
            if data[index] not in [SEND_CMD[0], RET_CMD[0]]:
                # wrong header
                index += 1
                continue
            try:
                header, all_l, counter = struct.unpack('>cBI', data[index:index + 6])
                if data[index] == SEND_CMD[0]:
                    assert all_l in [2, 3]
                    if length - index - 6 < 10:
                        break
                    n, cmd_l, cmd_str, method_l = struct.unpack('>BB7sB', data[index + 6:index + 16])
                    assert n == 1 and cmd_l == 7 and cmd_str == COMMAND
                    if all_l == 2:
                        # eg: Command GetVolume
                        if length - index - 16 < method_l:
                            break
                        method = struct.unpack(f'>{method_l}s', data[index + 16:index + 16 + method_l])[0]
                        self.cmd_from_client(method.decode(), counter)
                        index += 16 + method_l
                    else:
                        # eg: Command OnProgress {"duration": 422, "position": 64}
                        if length - index - 16 < method_l + 4:
                            break
                        method, param_l = struct.unpack(f'>{method_l}sI', data[index + 16:index + method_l + 20])
                        if length - index - method_l - 20 < param_l:
                            break
                        params = \
                            struct.unpack(f'>{param_l}s', data[index + method_l + 20:index + method_l + 20 + param_l])[
                                0]
                        try:
                            params = json.loads(params)
                        except Exception as e:
                            # error decode params
                            print(e)
                        else:
                            self.cmd_from_client(method.decode(), counter, params)
                        finally:
                            index += method_l + 20 + param_l
                else:
                    assert all_l in [0, 1]
                    if all_l == 0:
                        # return nothing
                        self.res_from_client(counter)
                        index += 6
                    else:
                        # {"volume": 0}
                        if length - index - 6 < 4:
                            break
                        param_l = struct.unpack(f'>I', data[index + 6:index + 10])[0]
                        if length - index - 10 < param_l:
                            break
                        params = struct.unpack(f'>{param_l}s', data[index + 10:index + 10 + param_l])[0]
                        try:
                            params = json.loads(params)
                        except Exception as e:
                            # error decode params
                            print(e)
                        else:
                            self.res_from_client(counter, params)
                        finally:
                            index += 10 + param_l
            except Exception as e:
                print(e)
                index += 1
                # try to get next batch of data
        self.cache = data[index:]


class NVAConectionHandler(NVAConectionBaseHandler):

    def __init__(self, conn, req):
        super(NVAConectionHandler, self).__init__(conn, req)
        self.session = req.headers.get('Session', '')
        self.uuid = req.headers.get('UUID', '')
        self.playlist = []
        self.sub = os.path.join(SETTING_DIR, 'macast.ass')
        logger.info(f'创建 NVAConectionHandler session:{self.session[-4:]} uuid:{self.uuid[-4:]} {self}')

        self.aid = ''
        self.oid = ''
        self.cid = ''
        self.epid = ''
        self.season_id = ''
        self.access_key = ''
        self.current_qn = 0
        self.desire_qn = 0
        self.desire_speed = 1
        self.qn = {}
        self.playurl_type = 1
        self.content_type = 1
        self.title = ''
        self.title_p = ''
        self.is_portrait = False
        self.danmaku_switch_save = True

    def __del__(self):
        logger.info(f'销毁 NVAConectionHandler session:{self.session[-4:]} uuid:{self.uuid[-4:]} {self}')

    @property
    def renderer(self) -> Renderer:
        renderers = cherrypy.engine.publish('get_renderer')
        if len(renderers) == 0:
            logger.error("Unable to find an available renderer.")
            return Renderer()
        return renderers.pop()

    @property
    def protocol(self) -> Protocol:
        protocols = cherrypy.engine.publish('get_protocol')
        if len(protocols) == 0:
            logger.error("Unable to find an available protocol.")
            return NVAProtocol()
        return protocols.pop()

    def get_video_info(self):
        url = 'https://api.bilibili.com/x/tv/card/view_v2?'
        params = {
            # 'access_key': self.access_key,
            'auto_play': 0,
            'build': 104600,
            'card_type': 2 if self.epid != 0 else 1,
            'fourk': 0,
            'is_ad': 'false',
            'mobi_app': 'android_tv_yst',
            'object_id': self.season_id if self.epid != 0 else self.oid,
            'view_type': 2  # todo 验证参数含义
        }
        url += '&'.join([f'{i}={params[i]}' for i in params])
        play_list = []
        play_index = 0
        try:
            json_text = requests.get(url).text
            json_obj = json.loads(json_text)
            if json_obj['code'] != 0:
                logger.error(f"Error getting video info 1: {json_obj['message']}")
                cherrypy.engine.publish('app_notify', 'ERROR', json_obj['message'])
                raise Exception('error')
            self.title = json_obj['data']['title']
            video_list = json_obj['data']['auto_play']['cid_list']
            for index, video in enumerate(video_list):
                title_p = video.get('title', '')
                if video.get('long_title', '') != '':
                    title_p = video.get('long_title', '')
                play_list.append({
                    'oid': video['playurl_args']['object_id'],
                    'epid': video['playurl_args']['object_id'],
                    'cid': video['playurl_args']['cid'],
                    'aid': video['aid'],
                    'title': title_p,
                    'is_portrait': video['is_portrait']
                })
                if int(self.cid) == int(video['playurl_args']['cid']):
                    play_index = index
                    logger.info(f"当前正在播放 分集{index + 1} {title_p}")
                    self.is_portrait = video['is_portrait']
                    self.renderer.set_media_title(f'{self.title} {title_p}')
        except Exception as e:
            logger.error(f"Error getting video info 2: {e}")
            cherrypy.engine.publish('app_notify', 'ERROR', f"Error getting video info: {e}")
        finally:
            self.protocol.play_list = play_list
            self.protocol.play_index = play_index

    def get_video_url(self) -> (str, dict):

        base_url = 'https://api.bilibili.com/x/tv/playurl?'
        params = {
            'build': 104600,
            'is_proj': 1,
            'device_type': 1,
            'mobi_app': 'android_tv_yst',
            'platform': 'android',
            'fnval': 0,  # 16 | 64 | 128 | 256 # todo 16为dash视频，尝试加载dash视频
            'fnver': 0,
            'fourk': 1,  # allowed 4k
            'playurl_type': self.playurl_type,
            'protocol': 1,
            'cid': self.cid,
            'qn': self.desire_qn,
            'object_id': self.oid,
            'mobile_access_key': self.access_key
        }
        url = base_url + '&'.join(f'{i}={params[i]}' for i in params)

        try:
            res = requests.get(url).text
            res = json.loads(res)

            print(res)

            if res['code'] != 0:
                error_msg = res.get('message', '')
                if error_msg != '':
                    cherrypy.engine.publish('app_notify', 'ERROR', error_msg)
                    print(error_msg, params)
                return None, {}

            qn_support = {}
            qn_extras = res['data'].get('qn_extras', [])
            for i in qn_extras:
                q = i['qn']
                if q not in qn_support:
                    qn_support[q] = {}
                qn_support[q]['quality'] = q
                qn_support[q]['needVip'] = i.get('need_vip', False)
                qn_support[q]['needLogin'] = i.get('need_login', False)
            support_formats = res['data'].get('support_formats', [])
            for i in support_formats:
                q = i['quality']
                if q not in qn_support:
                    qn_support[q] = {}
                qn_support[q]['description'] = i.get('new_description', '')
                qn_support[q]['displayDesc'] = i.get('display_desc', '')
                qn_support[q]['superscript'] = "Macast " + i.get('superscript', '')  # todo: 专有尾巴
            qn_support = [qn_support[i] for i in qn_support]
            self.current_qn = res['data'].get('quality', 0)
            self.qn = {"curQn": self.current_qn,
                       "supportQnList": qn_support,
                       "userDesireQn": self.desire_qn
                       }
            # todo 清晰度切换
            durl = res['data']['durl']
            if durl:
                return durl[0]['url'], self.qn  # todo: fix error when durl have more than one videos

            dash = res['data']['dash']
            if dash:
                return dash['video'][0]['base_url'], self.qn

        except Exception as e:
            logger.error(f'error getting video urls {e}')
            cherrypy.engine.publish('app_notify', 'ERROR', f'error getting video urls {e}')
        return None, {}

    def send_play_cmd(self, url: str, start='0'):
        self.protocol.set_state_url(url)
        self.renderer.set_media_url(url, start)
        self.renderer.set_media_speed(self.desire_speed)
        self.renderer.set_media_title(f'{self.title} {self.title_p}')
        cherrypy.engine.publish('renderer_av_uri', url)
        # 通知客户端，正在加载
        cherrypy.engine.publish('nva-broadcast', 'OnPlayState', {"playState": 3})
        self.update_play_state()

        def get_extra_info():
            logger.info("start get_extra_info")
            DanmakuManager.get_danmaku(self.cid, self.sub)
            self.renderer.set_media_sub_file({
                'url': self.sub,
                'title': '弹幕'
            })
            self.get_video_info()
            logger.info("end get_extra_info")

        threading.Thread(target=get_extra_info).start()

    def update_play_state(self):
        danmuku_open = True
        if self.danmaku_switch_save:
            danmuku_open = bool(self.protocol.get_state_display_subtitle())
        self.renderer.set_media_sub_show(danmuku_open)
        cherrypy.engine.publish('nva-broadcast', 'OnDanmakuSwitch', {'open': danmuku_open})
        cherrypy.engine.publish('nva-broadcast', 'OnEpisodeSwitch',
                                {"playItem": {"aid": self.aid,
                                              "cid": self.cid,
                                              "contentType": self.content_type,
                                              "epId": self.epid,
                                              "seasonId": self.season_id},
                                 "qnDesc": self.qn,
                                 "title": f'{self.title} {self.title_p}'})
        cherrypy.engine.publish('nva-broadcast', 'OnQnSwitch', self.qn)
        current_speed = round(float(self.protocol.get_state_speed()), 2)
        support_speed = [0.5, 0.75, 1, 1.25, 1.5, 2]
        cherrypy.engine.publish('nva-broadcast', 'SpeedChanged',
                                {"currSpeed": current_speed, "supportSpeedList": support_speed})

    def cmd_from_client(self, method, counter, params=None):
        logger.info(f'CMD{counter} method:{method} params{params}')
        if method == 'GetVolume':
            volume = self.protocol.get_state_volume()
            self.send_res(counter, {'volume': volume})
        elif method == 'SetVolume':
            volume = params.get('volume', -1)
            if 0 <= volume <= 100:
                self.renderer.set_media_volume(volume)
        elif method == 'Pause':
            self.send_res(counter)
            self.renderer.set_media_pause()
        elif method == 'Resume':
            self.send_res(counter)
            self.renderer.set_media_resume()
        elif method == 'SendDanmaku':
            # todo 1.发送弹幕，2.通过附字幕实现实时显示
            # 1：滚动
            # 5：上
            # 4：下
            # {'size': 25, 'mRemoteDmId': 1184473088, 'content': '感动', 'action': '', 'type': 1, 'color': 16777215}
            # {'size': 18, 'mRemoteDmId': -1382023168, 'content': '？！', 'action': '', 'type': 4, 'color': 16777215}
            self.send_res(counter)
            self.renderer.set_media_text(f'暂未支持弹幕：{params["content"]}', 4000)
        elif method == 'SwitchDanmaku':
            self.send_res(counter)
            self.renderer.set_media_sub_show(False if params['open'] == 'false' else True)
        elif method == 'SwitchSpeed':
            speed = float(params['speed'])
            self.renderer.set_media_speed(speed)
            self.renderer.set_media_text(f'修改倍速：{speed}X', 2000)
        elif method == 'SwitchQn':
            self.send_res(counter)
            self.desire_qn = params['qn']
            url, qn = self.get_video_url()
            print(f'url: {url}\nqn: {qn}')
            position = self.protocol.get_state_position()
            self.send_play_cmd(url, position)
        elif method == 'Stop':
            self.send_res(counter)
            self.renderer.set_media_stop()
        elif method == 'Play':
            self.send_res(counter)
            self.aid = params['aid']
            self.oid = params['oid']
            self.cid = params['cid']
            self.epid = int(params['epId'])
            self.access_key = params['accessKey']
            self.current_qn = params['userDesireQn']
            self.desire_qn = params['userDesireQn']
            self.content_type = params['contentType']
            self.season_id = int(params['seasonId'])
            self.playurl_type = 1
            self.danmaku_switch_save = params.get('danmakuSwitchSave', True)
            self.desire_speed = float(params['userDesireSpeed'])
            self.title = ''
            if int(params['epId']) != 0:
                # 番剧
                self.oid = params['epId']
                self.playurl_type = 2

            url, qn = self.get_video_url()
            print(f'url: {url}\nqn: {qn}')
            start = params['seekTs']
            self.send_play_cmd(url, start)
        elif method == 'PlayUrl':
            # todo 开始时seek
            self.send_res(counter)
            url = params.get('url', '')
            title = params.get('title', '')
            self.title = title

            video_info = json.loads(parse.parse_qs(url)['nva_ext'][0])
            ver = video_info.get('ver', -1)
            if ver != 2:
                logger.error("Maybe error in url parse")
            params = video_info.get('content', {})
            self.qn = {"curQn": 0,
                       "supportQnList": [{"description": "",
                                          "displayDesc": "",
                                          "needLogin": False,
                                          "needVip": False,
                                          "quality": 0,
                                          "superscript": ""}],
                       "userDesireQn": 0}
            print(params)
            # todo
            self.aid = params['aid']
            self.oid = params['oid']
            self.cid = params['cid']
            self.epid = int(params['epId'])
            self.access_key = params['accessKey']
            self.current_qn = params['quality']
            self.desire_qn = params['userDesireQn']
            self.content_type = params['contentType']
            self.playurl_type = 1
            self.season_id = int(params['seasonId'])
            self.desire_speed = float(params['userDesireSpeed'])
            # todo danmuku switch save
            self.danmaku_switch_save = params.get('danmakuSwitchSave', True)
            if int(params['epId']) != 0:
                # 番剧
                self.oid = params['epId']
                self.playurl_type = 2

            self.send_play_cmd(url, start=params['seekTs'])
        elif method == 'Seek':
            self.send_res(counter)
            position = params.get('seekTs', 0)  # second?
            duration = NVAProtocol.position_to_second(self.protocol.get_state_duration())
            cherrypy.engine.publish('nva-broadcast',
                                    'OnProgress', {"duration": duration,
                                                   "position": position
                                                   })
            position = f'{position // 3600}:{(position % 3600) // 60:02d}:{position % 60:02d}'
            self.renderer.set_media_position(position)
        else:
            self.send_res(counter)

    def res_from_client(self, counter, params=None):
        logger.info(f'RET{counter} params:{params}')

    def terminate(self):
        super(NVAConectionHandler, self).terminate()


# NVATool 负责将tcp长连接从 NVAHTTPServer 中分离，生成 NVAConectionHandler
# NVAHandler 修改自 DLNAHandler，负责HTTP服务的处理
# 增加了NVA协议的相关适配，启动时需调用 reload() 设置后端服务为 NVAHTTPServer


class NVATool(Tool):
    """NVA protocol tools for cherrypy
    """

    def __init__(self):
        Tool.__init__(self, 'before_request_body', self.set_nva_handler)

    def _setup(self):
        conf = self._merged_args()
        hooks = cherrypy.serving.request.hooks
        p = conf.pop("priority", getattr(self.callable, "priority",
                                         self._priority))
        hooks.attach(self._point, self.callable, priority=p, **conf)
        hooks.attach('before_finalize', self.nva_response_header, priority=70)
        hooks.attach('on_end_request', self.nva_start, priority=70)

    def set_nva_handler(self, handler_cls=NVAConectionHandler):
        print("NVATool set_nva_handler")
        request = cherrypy.serving.request
        conn = request.rfile.rfile.raw._sock
        request.nva_handler = handler_cls(conn, request)

    def nva_start(self):
        request = cherrypy.request
        if not hasattr(request, 'nva_handler'):
            return

        nva_handler = request.nva_handler
        request.nva_handler = None
        delattr(request, 'nva_handler')

        # By doing this we detach the socket from the CherryPy stack avoiding memory leaks
        request.rfile.rfile.detach()

        print("NVATool nva_start", nva_handler, request.remote.ip, request.remote.port)

        if request.method == 'SETUP':
            cherrypy.engine.publish('nva-add', nva_handler)
        else:
            cherrypy.engine.publish('nva-restore', nva_handler)

    def nva_response_header(self):
        cherrypy.response.headers['Session'] = cherrypy.request.headers.get('Session', '')
        cherrypy.response.headers['UUID'] = Setting.get_usn()
        cherrypy.response.headers['NvaVersion'] = '1'


cherrypy.tools.nva = NVATool()


@cherrypy.expose
class NVAHandler(DLNAHandler):
    def reload(self):
        cherrypy.server.httpserver = NVAHTTPServer(cherrypy.server)
        self.build_description()

    def build_description(self):
        self.description = load_xml(XMLPath.DESCRIPTION.value).format(
            friendly_name='我的小电视',
            manufacturer="Bilibili Inc.",
            manufacturer_url="https://bilibili.com/",
            model_description="云视听小电视",
            model_name="Macast",
            model_url="https://app.bilibili.com/",
            model_number=Setting.get_version(),
            uuid=Setting.get_usn(),
            serial_num=1024,
            header_extra="""<X_brandName>Macast</X_brandName>
        <hostVersion>25</hostVersion>
        <ottVersion>104600</ottVersion>
        <channelName>master</channelName>
        <capability>254</capability>""",
            service_extra="""<service>
                <serviceType>urn:app-bilibili-com:service:NirvanaControl:3</serviceType>
                <serviceId>urn:app-bilibili-com:serviceId:NirvanaControl</serviceId>
                <controlURL>NirvanaControl/action</controlURL>
                <eventSubURL>NirvanaControl/event</eventSubURL>
                <SCPDURL>dlna/NirvanaControl.xml</SCPDURL>
            </service>"""
        ).encode()

    def GET(self, param=None, xml=None, **kwargs):
        if param == 'dlna' and xml == 'NirvanaControl.xml':
            return NVA_SERVICE
        return super(NVAHandler, self).GET(param, xml, **kwargs)

    @cherrypy.tools.nva()
    def SETUP(self, p):
        logger.info(f'SETUP ----{p}')
        print(cherrypy.request.headers)

    @cherrypy.tools.nva()
    def RESTORE(self, p):
        logger.info(f'RESTORE ----{p}')
        print(cherrypy.request.headers)

    @cherrypy.tools.nva()
    def STARTRESTORE(self, p):
        logger.info(f'STARTRESTORE ----{p}')
        print(cherrypy.request.headers)


# NVA 协议主要代码


class SelectPoller(object):
    """ copy from ws4py.manager.SelectPoller

    """

    def __init__(self, timeout=0.1):
        """
        A socket poller that uses the `select`
        implementation to determines which
        file descriptors have data available to read.

        It is available on all platforms.
        """
        self._fds = []
        self.timeout = timeout

    def release(self):
        """
        Cleanup resources.
        """
        self._fds = []

    def register(self, fd):
        """
        Register a new file descriptor to be
        part of the select polling next time around.
        """
        if fd not in self._fds:
            self._fds.append(fd)

    def unregister(self, fd):
        """
        Unregister the given file descriptor.
        """
        if fd in self._fds:
            self._fds.remove(fd)

    def poll(self):
        """
        Polls once and returns a list of
        ready-to-be-read file descriptors.
        """
        if not self._fds:
            time.sleep(self.timeout)
            return []
        try:
            r, w, x = select.select(self._fds, [], [], self.timeout)
        except IOError as e:
            return []
        return r


class NVAProtocol(DLNAProtocol):
    """
    Some code is from ws4py.manager.WebSocketManager
    """

    def __init__(self):
        super(NVAProtocol, self).__init__()
        self.nva_manager = None
        self.lock = threading.Lock()
        self.clients = {}
        self.poller = SelectPoller(timeout=0.5)

        self.media_playing = False
        self.play_list = []  # [{oid:'', cid:'', title:'', is_portrait: false}...]
        self.play_index = 0

    def start(self):
        super(NVAProtocol, self).start()
        self.nva_manager = threading.Thread(target=self.run_manager,
                                            name="NVA_MANAGER_THREAD",
                                            daemon=True)
        self.nva_manager.start()
        cherrypy.engine.subscribe('nva-add', self.add)
        cherrypy.engine.subscribe('nva-broadcast', self.broadcast)
        cherrypy.engine.subscribe('nva-restore', self.restore)

    def stop(self):
        super(NVAProtocol, self).stop()
        cherrypy.engine.unsubscribe('nva-add', self.add)
        cherrypy.engine.unsubscribe('nva-broadcast', self.broadcast)
        cherrypy.engine.unsubscribe('nva-restore', self.restore)
        with self.lock:
            for fd in self.clients:
                self.clients[fd].terminate()
            self.clients.clear()
            self.poller.release()

    def restore(self, nva: NVAConectionHandler):
        self.add(nva)
        with self.lock:
            clients = self.clients.copy()
            nva_iter = iter(clients.values())

        for nva in nva_iter:
            if not nva.terminated:
                nva.update_play_state()

    def remove(self, nva: NVAConectionHandler):
        if nva not in self.clients:
            return
        logger.info(f"NVA Client {nva} leave.")
        with self.lock:
            fd = nva.sock.fileno()
            self.clients.pop(fd, None)
            self.poller.unregister(fd)
            nva.terminate()

    def add(self, nva: NVAConectionHandler):
        if nva in self.clients:
            return
        logger.info(f"NVA Client {nva} added.")
        with self.lock:
            new_fd = nva.sock.fileno()
            self.poller.register(new_fd)
            uuid = nva.uuid
            session = nva.session
            clients_remove_list = []
            for fd in self.clients:
                if self.clients[fd].uuid == uuid:
                    # 曾经连接过的设备重新连接
                    if self.clients[fd].session == session:
                        logger.info('设备断线重连：恢复之前的session')
                        # 恢复之前的session：手机断连，恢复session
                        # 移除旧连接
                        clients_remove_list.append(fd)
                        self.clients[fd].terminate()
                        # 将新的socket转移到旧连接上
                        self.clients[new_fd] = self.clients[fd]
                        self.clients[new_fd].sock = nva.sock
                        self.clients[new_fd].counter = 0
                        self.clients[new_fd].terminated = False
                    else:
                        # 新的session：手机应用重启，重新投屏
                        # 移除旧连接
                        logger.info('设备断线重连：移除旧连接')
                        clients_remove_list.append(fd)
                        self.clients[fd].terminate()
                        # 添加新的连接
                        self.clients[new_fd] = nva
                    break
            else:
                # 新设备连接
                logger.info('新设备连接')
                self.clients[new_fd] = nva

            for fd in clients_remove_list:
                self.poller.unregister(fd)
                self.clients.pop(fd, None)

            # 启动ping线程
            logger.info("启动ping线程")
            self.clients[new_fd].start()

    def broadcast(self, cmd, params=None):
        with self.lock:
            clients = self.clients.copy()
            nva_iter = iter(clients.values())

        for nva in nva_iter:
            if not nva.terminated:
                try:
                    nva.send_cmd(cmd, params)
                except:
                    pass

    def set_playlist(self, play_list, play_index):
        self.play_index = play_index
        self.play_list = play_list

    @staticmethod
    def position_to_second(position: str) -> int:
        pos = position.split(':')
        if len(pos) < 3:
            return 0
        return int(pos[0]) * 3600 + int(pos[1]) * 60 + int(pos[2])

    def set_state_position(self, data: str):
        """
        :param data: string, eg: 00:00:00
        :return:
        """

        if data != self.get_state_position():
            position = self.position_to_second(data)
            duration = self.position_to_second(self.get_state_duration())
            if duration > 0:
                self.broadcast('OnProgress',
                               {"duration": duration,
                                "position": position
                                })
        super(NVAProtocol, self).set_state_position(data)

    # todo 直播时 总时长会不断增加，其实直播时无须返回时长信息
    # 目前nva协议并没有涉及直播投放
    def set_state_duration(self, data: str):
        """
        :param data: string, eg: 00:00:00
        :return:
        """
        if data != self.get_state_duration():
            duration = self.position_to_second(data)
            if duration > 0:
                # 有时候播放器初始化时会设置duration为0，这时候不需要发送给客户端
                position = self.position_to_second(self.get_state_position())
                self.broadcast('OnProgress',
                               {"duration": duration,
                                "position": position
                                })
        super(NVAProtocol, self).set_state_duration(data)

    def set_state_transport(self, data: str):
        super(NVAProtocol, self).set_state_transport(data)
        # 以下对playState的猜测，暂未得到确切验证
        # 3 加载中
        # 4 播放中
        # 5 暂停
        # 6 媒体播放结束 end of file
        # 7 停止
        if data == 'PLAYING':
            self.broadcast('OnPlayState', {"playState": 4})
            if not self.media_playing:
                # 播放成功
                self.broadcast('PLAY_SUCCESS')
                self.media_playing = True
            return
        elif data == 'PAUSED_PLAYBACK':
            self.broadcast('OnPlayState', {"playState": 5})
            return
        elif data == 'STOPPED':
            self.broadcast('OnPlayState', {"playState": 7})
        elif data == 'NO_MEDIA_PRESENT':
            self.broadcast('OnPlayState', {"playState": 6})
            self.play_index += 1
            if self.play_index < len(self.play_list):
                logger.info(f"准备播放 分集{self.play_index + 1} {self.play_list[self.play_index]}")
                # 切换下一集
                with self.lock:
                    clients = self.clients.copy()
                    nva_iter = iter(clients.values())
                next_video = self.play_list[self.play_index]
                for nva in nva_iter:
                    if nva:
                        nva.cid = next_video['cid']
                        nva.oid = nva.aid = next_video['aid']
                        if next_video['epid'] != 0:
                            nva.oid = nva.epid = next_video['epid']
                        nva.title_p = next_video['title']
                        url, qn = nva.get_video_url()
                        print(f'url: {url}\nqn: {qn}')
                        nva.send_play_cmd(url)
                        break
                else:
                    logger.error("客户端断开连接，播放结束")

            else:
                logger.info(f'分集{self.play_index} {self.play_list}')
                logger.info("没有下一集，播放结束")
        self.media_playing = False

        # 不同播放状态应返回的 playState 序列

        # 播放一条视频
        # 加载中(3)、播放(4)、播放成功(PLAY_SUCCESS)

        # 分集1播放完毕，自动播放分集2
        # 媒体播放结束(6)、加载下一条视频(3)、播放(4)、播放成功(PLAY_SUCCESS)
        # MPVRenderer实现的顺序  媒体播放结束(6)、播放停止(7)、加载下一条视频(3)、播放(4)、播放成功(PLAY_SUCCESS)

        # 当所有分集播放完毕时
        # 播放停止(7)、媒体播放结束(6)、加载推荐视频(3)、播放(4)、播放成功(PLAY_SUCCESS)
        # MPVRenderer实现的顺序：媒体播放结束(6)、播放停止(7)

        # 在正在播放时，切投其他视频
        # 暂停(5)、播放(4)、加载中(3)、播放(4)、播放成功(PLAY_SUCCESS)
        # MPVRenderer实现的顺序实现的顺序：停止(7)、加载中(3)、播放(4)、播放成功(PLAY_SUCCESS)

    def set_state_transport_error(self):
        """
        :return:
        """
        super(NVAProtocol, self).set_state_transport_error()
        self.broadcast('OnPlayState', {"playState": 3})

    # todo 反向控制手机静音/貌似没有这个功能
    def set_state_mute(self, data: bool):
        """
        :param data: bool
        :return:
        """
        super(NVAProtocol, self).set_state_mute(data)

    # todo 反向控制手机音量/貌似没有这个功能
    def set_state_volume(self, data: int):
        """
        :param data: int, range from 0 to 100
        :return:
        """
        super(NVAProtocol, self).set_state_volume(data)

    def set_state_speed(self, data: str):
        super(NVAProtocol, self).set_state_speed(data)
        current_speed = round(float(data), 2)
        support_speed = [0.5, 0.75, 1, 1.25, 1.5, 2]
        self.broadcast('SpeedChanged',
                       {"currSpeed": current_speed, "supportSpeedList": support_speed})

    def set_state_display_subtitle(self, data: bool):
        super(NVAProtocol, self).set_state_display_subtitle(data)
        self.broadcast('OnDanmakuSwitch',
                       {'open': data})

    def run_manager(self):
        while self.running:
            with self.lock:
                polled = self.poller.poll()
            logger.debug(f'polled {polled}')
            if not self.running:
                break
            for fd in polled:
                if not self.running:
                    break
                nva = self.clients.get(fd, None)
                if nva and not nva.terminated:
                    try:
                        data = nva.sock.recv(2048)
                        if data == b'':
                            raise Exception('socket received null data')
                        nva.parse_request(data)
                    except (socket.error, OSError, Exception) as e:
                        if hasattr(e, "errno") and e.errno == errno.EINTR:
                            logger.error("socket: errno.EINTR")
                            pass
                        else:
                            logger.error(f"ERROR received data: {e}")
                            nva.terminate()
                            with self.lock:
                                self.poller.unregister(fd)
                            # todo 移除长时间未连接的客户端
                            # 下面的注释代码是立刻移除断开连接的客户端
                            # 但是立刻移除会导致意外断开连接的客户端无法完成重连
                            # 当断开连接的客户端数量过多时可能会导致内存占用小幅增加
                            # 不过日常使用的情况影响不大，所以暂时先不处理这个问题
                            # with self.lock:
                            #     self.clients.pop(fd, None)
                            #     self.poller.unregister(fd)
                else:
                    logger.debug(f'retained clients {self.clients}')
                del nva

    @property
    def handler(self):
        if self._handler is None:
            self._handler = NVAHandler()
        return self._handler

    def init_services(self, description=XMLPath.DESCRIPTION.value):
        super(NVAProtocol, self).init_services()
        self.build_action('urn:app-bilibili-com:service:NirvanaControl:3',
                          'NirvanaControl',
                          etree.fromstring(NVA_SERVICE))


if __name__ == '__main__':
    from macast import cli
    from macast_renderer.mpv import MPVRenderer

    cli(renderer=MPVRenderer(path='mpv'), protocol=NVAProtocol())
