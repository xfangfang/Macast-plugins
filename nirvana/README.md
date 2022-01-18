# NVA(nirvana) Protocol support for Macast

platform: darwin,win32,linux

This plugin completely implements the NVA protocol

NVA is a protocol owned by [bilibili](https://app.bilibili.com/), Known as "哔哩必连".

使用本协议时，Macast在Bilibili客户端中会被识别为 `我的小电视(有弹幕)`，支持倍速、弹幕、高清视频的投放，也支持自动播放下一P，自动播放番剧下一集等功能。

Windows下Clash默认配置与本协议的访问网络部分有冲突，做了简单修复  
但还是建议在 `Clash->Settings->System Proxy` 中开启 `Specify Protocol` 选项

本脚本仅用于编程学习使用，禁止用做商业用途，如有侵权，请联系作者删除。  
关于NVA协议的分析过程与协议内容，见：https://xfangfang.github.io/028

版本更新：
v0.31 修复Windows下与Clash的兼容性  
v0.3 添加字段适配老版本，适配未登录的设备  
v0.2 添加字段适配老版本  
v0.1 暂时可用  
