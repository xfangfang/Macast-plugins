# Macast Recording Plugin

A DLNA stream recording plugin for Macast that uses FFmpeg to record media streams to MP4 files while simultaneously playing them.

## Features

- **Automatic Recording**: Automatically starts recording when media is cast to Macast
- **Manual Control**: Start or stop recording manually from the system tray menu
- **High Quality Output**: H.264 video (6000 kbps) + AAC audio (192 kbps)
- **Real-time Status**: Displays recording duration and file size in the menu
- **Custom Save Path**: Choose where to save recorded files via native file dialogs
- **Custom FFmpeg Path**: Configure a custom FFmpeg executable location or use auto-detection
- **Smart File Naming**: Files named with media title and timestamp (e.g., `VideoTitle_20260515_143025.mp4`)
- **Graceful Stop**: Sends `q` command to FFmpeg for clean finalization, with SIGINT/terminate fallback
- **FFmpeg Verification**: Validates FFmpeg availability and version before each recording
- **Startup Validation**: Detects FFmpeg immediate exit after launch and reports errors
- **Invalid Output Detection**: Automatically removes output files smaller than 1 KB
- **FFmpeg Log Capture**: Captures FFmpeg stderr to log files for troubleshooting
- **Cross-Platform**: Works on macOS, Windows, and Linux

## Requirements

- Macast 0.7 or later
- FFmpeg (bundled with the project, custom path, or system PATH)

## Installation

### Manual Installation

1. Copy the `recorder` folder to Macast's renderer directory:
   - **Windows**: `%APPDATA%\xfangfang\Macast\renderer\`
   - **macOS**: `~/.config/Macast/renderer/`
   - **Linux**: `~/.config/Macast/renderer/`

2. Restart Macast

3. Select **Recording Renderer** from the Renderers menu

## Usage

### Automatic Recording

By default, recording starts automatically when media is cast:

1. Select **Recording Renderer** as your renderer in Macast
2. Cast media from your phone or device
3. Recording starts automatically
4. Stop casting or select **Stop Cast** to end recording
5. A notification shows the recording duration and file size

### Manual Recording

1. Right-click the Macast icon in the system tray or menu bar
2. Navigate to **Setting** > **Recording Renderer**
3. Click **Start Recording** to begin
4. Click **Stop Recording** to end

> **Note**: Manual recording requires an active media stream. If no media is currently playing, an error notification will appear.

## Configuration

All settings are accessible from the **Recording Renderer** submenu in Macast's system tray menu.

### Menu Options

```
Recording: Idle                        (Status display, read-only)
────────────────────────────────────────
Start Recording                        (Manual start)
Stop Recording                         (Manual stop, disabled when idle)
────────────────────────────────────────
Auto Record on Cast            [✓]     (Toggle auto-record on cast)
Save Path: .../Videos/Macast           (Click to change save location)
FFmpeg Path: Auto Detect               (Click to set custom FFmpeg path)
```

### Auto Record on Cast

When enabled (default), recording starts automatically when media is cast to Macast. Toggle this option to disable auto-recording and use manual control only.

### Save Path

Click to open a folder selection dialog and change where recordings are saved. The default save path is the user's home directory.

- **macOS**: Uses native folder picker via AppleScript
- **Windows**: Uses tkinter folder dialog
- **Linux**: Uses tkinter folder dialog

### FFmpeg Path

Click to set a custom FFmpeg executable path. Supports both file paths and directory paths:

- **File path**: Direct path to the FFmpeg executable (e.g., `D:\devsoft\ffmpeg\ffmpeg.exe`)
- **Directory path**: Directory containing FFmpeg (e.g., `D:\devsoft\ffmpeg`); the plugin will automatically look for `ffmpeg.exe` (Windows) or `ffmpeg` (macOS/Linux) inside the directory
- **Auto Detect**: Leave empty to use auto-detection (default)

FFmpeg lookup priority when auto-detect is used:

1. User-configured custom path (if set)
2. Bundled FFmpeg in the project directory
3. System PATH environment variable
4. Default command name `ffmpeg`

## Recording Status

The menu displays real-time recording status:

- **Recording: Idle** — No active recording
- **Recording: 00:05:23 - 156.3 MB** — Currently recording (duration and file size update in real time)

## Output Format

| Setting | Value |
|---------|-------|
| Container | MP4 (MPEG-4) |
| Video Codec | H.264 (libx264) |
| Video Bitrate | 6000 kbps (configurable) |
| Video Preset | fast |
| Pixel Format | yuv420p |
| Audio Codec | AAC |
| Audio Bitrate | 192 kbps (configurable) |
| Fast Start | Enabled (`+faststart` movflag) |

> The output preserves the source resolution, framerate, sample rate, and channel layout.

## File Naming

Files are named using the recording start time and optional media title:

- **Without title**: `YYYYMMDD_HHMMSS.mp4` (e.g., `20260515_143025.mp4`)
- **With title**: `Title_YYYYMMDD_HHMMSS.mp4` (e.g., `MyVideo_20260515_143025.mp4`)

Special characters in titles are automatically sanitized (only alphanumeric, spaces, hyphens, and underscores are retained).

## FFmpeg Log Files

Each recording generates a hidden FFmpeg log file in the save directory:

- **Naming**: `.{filename}.ffmpeg.log` (e.g., `.20260515_143025.mp4.ffmpeg.log`)
- **Content**: Captures FFmpeg stderr output (progress, warnings, errors)
- **Encoding**: Written in binary mode for cross-platform compatibility
- **Purpose**: Used for error diagnosis when recording fails

## Configuration Keys

The plugin stores its settings in Macast's configuration file. These keys can be found in the advanced settings JSON:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Record_SavePath` | string | User home directory | Directory where recordings are saved |
| `Record_AutoStart` | int | `1` | Auto-record on cast (1 = enabled, 0 = disabled) |
| `Record_VideoBitrate` | string | `6000k` | Video bitrate for FFmpeg output |
| `Record_AudioBitrate` | string | `192k` | Audio bitrate for FFmpeg output |
| `Record_FFmpegPath` | string | `""` | Custom FFmpeg path (empty = auto-detect) |

## Troubleshooting

### "Recording Failed — Could not start recording. Check FFmpeg installation and log files."

This error indicates FFmpeg could not be found or failed to start. Check the following:

1. **Verify FFmpeg is installed**:
   ```bash
   ffmpeg -version
   ```

2. **Set FFmpeg path in plugin settings**: Click **FFmpeg Path** in the menu and select the FFmpeg executable or its parent directory.

3. **Check Macast logs** for detailed error messages.

4. **Check FFmpeg log files** in the save directory (files named `.*.ffmpeg.log`).

### "No media is currently playing"

This appears when manually starting recording without an active media stream. Ensure media is being cast to Macast before clicking **Start Recording**.

### Recording doesn't start / No output file generated

1. Verify FFmpeg is available and executable
2. Check that the save path exists and is writable
3. Look for FFmpeg log files (`.ffmpeg.log`) in the save directory for error details
4. If the log file is empty, FFmpeg may have failed to start — verify the FFmpeg binary is correct for your platform

### FFmpeg log file is empty

An empty log file typically indicates:

- FFmpeg binary is incompatible with your platform
- FFmpeg crashed before writing any output
- File permissions prevent FFmpeg from running

### Recordings are corrupted or file is too small

1. Check available disk space
2. Verify the source stream URL is accessible from your computer
3. The plugin automatically removes output files smaller than 1 KB as they likely indicate a failed recording
4. Check FFmpeg log files for stream access errors

### Custom FFmpeg path not working

- If you set a **directory path**, ensure `ffmpeg.exe` (Windows) or `ffmpeg` (macOS/Linux) exists inside that directory
- If you set a **file path**, ensure the file is executable
- Check Macast logs for messages like "Custom FFmpeg path exists but is not executable"

## Logs

Macast application logs are stored at:

- **Windows**: `%APPDATA%\xfangfang\Macast\macast.log`
- **macOS**: `~/.config/Macast/macast.log`
- **Linux**: `~/.config/Macast/macast.log`

FFmpeg recording logs are stored as hidden files in the save directory (`.filename.ffmpeg.log`).

## Changelog

### v1.0

- Initial release
- Automatic and manual recording support
- FFmpeg integration with auto-detection and custom path configuration
- Real-time recording status display (duration and file size)
- Graceful FFmpeg stop with `q` command and signal fallback
- FFmpeg availability verification before recording
- Startup validation to detect immediate FFmpeg exit
- Invalid output file detection and automatic cleanup
- FFmpeg log capture for troubleshooting
- Cross-platform support (macOS, Windows, Linux)
- Custom save path and FFmpeg path configuration via menu
- Media title-aware file naming

## License

This plugin is part of the Macast project and follows the same license.
