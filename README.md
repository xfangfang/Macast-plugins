# Macast-plugins
[![visitor](https://visitor-badge.glitch.me/badge?page_id=xfangfang.Macast-plugins)](https://github.com/xfangfang/Macast-plugins)
[![plugins](https://shields-staging.herokuapp.com/github/directory-file-count/xfangfang/Macast-plugins?type=dir&label=plugins)](https://github.com/xfangfang/Macast-plugins/search?q=extension%3Apy)

[中文说明](https://github.com/xfangfang/Macast-plugins/blob/main/README_ZH.md)

Plugin repository for [Macast](https://github.com/xfangfang/Macast/).  

<img align="center" width="400" src="https://xfangfang.github.io/assets/img/macast/select_renderer.png" alt="select_renderer" height="auto"/>

## How to use third-party player plugin

  1. Download [Macast](https://github.com/xfangfang/Macast/) from GitHub Release.
  2. Download the plugin you want from this repo（See next section）.
  3. Open Macast, and click `Open Config Directory` in the setting menu.
  4. Put the **[some plugin].py** you just downloaded into the renderer folder of the Macast configuration directory
  5. Restart Macast and choose the plugins you want.

## How to download Plugins

*You can click [some plugin].py on the right side of the table, and then save the displayed text to the renderer folder with the corresponding file name.*

| Plugins    | MacOS | Linux                    | Windows | Description                                                  | Links                                                        |
| ---------- | ----- | ------------------------ | ------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| IINA       | ☑️     |                          |         | IINA support for Macast                                      | [iina-beta.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/iina/iina-beta.py)  [iina.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/iina/iina.py)  [README](https://github.com/xfangfang/Macast-plugins/tree/main/iina) |
| PotPlayer  |       |                          | ☑️       | PotPlayer support for Macast                                 | [potplayer.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/potplayer/potplayer.py)  [README](https://github.com/xfangfang/Macast-plugins/tree/main/potplayer) |
| PI-FM-RDS  |       | ☑️ (Only for RaspberryPi) |         | Use this to send MP3 music in the form of FM broadcast       | [pi_fm.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/pi-fm-rds/pi_fm.py)  [README](https://github.com/xfangfang/Macast-plugins/tree/main/pi-fm-rds) |
| WebBrowser | ☑️     | ☑️                        | ☑️       | This can be used to download media files or get some m3u8 played | [web.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/web/web.py)  [README](https://github.com/xfangfang/Macast-plugins/tree/main/web) |


## Write a new plugin

if you can't find any plugins you like, check [here](https://github.com/xfangfang/Macast/wiki/Custom-Renderer) to learn how to write a custom renderer plugin, and feel welcome to open a pull requests.
