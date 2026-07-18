import threading
import time
from typing import List, Dict, Callable
from .detector import get_usb_devices, USBDevice

class USBDeviceMonitor:
    """Monitors USB device insertion/removal using periodic polling."""
    def __init__(self, interval: int = 3):
        self.interval = interval
        self.devices: List[USBDevice] = []
        self._running = False
        self._thread = None
        self._callbacks = []

    def add_callback(self, callback: Callable[[List[USBDevice]], None]):
        self._callbacks.append(callback)

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _run_loop(self):
        while self._running:
            try:
                current_devices = get_usb_devices()
                
                # Check for changes in serial numbers / drive letters
                current_keys = {d.drive_letter: d.serial_number for d in current_devices}
                cached_keys = {d.drive_letter: d.serial_number for d in self.devices}
                
                if current_keys != cached_keys:
                    self.devices = current_devices
                    for callback in self._callbacks:
                        try:
                            callback(self.devices)
                        except Exception as e:
                            print(f"[Monitor] Callback error: {e}")
            except Exception as e:
                print(f"[Monitor] Error in scan loop: {e}")
            time.sleep(self.interval)

    def scan_now(self) -> List[USBDevice]:
        self.devices = get_usb_devices()
        return self.devices
