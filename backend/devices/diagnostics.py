import os
import platform
import shutil
import logging

logger = logging.getLogger("DeviceDiagnostics")

def detect_docker() -> bool:
    """
    Detect whether the backend is running inside a Docker container.
    """
    if os.path.exists('/.dockerenv'):
        return True
    try:
        with open('/proc/self/cgroup', 'r') as f:
            for line in f:
                if 'docker' in line or 'kubepods' in line:
                    return True
    except Exception:
        pass
    return False

def resolve_mapped_path(device_path: str) -> str:
    """
    Translate Windows drive letters to Linux mounts if running in a container.
    For example: 'D:\' -> '/mnt/d' or '/data/d'.
    """
    if not device_path:
        return device_path

    # Clean path formatting
    cleaned = device_path.strip().replace('/', os.sep).replace('\\', os.sep)
    
    # If we are on Windows, we do not translate paths
    if platform.system() == 'Windows':
        return cleaned

    # Check for Windows drive letters like D: or D:\ in Linux/Docker environment
    import re
    match = re.match(r'^([a-zA-Z]):?\\?$', cleaned)
    if match:
        drive_letter = match.group(1).lower()
        
        # Candidate Docker bind mounts
        candidates = [
            f"/mnt/{drive_letter}",
            f"/data/{drive_letter}",
            f"/media/{drive_letter}"
        ]
        
        for cand in candidates:
            if os.path.exists(cand):
                logger.info(f"Resolved Windows drive path '{device_path}' to container mount path '{cand}'")
                return cand
                
        # If no mounted directory exists, return default /mnt/ path
        return f"/mnt/{drive_letter}"

    return cleaned

def run_diagnostics(device_path: str) -> dict:
    """
    Run comprehensive diagnostics on the target forensic device.
    Checks:
    1. Docker environment detection
    2. Path mapping & existence check
    3. Read permission validation
    4. Tool binary compatibility
    """
    is_docker = detect_docker()
    resolved_path = resolve_mapped_path(device_path)
    
    report = {
        "device_path": device_path,
        "resolved_path": resolved_path,
        "is_docker": is_docker,
        "checks": {
            "docker_environment": {
                "status": "warning" if is_docker else "success",
                "label": "Containerized (Docker)" if is_docker else "Native Host OS",
                "message": "Running in Docker container. Drive mounts translated to Linux format." if is_docker else "Running natively on host operating system."
            },
            "drive_existence": {
                "status": "pending",
                "label": "Drive Existence Check",
                "message": ""
            },
            "read_permissions": {
                "status": "pending",
                "label": "Read Permission Check",
                "message": ""
            },
            "forensic_tools": {
                "status": "pending",
                "label": "Forensic Tools Check",
                "message": ""
            }
        },
        "success": True,
        "logs": [],
        "recommended_action": ""
    }

    # 1. Drive Existence Check
    report["logs"].append(f"Analyzing device: {device_path}")
    report["logs"].append(f"Resolved mapping: {resolved_path}")
    
    if not resolved_path:
        report["checks"]["drive_existence"] = {
            "status": "failed",
            "label": "Drive Existence Check",
            "message": "No drive path specified."
        }
        report["success"] = False
        report["recommended_action"] = "Please select a valid drive or path from the dropdown."
        return report

    if not os.path.exists(resolved_path):
        report["checks"]["drive_existence"] = {
            "status": "failed",
            "label": "Drive Existence Check",
            "message": f"Path not found: '{resolved_path}'"
        }
        report["logs"].append(f"Error: Path '{resolved_path}' does not exist on filesystem.")
        report["success"] = False
        
        if is_docker:
            drive_char = device_path[0].lower() if len(device_path) >= 2 and device_path[1] == ':' else 'd'
            report["recommended_action"] = (
                f"Mount the drive letter into the container using Docker volumes. "
                f"Example: Add '-v {drive_char.upper()}:\\:/mnt/{drive_char}' in docker-compose.yml, "
                f"then restart the container."
            )
        else:
            report["recommended_action"] = "Verify the HDD or USB thumb drive is connected and assigned a drive letter in the OS."
        return report
    else:
        report["checks"]["drive_existence"] = {
            "status": "success",
            "label": "Drive Existence Check",
            "message": f"Drive detected at '{resolved_path}'"
        }
        report["logs"].append("Drive existence verified.")

    # 2. Read Permissions Check
    try:
        # Check if we can read directory contents or file bytes
        if os.path.isdir(resolved_path):
            os.listdir(resolved_path)
            report["logs"].append("Read permission granted: successfully listed directory contents.")
        else:
            with open(resolved_path, 'rb') as f:
                f.read(512)
            report["logs"].append("Read permission granted: successfully read block sectors.")
            
        report["checks"]["read_permissions"] = {
            "status": "success",
            "label": "Read Permission Check",
            "message": "Permissions verified: READ access granted"
        }
    except PermissionError as pe:
        report["checks"]["read_permissions"] = {
            "status": "failed",
            "label": "Read Permission Check",
            "message": f"Read permission denied: {str(pe)}"
        }
        report["logs"].append(f"Error: Permission denied when accessing '{resolved_path}'.")
        report["success"] = False
        report["recommended_action"] = "Run the application with administrative permissions (run as Administrator/sudo) or adjust drive read access rights."
        return report
    except Exception as e:
        report["checks"]["read_permissions"] = {
            "status": "failed",
            "label": "Read Permission Check",
            "message": f"Access error: {str(e)}"
        }
        report["logs"].append(f"Error: Access exception when checking read permissions: {str(e)}")
        report["success"] = False
        report["recommended_action"] = "Verify that the USB drive or device is formatted properly and is not corrupted."
        return report

    # 3. Forensic Tools Compatibility Check
    from forensic_api.tsk_wrapper import resolve_tool_path
    
    missing_tools = []
    available_tools = []
    
    tools_to_check = {
        "Sleuth Kit (mmls/fls/ils)": "mmls",
        "PhotoRec Carver": "photorec",
        "TestDisk scanner": "testdisk",
        "ExifTool analyzer": "exiftool"
    }
    
    for tool_name, binary in tools_to_check.items():
        path_or_bin = resolve_tool_path(binary)
        # Verify if command is on system PATH or if absolute resolved path exists
        if shutil.which(path_or_bin) or (os.path.isabs(path_or_bin) and os.path.exists(path_or_bin)):
            available_tools.append(tool_name)
        else:
            missing_tools.append(tool_name)

    if missing_tools:
        report["checks"]["forensic_tools"] = {
            "status": "warning",
            "label": "Forensic Tools Check",
            "message": f"Missing utilities: {', '.join(missing_tools)}"
        }
        report["logs"].append(f"Warning: {len(missing_tools)} forensic binary/binaries missing on container path.")
        # Note: We do not set report["success"] = False here since the backend implements hybrid-bypass fallbacks
        report["recommended_action"] = "Some advanced carvings will use fallback methods. To use full native capabilities, install missing tools via apt/winget."
    else:
        report["checks"]["forensic_tools"] = {
            "status": "success",
            "label": "Forensic Tools Check",
            "message": "All forensic tools (SleuthKit, PhotoRec, TestDisk, ExifTool) are available"
        }
        report["logs"].append("All diagnostic tools passed verification.")

    report["logs"].append("Diagnostics completed successfully. No critical device path errors detected.")
    return report
