# Sky Stack – Revision rev_0002 (2025-11-02 UTC)

Changes since rev_0001
- Added Windows Scheduled Task to download Garmin sleep CSV daily at 06:55 local time.
  - Task name: `SkyGarminDownload0655`
  - Command: `python C:\\Users\\blyth\\Desktop\\Engineering\\Sky\\agents\\garmin_sleep_downloader.py`
- Watchdog enhancement: verifies that yesterday’s CSV exists in `Sky\\downloads\\garmin` and reports status in JSON + daily memory.
- Snapshots of current watchdog config and Garmin selectors included in this revision.

How to verify
- Check next run time:
  - PowerShell: `Get-ScheduledTask -TaskName 'SkyGarminDownload0655' | Get-ScheduledTaskInfo`
- Run the watchdog once to update status JSON:
  - `python Sky\\watchdog\\watchdog.py`
  - Inspect: `open-webui-full\\backend\\data\\sky_watchdog\\status.json`
- View daily memory summary:
  - `open-webui-full\\backend\\data\\sky_memory.txt`

