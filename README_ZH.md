# Macast-plugins
[![visitor](https://visitor-badge.glitch.me/badge?page_id=xfangfang.Macast-plugins)](https://gitee.com/xfangfang/Macast-plugins)
[![plugins](https://shields-staging.herokuapp.com/github/directory-file-count/xfangfang/Macast-plugins?type=dir&label=plugins)](https://gitee.com/xfangfang/Macast-plugins/)

[Macast](https://gitee.com/xfangfang/Macast/)的插件仓库.  

<img align="center" width="400" src="https://xfangfang.gitee.io/assets/img/macast/select_renderer.png" alt="select_renderer" height="auto"/>

## 如何使用第三方插件

  1. 从Gitee下载 [Macast](https://gitee.com/xfangfang/Macast/)
  2. 从这个仓库下载你需要的插件
  3. 打开Macast, 点击设置选项中的 `打开配置目录`
  4. 把您刚刚下载的 **[some plugin].py** 文件放入配置目录中的renderer文件夹下
  5. 重启Macast，然后在菜单中选择你需要的插件.

## Plugins

**您可以点击下表右侧的 [some plugin].py 链接, 然后把浏览器显示的文字全部保存为[some plugin].py文件并放入配置目录中的renderer文件夹下，使用之前不要忘记查看每个插件的README**

| 插件    | MacOS | Linux                    | Windows | 描述                                                  | 链接                                                        |
| ---------- | ----- | ------------------------ | ------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| IINA       | ☑️     |                          |         | IINA 适配插件                                     | [iina-beta.py](https://gitee.com/xfangfang/Macast-plugins/raw/main/iina/iina-beta.py)  [iina.py](https://gitee.com/xfangfang/Macast-plugins/raw/main/iina/iina.py)  [README](https://gitee.com/xfangfang/Macast-plugins/tree/main/iina) |
| PotPlayer  |       |                          | ☑️       | PotPlayer 适配插件                                | [potplayer.py](https://gitee.com/xfangfang/Macast-plugins/raw/main/potplayer/potplayer.py)  [README](https://gitee.com/xfangfang/Macast-plugins/tree/main/potplayer) |<img width="265" alt="image" src="https://user-images.githubusercontent.com/16631584/143246295-cd7b4618-f90c-445a-b9c0-1ec0b7bdf885.png">
| PI-FM-RDS  |       | ☑️ (只能用在树莓派上) |         | 使用这个插件接收mp3媒体链接并用pi-fm-rds以fm广播的形式发送       | [pi_fm.py](https://gitee.com/xfangfang/Macast-plugins/raw/main/pi-fm-rds/pi_fm.py)  [README](https://gitee.com/xfangfang/Macast-plugins/tree/main/pi-fm-rds) |
| WebBrowser | ☑️     | ☑️                        | ☑️       | 这个插件可以用于使用浏览器下载媒体文件，或播放某些不受mpv支持的m3u8文件 | [web.py](https://gitee.com/xfangfang/Macast-plugins/raw/main/web/web.py)  [README](https://gitee.com/xfangfang/Macast-plugins/tree/main/web) |


## 写一个新的插件

如果你想要适配其他的播放器, 点 [这里](https://gitee.com/xfangfang/Macast/wikis/Custom-Renderer) 来学习如何写一个插件，欢迎给项目提交PR（只接受提交到Github的PR）.
