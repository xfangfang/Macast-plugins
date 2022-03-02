# Macast-plugins
[![visitor](https://visitor-badge.deta.dev/badge?page_id=xfangfang.Macast-plugins)](https://github.com/xfangfang/Macast-plugins)
[![plugins](https://shields-staging.herokuapp.com/github/directory-file-count/xfangfang/Macast-plugins?type=dir&label=plugins)](https://github.com/xfangfang/Macast-plugins/search?q=extension%3Apy)

[中文说明](https://github.com/xfangfang/Macast-plugins/blob/main/README_ZH.md)

Plugin repository for [Macast](https://github.com/xfangfang/Macast/).  

<img align="center" width="400" src="https://xfangfang.github.io/assets/img/macast/select_renderer.png" alt="select_renderer" height="auto"/>

**It is recommended to click the `advanced setting` of Macast and download the plugin in your web browser.**

## How to install plugin manually

  1. Download [Macast](https://github.com/xfangfang/Macast/) from GitHub Release.
  2. Download the plugin you want from this repo（See next section for how to download and where to save）.
  3. Open Macast, and click `Open Config Directory` in the setting menu.
  4. Put the **[some plugin].py** you just download into the corresponding folder(`renderer` or `protocol` depends on what kind of plugin) of the Macast configuration directory.
  5. Restart Macast and choose the plugin you want.

## How to download Plugins

*You can click [some plugin].py on the right side of the table, and then save the displayed text to the renderer or protocol folder with the corresponding file name.*

**1. Put Player plugin(like: IINA PotPlayer WebBrowser) in the `renderer` folder.**

**2. Put Protocol plugin(like: Nirvana) in the `protocol` folder.**

**3. Never forget to read the `README`.**

| Plugins    | MacOS | Linux                    | Windows | Description                                                  | Links                                                        |
| ---------- | ----- | ------------------------ | ------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| IINA       | ☑️     |                          |         | IINA support for Macast                                      | [iina.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/iina/iina.py)  [README](https://github.com/xfangfang/Macast-plugins/tree/main/iina) |
| PotPlayer  |       |                          | ☑️       | PotPlayer support for Macast                                 | [potplayer.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/potplayer/potplayer.py)  [README](https://github.com/xfangfang/Macast-plugins/tree/main/potplayer) |
| PI-FM-RDS  |       | ☑️ (Only for RaspberryPi) |         | Use this to send MP3 music in the form of FM broadcast       | [pi_fm.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/pi-fm-rds/pi_fm.py)  [README](https://github.com/xfangfang/Macast-plugins/tree/main/pi-fm-rds) |
| WebBrowser | ☑️     | ☑️                        | ☑️       | This can be used to download media files or get some m3u8 played | [web.py](https://raw.githubusercontent.com/xfangfang/Macast-plugins/main/web/web.py)  [README](https://github.com/xfangfang/Macast-plugins/tree/main/web) |
| Nirvana（Protocol） | ☑️     | ☑️                        | ☑️       | A protocol created by Bilibili. | [nirvana.py](https://gitee.com/xfangfang/Macast-plugins/raw/main/nirvana/nirvana.py)  [README](https://gitee.com/xfangfang/Macast-plugins/tree/main/nirvana) |


## Write a new plugin

if you can't find any plugins you like, check [here](https://github.com/xfangfang/Macast/wiki/Custom-Renderer) to learn how to write a custom renderer plugin, and feel welcome to open a pull requests.
