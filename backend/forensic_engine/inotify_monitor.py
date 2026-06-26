import os
import time
import threading
from datetime import datetime, timezone
from django.conf import settings

class InotifyMonitor:
    """
    Inotify style background folder watcher.
    Monitors the 'storage/' directory for modifications, creations, and deletions.
    Emits events: IN_CREATE, IN_MODIFY, IN_DELETE.
    """
    def __init__(self, watch_dir=None, interval=2):
        self.watch_dir = watch_dir or os.path.join(settings.BASE_DIR, 'storage')
        self.interval = interval
        self.events = []
        self._running = False
        self._thread = None
        self._known_state = {}  # filepath -> mtime

    def start(self):
        """Start directory polling monitor thread."""
        if not self._running:
            self._running = True
            os.makedirs(self.watch_dir, exist_ok=True)
            self._initialize_state()
            self._thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _initialize_state(self):
        """Scan folder initially to build base state."""
        self._known_state = {}
        for root, _, files in os.walk(self.watch_dir):
            for file in files:
                path = os.path.join(root, file)
                try:
                    self._known_state[path] = os.path.getmtime(path)
                except Exception:
                    pass

    def _watch_loop(self):
        """Background watching loop."""
        while self._running:
            try:
                current_state = {}
                for root, _, files in os.walk(self.watch_dir):
                    for file in files:
                        path = os.path.join(root, file)
                        try:
                            current_state[path] = os.path.getmtime(path)
                        except Exception:
                            pass

                # Detect Creations & Modifications
                for path, mtime in current_state.items():
                    rel_path = os.path.relpath(path, self.watch_dir)
                    if path not in self._known_state:
                        # IN_CREATE event
                        self._log_event("IN_CREATE", rel_path, f"New file created: {rel_path}")
                    elif mtime > self._known_state[path]:
                        # IN_MODIFY event
                        self._log_event("IN_MODIFY", rel_path, f"File modified: {rel_path}")

                # Detect Deletions
                for path in list(self._known_state.keys()):
                    if path not in current_state:
                        rel_path = os.path.relpath(path, self.watch_dir)
                        # IN_DELETE event
                        self._log_event("IN_DELETE", rel_path, f"File deleted: {rel_path}")

                self._known_state = current_state
            except Exception as e:
                print(f"[InotifyMonitor] Error: {e}")
            time.sleep(self.interval)

    def _log_event(self, event_type, path, message):
        """Log event into history (cap at 200 items)."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "path": path,
            "message": message
        }
        self.events.insert(0, event)
        if len(self.events) > 200:
            self.events.pop()

    def get_events(self):
        return self.events

# Singleton instance
inotify_monitor = InotifyMonitor()
