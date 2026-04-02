"""
USB Device Detector — uses the Windows/Linux storage driver stack directly.

Detection Strategy (Windows):
  1. psutil.disk_partitions()           — get all mounted drive letters + fstype
  2. ctypes Win32 GetDriveTypeW()       — confirm DRIVE_REMOVABLE (type 2 = USB pendrive)
  3. PowerShell Get-Disk pipeline       — match BusType=USB to drive letters for metadata
  4. WMI Win32_DiskDrive WHERE USB      — enrich with serial number and model

Detection Strategy (Linux):
  1. lsblk -J                           — enumerate block devices with size & mountpoint
  2. /sys/bus/usb/devices               — confirm USB bus attachment
"""

import json
import subprocess
import threading
import time
import platform
from typing import List, Dict, Optional
from datetime import datetime, timezone

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import ctypes
    CTYPES_AVAILABLE = True
except ImportError:
    CTYPES_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class USBDevice:
    """Represents a detected USB/removable drive."""

    def __init__(self, drive_letter: str, volume_name: str = "",
                 drive_type: str = "USB Drive", size_gb: float = 0,
                 serial_number: str = "", interface: str = "USB",
                 is_external: bool = True, filesystem: str = "",
                 model: str = ""):
        self.drive_letter = drive_letter
        self.volume_name = volume_name
        self.drive_type = drive_type
        self.size_gb = size_gb
        self.serial_number = serial_number
        self.interface = interface
        self.is_external = is_external
        self.filesystem = filesystem
        self.model = model
        self.connected_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict:
        return {
            "drive_letter": self.drive_letter,
            "volume_name": self.volume_name,
            "drive_type": self.drive_type,
            "size_gb": self.size_gb,
            "serial_number": self.serial_number,
            "interface": self.interface,
            "is_external": self.is_external,
            "filesystem": self.filesystem,
            "model": self.model,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
        }


# ---------------------------------------------------------------------------
# Windows detection
# ---------------------------------------------------------------------------

def _get_drive_type_win32(drive_letter: str) -> int:
    """
    Call Win32 GetDriveTypeW directly via ctypes.
    Return values:
      0 = DRIVE_UNKNOWN
      1 = DRIVE_NO_ROOT_DIR
      2 = DRIVE_REMOVABLE  <-- USB pendrives, SD cards
      3 = DRIVE_FIXED      <-- Internal/external HDDs
      4 = DRIVE_REMOTE
      5 = DRIVE_CDROM
      6 = DRIVE_RAMDISK
    """
    if not CTYPES_AVAILABLE:
        return 0
    try:
        path = f"{drive_letter}:\\"
        return ctypes.windll.kernel32.GetDriveTypeW(path)
    except Exception:
        return 0


def _get_removable_drives_psutil() -> List[Dict]:
    """
    Use psutil.disk_partitions() to get all mounted drives.
    Returns list of dicts with 'letter', 'fstype', 'opts'.
    """
    drives = []
    if not PSUTIL_AVAILABLE:
        return drives
    try:
        for part in psutil.disk_partitions(all=False):
            # On Windows, mountpoint is like 'C:\\' — extract letter
            mp = part.mountpoint.rstrip("\\").rstrip("/")
            letter = mp.rstrip(":") if mp.endswith(":") else mp
            if not letter:
                continue
            drives.append({
                "letter": letter,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "opts": part.opts,
            })
    except Exception as e:
        print(f"[USB] psutil error: {e}")
    return drives


def _get_disk_usage_gb(drive_letter: str) -> float:
    """Get total disk size in GB using psutil."""
    if not PSUTIL_AVAILABLE:
        return 0.0
    try:
        usage = psutil.disk_usage(f"{drive_letter}:\\")
        return round(usage.total / (1024 ** 3), 2)
    except Exception:
        return 0.0


def _get_usb_metadata_powershell() -> List[Dict]:
    """
    Use the native Windows Storage Stack (not wmic) to find USB drives.

    Get-Disk lists physical disks with BusType.
    Get-Partition maps them to drive letters.
    Get-Volume gives volume label and filesystem.

    Returns list of dicts: letter, volume_name, filesystem, model,
                            serial_number, size_gb, bus_type
    """
    ps_script = r"""
$results = @()
try {
    $disks = Get-Disk -ErrorAction SilentlyContinue
    foreach ($disk in $disks) {
        $busType = $disk.BusType
        if ($busType -eq 'USB' -or $busType -eq 7) {
            $partitions = $disk | Get-Partition -ErrorAction SilentlyContinue
            foreach ($part in $partitions) {
                $letter = $part.DriveLetter
                if (-not $letter -or $letter -eq '') { continue }
                $vol = $part | Get-Volume -ErrorAction SilentlyContinue
                $results += [PSCustomObject]@{
                    Letter       = [string]$letter
                    VolumeLabel  = if ($vol) { $vol.FileSystemLabel } else { '' }
                    FileSystem   = if ($vol) { $vol.FileSystem } else { '' }
                    SizeGB       = [math]::Round($disk.Size / 1GB, 2)
                    Model        = $disk.FriendlyName
                    SerialNumber = $disk.SerialNumber
                    BusType      = [string]$disk.BusType
                }
            }
        }
    }
} catch {}
$results | ConvertTo-Json -Depth 3
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        stdout = result.stdout.strip()
        if not stdout or stdout.lower() in ("null", ""):
            return []
        data = json.loads(stdout)
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception as e:
        print(f"[USB] PowerShell Get-Disk error: {e}")
        return []


def _get_volume_label_win32(drive_letter: str) -> str:
    """Get volume label for a drive using GetVolumeInformationW."""
    if not CTYPES_AVAILABLE:
        return ""
    try:
        label_buf = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetVolumeInformationW(
            f"{drive_letter}:\\",
            label_buf,
            ctypes.sizeof(label_buf),
            None, None, None, None, 0
        )
        return label_buf.value
    except Exception:
        return ""


def get_usb_devices() -> List["USBDevice"]:
    """
    Main entry point. Detects USB/removable drives using the OS storage driver.
    Works on Windows and Linux.
    """
    if platform.system() != "Windows":
        return _get_linux_usb_devices()

    return _get_windows_usb_devices()


def _get_windows_usb_devices() -> List["USBDevice"]:
    """Detect USB drives on Windows using multi-strategy approach."""
    devices: List[USBDevice] = []
    seen_letters: set = set()

    # ------------------------------------------------------------------
    # Strategy 1: PowerShell Get-Disk pipeline (most reliable for USB)
    # This queries the actual Windows storage driver (BusType = USB).
    # ------------------------------------------------------------------
    ps_devices = _get_usb_metadata_powershell()
    for item in ps_devices:
        letter = str(item.get("Letter", "")).strip().upper()
        if not letter or letter in seen_letters:
            continue
        seen_letters.add(letter)

        size_gb = item.get("SizeGB") or _get_disk_usage_gb(letter)
        label = item.get("VolumeLabel") or _get_volume_label_win32(letter)
        fstype = item.get("FileSystem", "")
        model = item.get("Model", "")
        serial = str(item.get("SerialNumber") or "").strip()

        # Determine drive type from size
        drive_type = "USB Pendrive"
        if size_gb and size_gb > 64:
            drive_type = "External Hard Drive"

        devices.append(USBDevice(
            drive_letter=letter,
            volume_name=label,
            drive_type=drive_type,
            size_gb=size_gb or 0,
            serial_number=serial,
            interface="USB",
            is_external=True,
            filesystem=fstype,
            model=model,
        ))

    # ------------------------------------------------------------------
    # Strategy 2: psutil + ctypes Win32 GetDriveTypeW
    # Catches USB pendrives that don't show up in Get-Disk (e.g. some
    # older SD readers report as DRIVE_REMOVABLE but not BusType USB).
    # ------------------------------------------------------------------
    all_drives = _get_removable_drives_psutil()
    for drv in all_drives:
        letter = drv["letter"].upper().rstrip(":")
        if letter in seen_letters:
            continue  # already found via PowerShell

        drive_type_code = _get_drive_type_win32(letter)
        # 2 = DRIVE_REMOVABLE — pendrives, SD cards, etc.
        if drive_type_code != 2:
            continue

        seen_letters.add(letter)
        size_gb = _get_disk_usage_gb(letter)
        label = _get_volume_label_win32(letter)
        fstype = drv.get("fstype", "")

        devices.append(USBDevice(
            drive_letter=letter,
            volume_name=label,
            drive_type="USB Pendrive",
            size_gb=size_gb,
            serial_number="",
            interface="USB",
            is_external=True,
            filesystem=fstype,
            model="",
        ))

    return devices


# ---------------------------------------------------------------------------
# Linux detection
# ---------------------------------------------------------------------------

def _parse_size_to_gb(size_str: str) -> float:
    """Parse lsblk size string (e.g. '32G', '500M') to GB."""
    try:
        s = size_str.upper().strip()
        if "T" in s:
            return float(s.replace("T", "")) * 1024
        elif "G" in s:
            return float(s.replace("G", ""))
        elif "M" in s:
            return float(s.replace("M", "")) / 1024
        elif "K" in s:
            return float(s.replace("K", "")) / (1024 ** 2)
    except Exception:
        pass
    return 0.0


def _is_usb_block_device_linux(device_name: str) -> bool:
    """Check /sys/bus/usb to confirm a block device is connected via USB."""
    import os
    try:
        # lsblk gives names like 'sdb'; check if any USB device links to it
        sys_path = f"/sys/block/{device_name}"
        if os.path.exists(sys_path):
            real_path = os.path.realpath(sys_path)
            return "usb" in real_path.lower()
    except Exception:
        pass
    return False


def _get_linux_usb_devices() -> List["USBDevice"]:
    """Detect USB drives on Linux using lsblk + /sys/bus/usb."""
    devices = []
    try:
        result = subprocess.run(
            ["lsblk", "-o", "NAME,TYPE,MOUNTPOINT,SIZE,MODEL,FSTYPE", "-J"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if not result.stdout:
            return devices

        data = json.loads(result.stdout)
        for dev in data.get("blockdevices", []):
            if dev.get("type") != "disk":
                continue
            name = dev.get("name", "")
            if not _is_usb_block_device_linux(name):
                continue

            model = (dev.get("model") or "").strip()
            size_gb = _parse_size_to_gb(dev.get("size", "0"))

            # Find mountpoint from first child partition
            children = dev.get("children", [])
            mountpoint = ""
            fstype = ""
            if children:
                mountpoint = children[0].get("mountpoint") or ""
                fstype = children[0].get("fstype") or ""

            devices.append(USBDevice(
                drive_letter=f"/dev/{name}",
                volume_name=model or f"/dev/{name}",
                drive_type="USB Device",
                size_gb=size_gb,
                serial_number="",
                interface="USB",
                is_external=True,
                filesystem=fstype,
                model=model,
            ))
    except Exception as e:
        print(f"[USB] Linux detection error: {e}")
    return devices


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

class USBDeviceMonitor:
    """Monitor USB device connections periodically in a background thread."""

    def __init__(self, interval: int = 2):
        self.interval = interval
        self.devices: List[USBDevice] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks = []

    def start(self):
        """Start periodic USB device scanning."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._scan_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop periodic scanning."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _scan_loop(self):
        """Background scanning loop."""
        while self._running:
            try:
                self.devices = get_usb_devices()
                for cb in self._callbacks:
                    try:
                        cb(self.devices)
                    except Exception as e:
                        print(f"[USB] Callback error: {e}")
            except Exception as e:
                print(f"[USB] Scan loop error: {e}")
            time.sleep(self.interval)

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def get_devices(self) -> List[USBDevice]:
        return self.devices

    def scan_now(self) -> List[USBDevice]:
        """Force an immediate scan and cache result."""
        self.devices = get_usb_devices()
        return self.devices


# Global singleton
usb_monitor = USBDeviceMonitor(interval=2)
