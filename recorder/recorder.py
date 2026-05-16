#
# Macast 录制插件 - 使用FFmpeg录制DLNA流媒体
#
# Macast Metadata
# <macast.title>Recording Renderer</macast.title>
# <macast.renderer>RecordingRenderer</macast.renderer>
# <macast.platform>darwin,linux,win32</macast.platform>
# <macast.version>1.0</macast.version>
# <macast.host_version>0.7</macast.host_version>
# <macast.author>The Flash</macast.author>
# <macast.desc>基于FFmpeg的DLNA流媒体录制器。在播放的同时将媒体录制为MP4（H.264+AAC）格式。点击可配置保存路径并查看录制状态。</macast.desc>


import os
import sys
import time
import json
import shutil
import signal
import logging
import threading
import subprocess
import cherrypy
import gettext
from datetime import datetime
from enum import Enum
from pathlib import Path

from macast import gui, Setting, MenuItem
from macast.renderer import Renderer, RendererSetting
from macast.utils import SETTING_DIR

logger = logging.getLogger("RecordingRenderer")
logger.setLevel(logging.DEBUG)


class RecordingState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    STOPPED = "stopped"
    ERROR = "error"


class SettingProperty(Enum):
    Record_SavePath = 1000
    Record_AutoStart = 1001
    Record_VideoBitrate = 1002
    Record_AudioBitrate = 1003
    Record_FFmpegPath = 1004


class FFmpegRecorder:
    """基于FFmpeg的媒体录制器"""

    def __init__(self):
        self.process = None
        self.state = RecordingState.IDLE
        self.start_time = None
        self.output_path = None
        self.save_directory = Setting.get(SettingProperty.Record_SavePath, str(Path.home()))
        self.video_bitrate = Setting.get(SettingProperty.Record_VideoBitrate, "6000k")
        self.audio_bitrate = Setting.get(SettingProperty.Record_AudioBitrate, "192k")
        self.custom_ffmpeg_path = Setting.get(SettingProperty.Record_FFmpegPath, "")
        self._lock = threading.Lock()
        self.duration_seconds = 0
        self.file_size_bytes = 0
        self._monitor_thread = None
        self._monitor_running = False
        self._ffmpeg_log_path = None

    def _generate_filename(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}.mp4"

    def _get_ffmpeg_path(self):
        """获取FFmpeg可执行文件路径
        
        查找优先级：
        1. 用户自定义路径（通过设置配置）
        2. 项目内置FFmpeg目录
        3. 系统PATH环境变量
        4. 默认命令名 "ffmpeg"
        """
        if self.custom_ffmpeg_path:
            if os.path.isfile(self.custom_ffmpeg_path):
                if os.access(self.custom_ffmpeg_path, os.X_OK):
                    logger.info(f"使用自定义FFmpeg路径: {self.custom_ffmpeg_path}")
                    return self.custom_ffmpeg_path
                else:
                    logger.warning(f"自定义FFmpeg路径存在但不可执行: {self.custom_ffmpeg_path}")
            elif os.path.isdir(self.custom_ffmpeg_path):
                if sys.platform == 'win32':
                    ffmpeg_in_dir = os.path.join(self.custom_ffmpeg_path, "ffmpeg.exe")
                else:
                    ffmpeg_in_dir = os.path.join(self.custom_ffmpeg_path, "ffmpeg")
                if os.path.isfile(ffmpeg_in_dir) and os.access(ffmpeg_in_dir, os.X_OK):
                    logger.info(f"使用自定义目录中的FFmpeg: {ffmpeg_in_dir}")
                    return ffmpeg_in_dir
                else:
                    logger.warning(f"自定义目录中未找到FFmpeg可执行文件: {self.custom_ffmpeg_path}")
            else:
                logger.warning(f"自定义FFmpeg路径不存在: {self.custom_ffmpeg_path}")

        parent_dir = os.path.dirname(os.path.dirname(__file__))
        
        if sys.platform == 'win32':
            ffmpeg_dir = os.path.join(parent_dir, "ffmpeg-2026-05-13-git-a327bc0561-full_build", "bin")
            ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
            if os.path.isfile(ffmpeg_exe):
                logger.info(f"使用内置FFmpeg: {ffmpeg_exe}")
                return ffmpeg_exe
        else:
            possible_dirs = [
                os.path.join(parent_dir, "ffmpeg", "bin"),
                os.path.join(parent_dir, "bin"),
                os.path.join(parent_dir, "..", "ffmpeg-2026-05-13-git-a327bc0561-full_build", "bin"),
            ]
            for ffmpeg_dir in possible_dirs:
                ffmpeg_bin = os.path.join(ffmpeg_dir, "ffmpeg")
                if os.path.isfile(ffmpeg_bin) and os.access(ffmpeg_bin, os.X_OK):
                    logger.info(f"使用内置FFmpeg: {ffmpeg_bin}")
                    return ffmpeg_bin

        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            logger.info(f"使用系统PATH中的FFmpeg: {ffmpeg_in_path}")
            return ffmpeg_in_path

        logger.warning("未找到FFmpeg路径，使用默认命令名 'ffmpeg'")
        return "ffmpeg"

    def verify_ffmpeg(self):
        """验证FFmpeg是否可用，返回(可用, 错误信息)"""
        ffmpeg_path = self._get_ffmpeg_path()
        try:
            startupinfo = None
            creation_flags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creation_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                [ffmpeg_path, '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                startupinfo=startupinfo,
                creationflags=creation_flags
            )
            if result.returncode == 0:
                version_line = result.stdout.decode('utf-8', errors='ignore').split('\n')[0]
                logger.info(f"FFmpeg验证通过: {version_line}")
                return True, version_line
            else:
                error = result.stderr.decode('utf-8', errors='ignore')
                return False, f"FFmpeg返回错误: {error[:200]}"
        except FileNotFoundError:
            return False, f"未在以下路径找到FFmpeg: {ffmpeg_path}"
        except subprocess.TimeoutExpired:
            return False, "FFmpeg验证超时"
        except Exception as e:
            return False, f"FFmpeg验证失败: {str(e)}"

    def start_recording(self, url, title=None):
        with self._lock:
            if self.state == RecordingState.RECORDING:
                logger.warning("正在录制中")
                return False

            ffmpeg_ok, ffmpeg_err = self.verify_ffmpeg()
            if not ffmpeg_ok:
                logger.error(f"FFmpeg不可用: {ffmpeg_err}")
                self.state = RecordingState.ERROR
                return False

            if not os.path.exists(self.save_directory):
                try:
                    os.makedirs(self.save_directory, exist_ok=True)
                except Exception as e:
                    logger.error(f"无法创建保存目录: {e}")
                    self.state = RecordingState.ERROR
                    return False

            filename = self._generate_filename()
            if title:
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                if safe_title:
                    filename = f"{safe_title}_{filename}"

            self.output_path = os.path.join(self.save_directory, filename)

            ffmpeg_path = self._get_ffmpeg_path()
            cmd = [
                ffmpeg_path,
                '-y',
                '-user_agent', 'Macast/1.0 DLNA Recorder',
                '-i', url,
                '-c:v', 'libx264',
                '-b:v', self.video_bitrate,
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', self.audio_bitrate,
                '-movflags', '+faststart',
                '-f', 'mp4',
                self.output_path
            ]

            logger.info(f"开始FFmpeg录制: {url}")
            logger.info(f"输出路径: {self.output_path}")
            logger.info(f"执行命令: {' '.join(cmd)}")

            ffmpeg_log_file = None
            try:
                self._ffmpeg_log_path = os.path.join(self.save_directory, f".{filename}.ffmpeg.log")
                ffmpeg_log_file = open(self._ffmpeg_log_path, 'wb')

                startupinfo = None
                creation_flags = 0
                if sys.platform == 'win32':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creation_flags = subprocess.CREATE_NO_WINDOW

                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=ffmpeg_log_file,
                    startupinfo=startupinfo,
                    creationflags=creation_flags
                )
                self._ffmpeg_log_file = ffmpeg_log_file
                ffmpeg_log_file = None

                time.sleep(1.0)
                if self.process.poll() is not None:
                    self._close_ffmpeg_log()
                    error_msg = self._read_ffmpeg_log()
                    logger.error(f"FFmpeg启动后立即退出，退出码 {self.process.returncode}: {error_msg}")
                    self.state = RecordingState.ERROR
                    return False

                self.state = RecordingState.RECORDING
                self.start_time = time.time()
                self._monitor_running = True
                self._monitor_thread = threading.Thread(
                    target=self._monitor_process,
                    name="FFMPEG_MONITOR_THREAD",
                    daemon=True
                )
                self._monitor_thread.start()
                logger.info(f"录制已开始: {filename}")
                return True
            except FileNotFoundError as e:
                logger.error(f"未找到FFmpeg可执行文件: {e}")
                self.state = RecordingState.ERROR
                if ffmpeg_log_file:
                    ffmpeg_log_file.close()
                return False
            except Exception as e:
                logger.error(f"启动FFmpeg失败: {e}")
                self.state = RecordingState.ERROR
                if ffmpeg_log_file:
                    ffmpeg_log_file.close()
                return False

    def _monitor_process(self):
        while self._monitor_running and self.process:
            try:
                if self.process.poll() is not None:
                    self._close_ffmpeg_log()
                    if self.process.returncode != 0 and self.state == RecordingState.RECORDING:
                        error_msg = self._read_ffmpeg_log()
                        logger.error(f"FFmpeg异常退出，退出码 {self.process.returncode}: {error_msg}")
                        self.state = RecordingState.ERROR
                        if self.output_path and os.path.exists(self.output_path):
                            file_size = os.path.getsize(self.output_path)
                            if file_size < 1024:
                                logger.warning("输出文件过小，录制可能失败")
                                try:
                                    os.remove(self.output_path)
                                    logger.info(f"已删除无效输出文件: {self.output_path}")
                                except:
                                    pass
                    else:
                        self.state = RecordingState.STOPPED
                    if self.output_path and os.path.exists(self.output_path):
                        self.file_size_bytes = os.path.getsize(self.output_path)
                    self._monitor_running = False
                    break
                if self.start_time:
                    self.duration_seconds = time.time() - self.start_time
                if self.output_path and os.path.exists(self.output_path):
                    self.file_size_bytes = os.path.getsize(self.output_path)
            except Exception as e:
                logger.error(f"监控线程错误: {e}")
            time.sleep(0.5)

    def _close_ffmpeg_log(self):
        if hasattr(self, '_ffmpeg_log_file') and self._ffmpeg_log_file:
            try:
                self._ffmpeg_log_file.close()
            except:
                pass
            self._ffmpeg_log_file = None

    def _read_ffmpeg_log(self):
        if self._ffmpeg_log_path and os.path.exists(self._ffmpeg_log_path):
            try:
                file_size = os.path.getsize(self._ffmpeg_log_path)
                if file_size == 0:
                    return "FFmpeg日志为空（FFmpeg可能未能启动或在写入输出前崩溃）"
                with open(self._ffmpeg_log_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    last_lines = content.strip().split('\n')[-30:]
                    return '\n'.join(last_lines)
            except Exception as e:
                return f"无法读取FFmpeg日志: {e}"
        return "FFmpeg日志文件不可用"

    def stop_recording(self):
        with self._lock:
            if self.state != RecordingState.RECORDING:
                return

            logger.info("正在停止录制")
            self._monitor_running = False

            if self.process:
                try:
                    try:
                        self.process.stdin.write(b'q')
                        self.process.stdin.flush()
                        logger.info("已向FFmpeg发送 'q' 命令进行优雅停止")
                    except:
                        pass

                    try:
                        self.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        logger.warning("FFmpeg未能优雅停止，正在发送SIGINT信号")
                        try:
                            if sys.platform == 'win32':
                                self.process.send_signal(signal.CTRL_BREAK_EVENT)
                            else:
                                self.process.send_signal(signal.SIGINT)
                            self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            logger.warning("FFmpeg未响应SIGINT信号，正在强制终止")
                            self.process.terminate()
                            self.process.wait(timeout=3)
                except Exception as e:
                    logger.error(f"停止FFmpeg时出错: {e}")
                    try:
                        self.process.kill()
                    except:
                        pass

            self._close_ffmpeg_log()

            if self.output_path and os.path.exists(self.output_path):
                self.file_size_bytes = os.path.getsize(self.output_path)
                if self.file_size_bytes < 1024:
                    logger.warning(f"输出文件过小 ({self.file_size_bytes} 字节)，录制可能失败")
                    self.state = RecordingState.ERROR
                    return

            self.state = RecordingState.STOPPED
            logger.info(f"录制已停止: {self.output_path}")
            logger.info(f"时长: {self.format_duration()}, 大小: {self.format_size()}")

    def get_status(self):
        return {
            'state': self.state.value,
            'duration': self.format_duration(),
            'size': self.format_size(),
            'output_path': self.output_path,
            'is_recording': self.state == RecordingState.RECORDING
        }

    def format_duration(self):
        if not self.start_time:
            return "00:00:00"
        total_seconds = int(self.duration_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def format_size(self):
        if self.file_size_bytes < 1024:
            return f"{self.file_size_bytes} B"
        elif self.file_size_bytes < 1024 * 1024:
            return f"{self.file_size_bytes / 1024:.1f} KB"
        elif self.file_size_bytes < 1024 * 1024 * 1024:
            return f"{self.file_size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def cleanup(self):
        self._monitor_running = False
        if self.process and self.process.poll() is None:
            try:
                try:
                    self.process.stdin.write(b'q')
                    self.process.stdin.flush()
                except:
                    pass
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
        self._close_ffmpeg_log()


class RecordingRenderer(Renderer):
    """在播放媒体的同时进行录制的DLNA渲染器"""

    def __init__(self, lang=gettext.gettext):
        global _
        _ = lang
        super(RecordingRenderer, self).__init__(lang)
        self.recorder = FFmpegRecorder()
        self.current_url = None
        self.current_title = None
        self.last_url = None
        self.last_title = None
        self.playback_position = 0
        self.position_thread_running = True
        self.position_thread = threading.Thread(
            target=self.position_tick,
            daemon=True,
            name="POSITION_TICK_THREAD"
        )
        self.position_thread.start()
        self.renderer_setting = RecordingRendererSetting()
        self.status_update_thread = None
        self.status_update_running = False

    def position_tick(self):
        while self.position_thread_running:
            time.sleep(1)
            if self.recorder.state == RecordingState.RECORDING:
                self.playback_position += 1
                sec = self.playback_position
                position = '%d:%02d:%02d' % (sec // 3600, (sec % 3600) // 60, sec % 60)
                self.set_state_position(position)

    def set_media_url(self, url, start="0"):
        self.current_url = url
        self.last_url = url
        self.playback_position = 0
        logger.info(f"收到媒体URL: {url}")
        cherrypy.engine.publish('renderer_av_uri', url)
        self.set_state_transport("PLAYING")
        auto_start = Setting.get(SettingProperty.Record_AutoStart, 1)
        if auto_start:
            threading.Thread(
                target=self._start_recording_with_title,
                kwargs={'url': url},
                daemon=True,
                name="AUTO_RECORD_THREAD"
            ).start()

    def _start_recording_with_title(self, url):
        time.sleep(0.5)
        title = self.current_title or self.last_title
        try:
            title = title or self.protocol.get_state_title()
        except Exception:
            pass
        success = self.recorder.start_recording(url, title=title)
        if success:
            self._start_status_update()
            cherrypy.engine.publish('app_notify',
                                    _('录制已开始'),
                                    _('录制: {}').format(title or _('未知')))
        else:
            status = self.recorder.get_status()
            error_detail = status.get('output_path', '')
            cherrypy.engine.publish('app_notify',
                                    _('录制失败'),
                                    _('无法开始录制，请检查FFmpeg安装及日志文件。'))

    def set_media_title(self, data):
        self.current_title = data
        self.last_title = data
        logger.info(f"媒体标题: {data}")

    def set_media_stop(self):
        if self.recorder.state == RecordingState.RECORDING:
            self.recorder.stop_recording()
            self._stop_status_update()
            status = self.recorder.get_status()
            cherrypy.engine.publish('app_notify',
                                    _('录制完成'),
                                    _('时长: {}, 大小: {}').format(status['duration'], status['size']))
        self.playback_position = 0
        self.current_url = None
        self.current_title = None
        self.set_state_transport('STOPPED')
        cherrypy.engine.publish('renderer_av_stop')

    def set_media_pause(self):
        logger.info("播放已暂停")
        self.set_state_pause()

    def set_media_resume(self):
        logger.info("播放已恢复")
        self.set_state_play()

    def _start_status_update(self):
        self.status_update_running = True
        self.status_update_thread = threading.Thread(
            target=self._status_update_loop,
            daemon=True,
            name="STATUS_UPDATE_THREAD"
        )
        self.status_update_thread.start()

    def _stop_status_update(self):
        self.status_update_running = False

    def _status_update_loop(self):
        while self.status_update_running:
            if self.recorder.state == RecordingState.RECORDING:
                status = self.recorder.get_status()
                cherrypy.engine.publish('recording_status_update', status)
            time.sleep(1)

    def get_recording_status(self):
        return self.recorder.get_status()

    def manual_start_recording(self):
        url = self.current_url or self.last_url
        title = self.current_title or self.last_title
        if url:
            if self.recorder.start_recording(url, title=title):
                self._start_status_update()
                cherrypy.engine.publish('app_notify',
                                        _('录制已开始'),
                                        _('录制: {}').format(title or _('未知')))
                return True
        cherrypy.engine.publish('app_notify',
                                _('错误'),
                                _('当前没有正在播放的媒体'))
        return False

    def manual_stop_recording(self):
        if self.recorder.state == RecordingState.RECORDING:
            self.recorder.stop_recording()
            self._stop_status_update()
            status = self.recorder.get_status()
            cherrypy.engine.publish('app_notify',
                                    _('录制完成'),
                                    _('时长: {}, 大小: {}').format(status['duration'], status['size']))
            return True
        return False

    def stop(self):
        super(RecordingRenderer, self).stop()
        self.position_thread_running = False
        self.recorder.cleanup()
        self._stop_status_update()
        logger.info("录制渲染器已停止")

    def start(self):
        super(RecordingRenderer, self).start()
        logger.info("录制渲染器已启动")


class RecordingRendererSetting(RendererSetting):
    def __init__(self):
        Setting.load()
        self.savePathItem = None
        self.autoStartItem = None
        self.recordingStatusItem = None
        self.startRecordItem = None
        self.stopRecordItem = None
        self.ffmpegPathItem = None
        self.setting_save_path = Setting.get(SettingProperty.Record_SavePath, str(Path.home()))
        self.setting_auto_start = Setting.get(SettingProperty.Record_AutoStart, 1)
        self.setting_ffmpeg_path = Setting.get(SettingProperty.Record_FFmpegPath, "")

    def build_menu(self):
        self.recordingStatusItem = MenuItem(
            _("录制: 空闲"),
            enabled=False
        )
        self.startRecordItem = MenuItem(
            _("开始录制"),
            self.on_start_record_clicked
        )
        self.stopRecordItem = MenuItem(
            _("停止录制"),
            self.on_stop_record_clicked,
            enabled=False
        )
        self.autoStartItem = MenuItem(
            _("投屏时自动录制"),
            self.on_auto_start_clicked,
            checked=self.setting_auto_start
        )
        self.savePathItem = MenuItem(
            _("保存路径: {}").format(self._shorten_path(self.setting_save_path)),
            self.on_save_path_clicked
        )
        self.ffmpegPathItem = MenuItem(
            _("FFmpeg路径: {}").format(self._shorten_ffmpeg_path(self.setting_ffmpeg_path)),
            self.on_ffmpeg_path_clicked
        )
        return [
            self.recordingStatusItem,
            None,
            self.startRecordItem,
            self.stopRecordItem,
            None,
            self.autoStartItem,
            self.savePathItem,
            self.ffmpegPathItem,
        ]

    def _shorten_path(self, path, max_len=30):
        if len(path) <= max_len:
            return path
        p = Path(path)
        name = p.name
        parent = p.parent.name
        return f".../{parent}/{name}"

    def _shorten_ffmpeg_path(self, path, max_len=30):
        if not path:
            return _("自动检测")
        if len(path) <= max_len:
            return path
        p = Path(path)
        return f".../{p.name}"

    def _update_recording_status_menu(self, status):
        if self.recordingStatusItem:
            if status['is_recording']:
                self.recordingStatusItem.text = _("录制: {} - {}").format(
                    status['duration'], status['size'])
                if self.startRecordItem:
                    self.startRecordItem.enabled = False
                if self.stopRecordItem:
                    self.stopRecordItem.enabled = True
            else:
                self.recordingStatusItem.text = _("录制: 空闲")
                if self.startRecordItem:
                    self.startRecordItem.enabled = True
                if self.stopRecordItem:
                    self.stopRecordItem.enabled = False

    def on_start_record_clicked(self, item):
        renderer = cherrypy.engine.publish('get_renderer')
        if renderer:
            r = renderer.pop()
            if hasattr(r, 'manual_start_recording'):
                r.manual_start_recording()

    def on_stop_record_clicked(self, item):
        renderer = cherrypy.engine.publish('get_renderer')
        if renderer:
            r = renderer.pop()
            if hasattr(r, 'manual_stop_recording'):
                r.manual_stop_recording()

    def on_auto_start_clicked(self, item):
        item.checked = not item.checked
        self.setting_auto_start = 1 if item.checked else 0
        Setting.set(SettingProperty.Record_AutoStart, self.setting_auto_start)

    def on_save_path_clicked(self, item):
        renderer = cherrypy.engine.publish('get_renderer')
        current_path = self.setting_save_path
        if renderer:
            r = renderer.pop()
            if hasattr(r, 'recorder'):
                current_path = r.recorder.save_directory
        new_path = self._show_path_dialog(current_path)
        if new_path and os.path.exists(new_path):
            self.setting_save_path = new_path
            Setting.set(SettingProperty.Record_SavePath, self.setting_save_path)
            item.text = _("保存路径: {}").format(self._shorten_path(self.setting_save_path))
            if renderer:
                r = renderer.pop()
                if hasattr(r, 'recorder'):
                    r.recorder.save_directory = self.setting_save_path
            cherrypy.engine.publish('app_notify',
                                    _('保存路径已更新'),
                                    _('新路径: {}').format(self.setting_save_path))

    def on_ffmpeg_path_clicked(self, item):
        renderer = cherrypy.engine.publish('get_renderer')
        current_path = self.setting_ffmpeg_path
        if renderer:
            r = renderer.pop()
            if hasattr(r, 'recorder'):
                current_path = r.recorder.custom_ffmpeg_path
        new_path = self._show_ffmpeg_dialog(current_path)
        if new_path and os.path.isfile(new_path):
            self.setting_ffmpeg_path = new_path
            Setting.set(SettingProperty.Record_FFmpegPath, self.setting_ffmpeg_path)
            item.text = _("FFmpeg路径: {}").format(self._shorten_ffmpeg_path(self.setting_ffmpeg_path))
            if renderer:
                r = renderer.pop()
                if hasattr(r, 'recorder'):
                    r.recorder.custom_ffmpeg_path = self.setting_ffmpeg_path
            cherrypy.engine.publish('app_notify',
                                    _('FFmpeg路径已更新'),
                                    _('新路径: {}').format(self.setting_ffmpeg_path))
        elif new_path == "":
            self.setting_ffmpeg_path = ""
            Setting.set(SettingProperty.Record_FFmpegPath, "")
            item.text = _("FFmpeg路径: {}").format(self._shorten_ffmpeg_path(""))
            if renderer:
                r = renderer.pop()
                if hasattr(r, 'recorder'):
                    r.recorder.custom_ffmpeg_path = ""
            cherrypy.engine.publish('app_notify',
                                    _('FFmpeg路径已重置'),
                                    _('使用自动检测'))

    def _show_ffmpeg_dialog(self, current_path):
        if sys.platform == 'darwin':
            try:
                res = Setting.system_shell(
                    ['osascript',
                     '-e',
                     'choose file with prompt "选择FFmpeg可执行文件" default location POSIX file "{}"'.format(
                         current_path if current_path else "/usr/local/bin/")])
                if res[0] == 0:
                    path = res[1].strip().strip('"')
                    if path.startswith("alias "):
                        res2 = Setting.system_shell(
                            ['osascript',
                             '-e',
                             'POSIX path of ({} as alias)'.format(path)])
                        if res2[0] == 0:
                            return res2[1].strip()
                    return path
            except Exception as e:
                logger.error(f"FFmpeg路径对话框错误: {e}")
        elif sys.platform == 'win32':
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                filetypes = [
                    ('可执行文件', '*.exe'),
                    ('所有文件', '*.*')
                ]
                path = filedialog.askopenfilename(
                    title="选择FFmpeg可执行文件",
                    initialdir=os.path.dirname(current_path) if current_path else ".",
                    filetypes=filetypes
                )
                root.destroy()
                return path if path else current_path
            except Exception as e:
                logger.error(f"FFmpeg路径对话框错误: {e}")
        else:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                filetypes = [
                    ('所有文件', '*.*')
                ]
                path = filedialog.askopenfilename(
                    title="选择FFmpeg可执行文件",
                    initialdir=os.path.dirname(current_path) if current_path else "/usr/bin",
                    filetypes=filetypes
                )
                root.destroy()
                return path if path else current_path
            except Exception as e:
                logger.error(f"FFmpeg路径对话框错误: {e}")
        return current_path

    def _show_path_dialog(self, current_path):
        if sys.platform == 'darwin':
            try:
                res = Setting.system_shell(
                    ['osascript',
                     '-e',
                     'choose folder with prompt "选择录制保存路径" default location POSIX file "{}"'.format(
                         current_path)])
                if res[0] == 0:
                    path = res[1].strip().strip('"')
                    if path.startswith("alias "):
                        res2 = Setting.system_shell(
                            ['osascript',
                             '-e',
                             'POSIX path of ({} as alias)'.format(path)])
                        if res2[0] == 0:
                            return res2[1].strip()
                    return path
            except Exception as e:
                logger.error(f"路径对话框错误: {e}")
        elif sys.platform == 'win32':
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                path = filedialog.askdirectory(
                    title="选择录制保存路径",
                    initialdir=current_path
                )
                root.destroy()
                if path:
                    return path
            except Exception as e:
                logger.error(f"路径对话框错误: {e}")
        else:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                path = filedialog.askdirectory(
                    title="选择录制保存路径",
                    initialdir=current_path
                )
                root.destroy()
                if path:
                    return path
            except Exception as e:
                logger.error(f"路径对话框错误: {e}")
        return current_path


cherrypy.engine.subscribe('recording_status_update',
                          lambda status: None)


if __name__ == '__main__':
    gui(RecordingRenderer())
