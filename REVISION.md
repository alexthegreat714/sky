rev_0001

Date: 2025-11-02 UTC

Scope:
- Added Sky watchdog (health checks + daily summary)
- Added Garmin sleep downloader with persistent Chrome profile
- Added interactive wizard and click-to-capture selectors
- Added daily info agent and browser-use agent with endpoint probing
- Wrote README under Sky/agents and revisions summary under Sky/revisions/rev_0001

rev_0002

Date: 2025-11-02 UTC

Scope:
- Added Garmin daily scheduling via Windows Task Scheduler at 06:55 local time (Task: SkyGarminDownload0655)
- Watchdog now checks Garmin CSV presence for yesterday in downloads folder and reports status
- Snapshotted updated watchdog config and selectors under rev_0002
