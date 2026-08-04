import json
import subprocess
import threading
import time
import platform
import os
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


class USBDevice:
    """Represents a detected USB/removable drive or physical forensic target."""

    def __init__(self, drive_letter: str, volume_name: str = "",
                 drive_type: str = "USB Drive", size_gb: float = 0,
                 serial_number: str = "", interface: str = "USB",
                 is_external: bool = True, filesystem: str = "",
                 model: str = "", vendor: str = "", manufacturer: str = "",
                 bus_type: str = "", device_path: str = ""):
        self.drive_letter = drive_letter
        self.volume_name = volume_name
        self.drive_type = drive_type
        self.size_gb = size_gb
        self.serial_number = serial_number or "UNKNOWN"
        self.interface = interface
        self.is_external = is_external
        self.filesystem = filesystem
        self.model = model
        self.vendor = vendor
        self.manufacturer = manufacturer
        self.bus_type = bus_type or interface
        self.device_path = device_path or drive_letter
        self.volume_label = volume_name or model or "USB Drive"
        self.mount_point = drive_letter
        self.capacity_bytes = int(size_gb * 1024 ** 3)
        self.connected_at = datetime.now(timezone.utc)

        # Cryptographic fingerprints of serial number + model
        fingerprint_src = f"{self.serial_number}:{self.model}".encode('utf-8')
        import hashlib
        self.hash_sha256 = hashlib.sha256(fingerprint_src).hexdigest()
        self.hash_md5 = hashlib.md5(fingerprint_src).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "device_name": self.volume_label,
            "model": self.model or "Unknown Model",
            "serial_number": self.serial_number,
            "filesystem": self.filesystem or "Auto-Detect",
            "capacity": self.size_gb,
            "capacity_bytes": self.capacity_bytes,
            "mount_point": self.mount_point,
            "drive_letter": self.drive_letter,
            "device_path": self.device_path,
            "connected_time": self.connected_at.isoformat() if self.connected_at else None,
            "vendor": self.vendor or "Unknown Vendor",
            "manufacturer": self.manufacturer or "Unknown Manufacturer",
            "bus_type": self.bus_type,
            "drive_type": self.drive_type,
            "size_gb": self.size_gb,
            "volume_name": self.volume_name or self.model or "USB Drive",
            "volume_label": self.volume_label,
            "interface": self.interface,
            "is_external": self.is_external,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "hash_sha256": self.hash_sha256,
            "hash_md5": self.hash_md5,
            "source": "AIDFIRS Agent"
        }



def _get_drive_type_win32(drive_letter: str) -> int:
    if not CTYPES_AVAILABLE:
        return 0
    try:
        path = f"{drive_letter}:\\"
        return ctypes.windll.kernel32.GetDriveTypeW(path)
    except Exception:
        return 0


def _get_removable_drives_psutil() -> List[Dict]:
    drives = []
    if not PSUTIL_AVAILABLE:
        return drives
    try:
        for part in psutil.disk_partitions(all=False):
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
    if not PSUTIL_AVAILABLE:
        return 0.0
    try:
        usage = psutil.disk_usage(f"{drive_letter}:\\")
        return round(usage.total / (1024 ** 3), 2)
    except Exception:
        return 0.0


def _get_usb_metadata_powershell() -> List[Dict]:
    ps_script = r"""
$results = @()
try {
    $disks = Get-Disk -ErrorAction SilentlyContinue
    foreach ($disk in $disks) {
        $partitions = $disk | Get-Partition -ErrorAction SilentlyContinue
        foreach ($part in $partitions) {
            $letter = $part.DriveLetter
            if (-not $letter -or $letter -eq '') { continue }
            $vol = $part | Get-Volume -ErrorAction SilentlyContinue
            
            $wmiDisk = Get-CimInstance -ClassName Win32_DiskDrive -Filter "Index=$($disk.Number)" -ErrorAction SilentlyContinue
            $manufacturer = if ($wmiDisk) { $wmiDisk.Manufacturer } else { '' }
            
            $driveType = "USB Drive"
            $busLower = "$($disk.BusType)".ToLower()
            if ($busLower -eq "sd" -or $busLower -eq "mmc" -or $disk.FriendlyName -match "SD Card" -or $disk.FriendlyName -match "Card Reader") {
                $driveType = "Memory Card"
            } elseif ($busLower -eq "sata" -or $busLower -eq "nvme" -or $busLower -eq "scsi") {
                if ($wmiDisk.MediaType -match "External" -or $disk.OperationalStatus -match "Removable" -or $wmiDisk.Capabilities -contains 4) {
                    $driveType = "External HDD"
                } else {
                    $driveType = "Internal HDD"
                }
            } elseif ($busLower -eq "usb") {
                $driveType = "USB Drive"
            }
            
            $results += [PSCustomObject]@{
                Letter       = [string]$letter
                VolumeLabel  = if ($vol) { $vol.FileSystemLabel } else { '' }
                FileSystem   = if ($vol) { $vol.FileSystem } else { '' }
                SizeGB       = [math]::Round($disk.Size / 1GB, 2)
                Model        = $disk.FriendlyName
                SerialNumber = $disk.SerialNumber
                BusType      = [string]$disk.BusType
                Manufacturer = $manufacturer
                Vendor       = $manufacturer
                DriveType    = $driveType
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
            timeout=5,
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


def get_usb_devices() -> List[USBDevice]:
    if platform.system() != "Windows":
        return _get_linux_usb_devices()
    return _get_windows_usb_devices()


def _get_windows_usb_devices() -> List[USBDevice]:
    devices: List[USBDevice] = []
    seen_letters: set = set()

    # 1. Instant native Win32 drive enumeration (A..Z)
    logical_letters = []
    if CTYPES_AVAILABLE:
        try:
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            logical_letters = [chr(65 + i) for i in range(26) if mask & (1 << i)]
        except Exception:
            pass

    if not logical_letters and PSUTIL_AVAILABLE:
        try:
            logical_letters = [p.mountpoint.rstrip(":\\") for p in psutil.disk_partitions(all=True)]
        except Exception:
            pass

    # 2. Try fast PowerShell query for hardware models/serials (1 sec timeout)
    ps_metadata = {}
    try:
        ps_script = r"Get-CimInstance Win32_DiskDrive -ErrorAction SilentlyContinue | Select-Object Model, SerialNumber, InterfaceType, MediaType, Size, DeviceID, BusType | ConvertTo-Json"
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True, text=True, timeout=2.0
        )
        if res.stdout and res.stdout.strip():
            raw_data = json.loads(res.stdout)
            if isinstance(raw_data, dict):
                raw_data = [raw_data]
            for disk_item in raw_data:
                dev_id = str(disk_item.get("DeviceID", "")).strip()
                if dev_id:
                    ps_metadata[dev_id] = disk_item
    except Exception:
        pass

    for letter in logical_letters:
        letter = letter.upper().rstrip(":")
        if not letter or letter in seen_letters:
            continue

        drive_type_code = _get_drive_type_win32(letter)
        # Type 2 = DRIVE_REMOVABLE, 3 = DRIVE_FIXED, 4 = DRIVE_REMOTE, 5 = DRIVE_CDROM, 6 = DRIVE_RAMDISK
        if drive_type_code not in (2, 3, 4, 5, 6):
            continue

        seen_letters.add(letter)
        drive_path = f"{letter}:\\"

        label = ""
        fstype = ""
        vol_serial_hex = ""
        size_gb = 0.0
        capacity_bytes = 0

        if CTYPES_AVAILABLE:
            try:
                vol_buf = ctypes.create_unicode_buffer(1024)
                fs_buf = ctypes.create_unicode_buffer(1024)
                serial_num = ctypes.c_ulong()
                max_len = ctypes.c_ulong()
                flags = ctypes.c_ulong()

                res = ctypes.windll.kernel32.GetVolumeInformationW(
                    drive_path, vol_buf, 1024,
                    ctypes.byref(serial_num),
                    ctypes.byref(max_len),
                    ctypes.byref(flags),
                    fs_buf, 1024
                )
                if res:
                    label = vol_buf.value
                    fstype = fs_buf.value
                    if serial_num.value:
                        vol_serial_hex = f"{serial_num.value:08X}"

                total_bytes = ctypes.c_ulonglong()
                free_bytes = ctypes.c_ulonglong()
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    drive_path, None,
                    ctypes.byref(total_bytes),
                    ctypes.byref(free_bytes)
                )
                capacity_bytes = total_bytes.value
                size_gb = round(capacity_bytes / (1024 ** 3), 2)
            except Exception:
                pass

        if size_gb == 0 and PSUTIL_AVAILABLE:
            size_gb = _get_disk_usage_gb(letter)

        label_lower = label.lower()
        model_str = f"Local Storage ({letter}:)"

        # Enhanced Drive Classification
        if "google drive" in label_lower or "google" in label_lower or fstype.lower() in ("googledrive", "gfs"):
            drive_type = "Google Drive"
            bus_type = "Cloud/Virtual"
            is_external = True
            model_str = f"Google Drive ({letter}:)"
        elif drive_type_code == 4:  # DRIVE_REMOTE
            drive_type = "Network Drive"
            bus_type = "Network"
            is_external = True
            model_str = f"Network Drive ({letter}:)"
        elif drive_type_code == 5:  # DRIVE_CDROM
            drive_type = "Mounted ISO"
            bus_type = "Virtual"
            is_external = True
            model_str = f"Optical/ISO Drive ({letter}:)"
        elif drive_type_code == 6:  # DRIVE_RAMDISK
            drive_type = "Virtual Drive"
            bus_type = "RAM"
            is_external = True
            model_str = f"RAM Disk ({letter}:)"
        elif drive_type_code == 2:  # DRIVE_REMOVABLE (USB Mass Storage / SD Card)
            drive_type = "USB Flash Drive"
            bus_type = "USB"
            is_external = True
            model_str = f"USB Flash Drive ({letter}:)"
        elif drive_type_code == 3:  # DRIVE_FIXED
            if "recovery" in label_lower:
                drive_type = "Recovery Partition"
                bus_type = "SATA"
                is_external = False
                model_str = f"Recovery Partition ({letter}:)"
            elif letter == 'C':
                drive_type = "Internal HDD"
                bus_type = "SATA"
                is_external = False
                model_str = f"Internal Hard Drive ({letter}:)"
            else:
                drive_type = "Internal HDD"
                bus_type = "SATA"
                is_external = False
                model_str = f"Fixed Disk ({letter}:)"
        else:
            drive_type = "Fixed Disk"
            bus_type = "SATA"
            is_external = False

        # Assign unique per-drive serial number to prevent DB collisions
        serial_str = vol_serial_hex if vol_serial_hex else f"DRIVE-{letter}-{capacity_bytes}"
        volume_name = label if label else f"{drive_type} ({letter}:)"

        devices.append(USBDevice(
            drive_letter=letter,
            volume_name=volume_name,
            drive_type=drive_type,
            size_gb=size_gb,
            serial_number=serial_str,
            interface=bus_type,
            is_external=is_external,
            filesystem=fstype or ("FAT32" if drive_type == "USB Flash Drive" else "NTFS"),
            model=model_str,
            vendor="Google" if drive_type == "Google Drive" else ("Removable Media" if is_external else "Storage"),
            manufacturer="System Storage",
            bus_type=bus_type,
            device_path=f"\\\\.\\{letter}:"
        ))

    return devices



def _parse_size_to_gb(size_str: str) -> float:
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
    try:
        sys_path = f"/sys/block/{device_name}"
        if os.path.exists(sys_path):
            real_path = os.path.realpath(sys_path)
            return "usb" in real_path.lower()
    except Exception:
        pass
    return False


def _get_linux_usb_devices() -> List[USBDevice]:
    devices = []
    try:
        result = subprocess.run(
            ["lsblk", "-o", "NAME,TYPE,MOUNTPOINT,SIZE,MODEL,FSTYPE", "-J"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for dev in data.get("blockdevices", []):
                if dev.get("type") != "disk":
                    continue
                name = dev.get("name", "")
                if not _is_usb_block_device_linux(name):
                    continue

                model = (dev.get("model") or "").strip()
                size_gb = _parse_size_to_gb(dev.get("size", "0"))

                children = dev.get("children", [])
                mountpoint = ""
                fstype = ""
                if children:
                    mountpoint = children[0].get("mountpoint") or ""
                    fstype = children[0].get("fstype") or ""

                devices.append(USBDevice(
                    drive_letter=f"/dev/{name}",
                    volume_name=model or f"/dev/{name}",
                    drive_type="USB Drive",
                    size_gb=size_gb,
                    serial_number="",
                    interface="USB",
                    is_external=True,
                    filesystem=fstype,
                    model=model,
                ))
    except Exception as e:
        print(f"[USB] Linux lsblk error: {e}")

    # Docker/WSL Fallback
    try:
        if os.path.exists('/.dockerenv') or os.path.exists('/mnt'):
            for entry in os.scandir('/mnt'):
                if entry.is_dir() and entry.name.lower() in ['c', 'd', 'e', 'f', 'g', 'h', 'i', 'usb', 'thumb']:
                    drive_letter = f"{entry.name.upper()}:\\"
                    if any(d.drive_letter == drive_letter or d.drive_letter == entry.path for d in devices):
                        continue
                    try:
                        import psutil
                        usage = psutil.disk_usage(entry.path)
                        size_gb = round(usage.total / (1024 ** 3), 2)
                    except Exception:
                        size_gb = 0.0

                    devices.append(USBDevice(
                        drive_letter=drive_letter,
                        volume_name=f"Mounted Drive ({entry.name.upper()})",
                        drive_type="USB Drive" if entry.name.lower() != 'c' else "HDD",
                        size_gb=size_gb,
                        serial_number=f"MAPPED-{entry.name.upper()}",
                        interface="USB",
                        is_external=True,
                        filesystem="Auto-Detect",
                        model=f"WSL/Docker Bind Mount ({entry.path})"
                    ))
    except Exception as e:
        print(f"[USB] Docker mount scan error: {e}")

    return devices
