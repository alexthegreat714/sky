import datetime as dt
from typing import List, Dict, Callable

class SimpleScheduler:
    """
    Very small time-based scheduler.
    - tasks: list of dicts {name, cron_like, func}
    cron_like supports "HH:MM" daily times (local), or "every:Nmin".
    """
    def __init__(self):
        self.tasks: List[Dict] = []
        self._last_run: Dict[str, dt.datetime] = {}

    def add_daily(self, name: str, hhmm: str, func: Callable):
        self.tasks.append({"name": name, "mode": "daily", "time": hhmm, "func": func})

    def add_every_minutes(self, name: str, minutes: int, func: Callable):
        self.tasks.append({"name": name, "mode": "every", "minutes": minutes, "func": func})

    def tick(self, now: dt.datetime = None):
        now = now or dt.datetime.now()
        for t in self.tasks:
            n = t["name"]
            last = self._last_run.get(n)

            if t["mode"] == "daily":
                hh, mm = map(int, t["time"].split(":"))
                due = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                # If we already ran today at/after due, skip
                if last and last.date() == now.date() and last >= due:
                    continue
                # Allow a 60s window
                window_start = due
                window_end = due + dt.timedelta(seconds=60)
                if window_start <= now <= window_end:
                    t["func"]()
                    self._last_run[n] = now

            elif t["mode"] == "every":
                interval = dt.timedelta(minutes=int(t["minutes"]))
                if not last or now - last >= interval:
                    t["func"]()
                    self._last_run[n] = now
