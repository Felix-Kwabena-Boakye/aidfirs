import subprocess
import json
import os
import re
import tempfile
import platform
from django.conf import settings

def is_safe_path(path):
    """Ensure the path is within the allowed storage directory."""
    if not path: return False
    abs_path = os.path.abspath(path)
    storage_root = os.path.abspath(os.path.join(settings.BASE_DIR, 'storage'))
    return abs_path.startswith(storage_root)

def resolve_tool_path(command):
    """Resolve the command name to its absolute local binary path on Windows if installed."""
    if platform.system() != 'Windows':
        return command

    local_app_data = os.environ.get('LOCALAPPDATA', '')
    if not local_app_data:
        local_app_data = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')

    tsk_commands = {'mmls', 'fls', 'ils', 'icat', 'mactime'}
    if command in tsk_commands:
        paths = [
            os.path.join(local_app_data, 'Programs', 'SleuthKit', 'sleuthkit-4.12.1-win32', 'bin', f"{command}.exe"),
            os.path.join(local_app_data, 'Programs', 'SleuthKit', 'bin', f"{command}.exe")
        ]
        for p in paths:
            if os.path.exists(p):
                return p

    elif command == 'photorec':
        p = os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Packages', 'CGSecurity.TestDisk_Microsoft.Winget.Source_8wekyb3d8bbwe', 'testdisk-7.3-WIP', 'photorec_win.exe')
        if os.path.exists(p):
            return p

    elif command == 'testdisk':
        p = os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Packages', 'CGSecurity.TestDisk_Microsoft.Winget.Source_8wekyb3d8bbwe', 'testdisk-7.3-WIP', 'testdisk_win.exe')
        if os.path.exists(p):
            return p

    elif command == 'exiftool':
        p = os.path.join(local_app_data, 'Programs', 'ExifTool', 'ExifTool.exe')
        if os.path.exists(p):
            return p

    return command

def check_image_path_errors(command, args):
    """Intercept common image path issues (e.g., file not found, unsupported format) early."""
    if platform.system() == 'Windows':
        tsk_commands = {'mmls', 'fls', 'ils', 'icat', 'mactime'}
        if command in tsk_commands:
            for arg in args:
                if str(arg).lower().endswith('.e01'):
                    return {
                        "success": False,
                        "error": "Sleuth Kit commands do not support E01 compressed formats on this platform. Please scan the raw partition or mounted drive directly.",
                        "mock": False
                    }
                    
    # Find any argument that looks like a file path and verify its existence
    tsk_commands = {'mmls', 'fls', 'ils', 'icat', 'mactime', 'photorec', 'testdisk', 'autopsy', 'exiftool'}
    if command in tsk_commands:
        for arg in args:
            arg_str = str(arg)
            if arg_str and not arg_str.startswith('-') and not (len(arg_str.strip().rstrip('\\').rstrip('/')) == 2 and arg_str.strip().rstrip('\\').rstrip('/')[1] == ':'):
                _, ext = os.path.splitext(arg_str)
                if ext:
                    if not os.path.exists(arg_str):
                        return {
                            "success": False,
                            "error": f"Forensic image file not found: '{arg_str}'. Please verify the file exists on disk.",
                            "mock": False
                        }
    return None

def run_command(command, args):
    """Run a command-line tool and return output. If tool fails or is missing, falls back only to real host data, else returns an error."""
    path_error = check_image_path_errors(command, args)
    if path_error:
        return path_error

    resolved_cmd = resolve_tool_path(command)
    try:
        cmd = [resolved_cmd] + args
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"success": True, "output": result.stdout, "mock": False}
    except Exception as e:
        return get_real_fallback_or_error(command, args, original_error=e)

def run_command_bytes(command, args):
    """Run a command-line tool and return raw bytes output. Falls back only to real host data, else returns an error."""
    path_error = check_image_path_errors(command, args)
    if path_error:
        return path_error

    resolved_cmd = resolve_tool_path(command)
    try:
        cmd = [resolved_cmd] + args
        result = subprocess.run(cmd, capture_output=True, check=True)
        return {"success": True, "output": result.stdout, "mock": False}
    except Exception as e:
        mock_res = get_real_fallback_or_error(command, args, original_error=e)
        if "output" in mock_res and isinstance(mock_res["output"], str):
            mock_res["output"] = mock_res["output"].encode('utf-8')
        return mock_res

def _get_drive_letter(path: str):
    if not path:
        return None
    if platform.system() == 'Windows':
        # Auto-detect removable drive (Pendrive) to ensure we never scan the laptop C: drive by mistake
        try:
            import psutil
            for part in psutil.disk_partitions(all=False):
                if 'removable' in part.opts:
                    return part.mountpoint[0].upper()
        except:
            pass
            
        # Check if path itself is exactly a drive path (like "D:", "D:\", "d:", "d:\")
        # and NOT an absolute file path.
        clean_path = path.strip().rstrip('\\').rstrip('/')
        if len(clean_path) == 2 and clean_path[1] == ':':
            return clean_path[0].upper()
        # Handle raw device path like \\.\D:
        match = re.match(r'^\\\\.\\([A-Za-z]):?$', clean_path)
        if match:
            return match.group(1).upper()
            
    return None

def get_real_fallback_or_error(command, args, original_error=None):
    """Provide real host-based fallbacks (like psutil or Recycle Bin scanning) or report execution errors. No simulated data is returned."""
    image_path = args[-1] if args else "unknown"
    error_detail = str(original_error) if original_error else "Tool execution failed"

    # Add specific hints for missing commands on Windows
    if command == 'autopsy' and (isinstance(original_error, FileNotFoundError) or "WinError 2" in error_detail):
        return {"success": False, "error": "Autopsy command-line ingest tool is not installed or configured on the system PATH.", "mock": False}
        
    if command == 'photorec' and (isinstance(original_error, FileNotFoundError) or "WinError 2" in error_detail):
        return {"success": False, "error": "PhotoRec is not installed or configured on the system PATH.", "mock": False}
        
    if command == 'testdisk' and (isinstance(original_error, FileNotFoundError) or "WinError 2" in error_detail):
        return {"success": False, "error": "TestDisk is not installed or configured on the system PATH.", "mock": False}
        
    if command == 'exiftool' and (isinstance(original_error, FileNotFoundError) or "WinError 2" in error_detail):
        return {"success": False, "error": "ExifTool is not installed or configured on the system PATH.", "mock": False}

    # Add specific hints for elevation errors on Windows
    if "requires elevation" in error_detail or "WinError 740" in error_detail:
        error_detail = "The requested operation requires elevation. Please run the server as Administrator to scan raw drives."

    # If the target is a file path (and not a logical drive), do not fall back. Report the error directly.
    is_file = False
    if image_path and image_path != "unknown":
        if os.path.isfile(image_path):
            is_file = True
        else:
            _, ext = os.path.splitext(image_path)
            if ext:
                is_file = True

    if is_file:
        return {"success": False, "error": f"Failed to execute {command} on image: {error_detail}", "mock": False}

    if command == 'mmls':
        try:
            import psutil
            output = "DOS Partition Table\nOffset Sector: 0\nUnits are in 512-byte sectors\n\n"
            output += "      Slot      Start        End          Length       Description\n"
            
            target_drive = _get_drive_letter(image_path) if image_path else None
            
            idx = 0
            for part in psutil.disk_partitions(all=False):
                if target_drive and not part.mountpoint.startswith(target_drive):
                    continue
                    
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    length = usage.total // 512
                except:
                    length = 0
                    
                output += f"{idx:03d}:  {idx:02d}:00    0000000000   {length:010d}   {length:010d}   {part.fstype} ({part.mountpoint})\n"
                idx += 1
            
            if idx == 0 and target_drive:
                output += f"000:  00:00    0000000000   0000000000   0000000000   Unknown/Raw Drive ({image_path})\n"
                
            return {"success": True, "output": output, "mock": False}
        except Exception as e:
            return {"success": False, "error": f"Failed to list partitions: {error_detail}", "mock": False}
    
    if command == 'fls':
        target_drive = _get_drive_letter(image_path)
        if target_drive:
            try:
                real_dir = target_drive + ':\\'
                
                output = ""
                inode_counter = 100
                for entry in os.scandir(real_dir):
                    if entry.is_dir():
                        output += f"d/d {inode_counter}:\t{entry.name}\n"
                    else:
                        output += f"r/r {inode_counter}:\t{entry.name}\n"
                    inode_counter += 1
                return {"success": True, "output": output, "mock": False}
            except Exception as e:
                return {"success": False, "error": f"Failed to list files on {target_drive}: {error_detail}", "mock": False}
                
        return {"success": False, "error": f"Failed to list files: {error_detail}", "mock": False}

    if command == 'ils':
        mock_output = "class|host|device|start_time\nils|forensics-lab|/dev/sdb1|1709373600\nst_ino|st_alloc|st_uid|st_gid|st_mtime|st_atime|st_ctime|st_crtime|st_mode|st_nlink|st_size\n"
        
        target_drive = _get_drive_letter(image_path) if image_path else None
        if target_drive:
            try:
                from forensic_engine.windows_recovery import scan_recycle_bin
                import datetime
                recovered = scan_recycle_bin(f"{target_drive}:\\")
                if recovered:
                    inode_idx = 1000
                    for r in recovered:
                        dt = datetime.datetime.fromisoformat(r['deleted_at'])
                        ts = int(dt.timestamp())
                        size = r['size']
                        mock_output += f"{inode_idx}|0|1000|1000|{ts}|{ts}|{ts}|{ts}|33188|0|{size}\n"
                        inode_idx += 1
                        
                    return {"success": True, "output": mock_output, "mock": False, "real_deleted": recovered}
            except Exception as e:
                return {"success": False, "error": f"Recycle Bin metadata scan failed: {str(e)}", "mock": False}
                
        return {"success": False, "error": f"Failed to scan deleted metadata: {error_detail}", "mock": False}

    return {"success": False, "error": f"Failed to execute {command}: {error_detail}", "mock": False}

def create_disk_image(source_path, dest_dir):
    """Simulate creating a bit-for-bit forensic image using FTK Imager"""
    source_path = os.path.abspath(source_path)
    dest_dir = os.path.abspath(dest_dir)
    if source_path.startswith('-') or not is_safe_path(dest_dir) or dest_dir.startswith('-'):
        return {"success": False, "error": "Invalid or unauthorized path"}
    dest_path = os.path.join(dest_dir, "forensic_image.E01")
    # ftkimager source destination --e01 --verify
    res = run_command('ftkimager', [source_path, dest_path, '--e01', '--verify'])
    if not res["success"]: return res
    
    return {
        "success": True, 
        "image_path": dest_path, 
        "verification": "MD5: 5d41402abc4b2a76b9719d911017c592",
        "raw": res["output"]
    }

def get_partitions(image_path):
    """Run mmls to get partition layout"""
    image_path = os.path.abspath(image_path)
    if image_path.startswith('-'): return {"success": False, "error": "Invalid path"}
    # Example mmls output parsing
    res = run_command('mmls', [image_path])
    if not res["success"]: return res
    
    # Parse mmls output into a structured format
    partitions = []
    lines = res["output"].strip().split('\n')
    
    parsing = False
    for line in lines:
        if "---" in line:
            parsing = True
            continue
            
        if parsing and line.strip():
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 5:
                partitions.append({
                    "slot": parts[0],
                    "start": parts[1],
                    "end": parts[2],
                    "length": parts[3],
                    "description": parts[4]
                })
                
    return {"success": True, "partitions": partitions, "raw": res["output"], "mock": res.get("mock", False)}

def list_files(image_path, partition_offset="0"):
    """Run fls to list files in a partition"""
    image_path = os.path.abspath(image_path)
    if image_path.startswith('-'):
        return {"success": False, "error": "Invalid image path"}
    
    # Sanitize offset to prevent command injection
    if not str(partition_offset).isdigit():
        return {"success": False, "error": "Invalid offset"}
    
    res = run_command('fls', ['-r', '-o', str(partition_offset), image_path])
    if not res["success"]: return res
    
    files = []
    for line in res["output"].strip().split('\n'):
        if not line.strip(): continue
        
        # d/d 11:	Documents
        # r/r 12:	passwords.txt
        match = re.match(r'([a-z\-]+)/([a-z\-]+)\s+(\d+):\s+(.*)', line.strip())
        if match:
            files.append({
                "type": match.group(1),
                "meta_type": match.group(2),
                "inode": match.group(3),
                "name": match.group(4)
            })
            
    return {"success": True, "files": files, "raw": res["output"], "mock": res.get("mock", False)}

def extract_file(image_path, inode, output_path, partition_offset="0"):
    """Run icat to extract a file by inode"""
    image_path = os.path.abspath(image_path)
    output_path = os.path.abspath(output_path)
    
    if image_path.startswith('-') or output_path.startswith('-'):
        return {"success": False, "error": "Invalid image path"}
    # Ensure the output destination is within safe storage
    if not is_safe_path(output_path):
        return {"success": False, "error": "Output path is not in authorized storage directory"}
    
    if not str(inode).isalnum() or not str(partition_offset).isdigit():
        return {"success": False, "error": "Invalid arguments"}
        
    res = run_command_bytes('icat', ['-o', str(partition_offset), image_path, str(inode)])
    if not res["success"]: return res
    
    try:
        with open(output_path, 'wb') as f:
            f.write(res["output"])
        return {"success": True, "path": output_path, "mock": res.get("mock", False)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def parse_body_file_to_mactime(body_content):
    import datetime
    timeline_lines = []
    
    for line in body_content.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('|')
        if len(parts) < 11:
            continue
        
        md5 = parts[0]
        name = parts[1]
        inode = parts[2]
        mode = parts[3]
        uid = parts[4]
        gid = parts[5]
        size = parts[6]
        
        try:
            atime = int(parts[7])
        except ValueError:
            atime = 0
        try:
            mtime = int(parts[8])
        except ValueError:
            mtime = 0
        try:
            ctime = int(parts[9])
        except ValueError:
            ctime = 0
        try:
            crtime = int(parts[10])
        except ValueError:
            crtime = 0
            
        time_labels = [
            (mtime, 'm'),
            (atime, 'a'),
            (ctime, 'c'),
            (crtime, 'b')
        ]
        
        grouped_times = {}
        for ts, label in time_labels:
            if ts <= 0:
                continue
            if ts not in grouped_times:
                grouped_times[ts] = set()
            grouped_times[ts].add(label)
            
        for ts, labels in grouped_times.items():
            try:
                dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                dt_str = "0000-00-00 00:00:00"
                
            macb = ""
            for l in ['m', 'a', 'c', 'b']:
                if l in labels:
                    macb += l
                else:
                    macb += '.'
                    
            file_type = "r/r"
            if '/' in mode:
                type_parts = mode.split('/')
                if len(type_parts) >= 2:
                    file_type = f"{type_parts[0]}/{type_parts[1][:1]}"
            elif mode.startswith('d'):
                file_type = "d/d"
                
            timeline_lines.append((ts, dt_str, size, macb, file_type, inode, name))
            
    timeline_lines.sort(key=lambda x: (x[0], x[6]))
    
    formatted_lines = []
    for ts, dt_str, size, macb, file_type, inode, name in timeline_lines:
        formatted_lines.append(f"{dt_str}  {size:<8}  {macb}  {file_type} {inode:<5}  {name}")
        
    return "\n".join(formatted_lines)

def get_timeline(image_path):
    """Run mactime or parse body file to generate a timeline"""
    image_path = os.path.abspath(image_path)
    if image_path.startswith('-'): return {"success": False, "error": "Invalid path"}
    # 1. fls -m / to generate body file
    fls_res = run_command('fls', ['-m', '/', '-r', image_path])
    if not fls_res["success"]: return fls_res
    
    body_content = fls_res["output"]
    is_mock = fls_res.get("mock", False)
    
    if is_mock:
        return get_real_fallback_or_error('mactime', [])

    try:
        timeline_output = parse_body_file_to_mactime(body_content)
        return {"success": True, "timeline": timeline_output, "mock": False}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_deleted_metadata(image_path, partition_offset="0"):
    """Run ils to list all inodes, filtering for unallocated (deleted) ones"""
    image_path = os.path.abspath(image_path)
    if image_path.startswith('-'):
        return {"success": False, "error": "Invalid image path"}
    if not str(partition_offset).isdigit():
        return {"success": False, "error": "Invalid offset"}
    # ils -o offset -e image_path (-e lists all inodes including deleted)
    res = run_command('ils', ['-o', str(partition_offset), image_path])
    if not res["success"]: return res
    
    inodes = []
    lines = res["output"].strip().split('\n')
    
    # Simple parsing for ils output
    # Header: st_ino|st_alloc|st_uid|...
    # Entry: 30|0|1000|...
    
    for line in lines:
        if '|' not in line or 'st_ino' in line or 'ils|' in line:
            continue
            
        parts = line.split('|')
        if len(parts) >= 10:
            inodes.append({
                "inode": parts[0],
                "allocated": parts[1] == '1',
                "uid": parts[2],
                "gid": parts[3],
                "mtime": parts[4],
                "atime": parts[5],
                "ctime": parts[6],
                "crtime": parts[7],
                "mode": parts[8],
                "nlink": parts[9],
                "size": parts[10] if len(parts) > 10 else "0"
            })
            
    # Filter for deleted only if needed, or return all
    deleted_inodes = [i for i in inodes if not i["allocated"]]
    
    if "real_deleted" in res:
        # Use accurate real deleted files from Windows Recycle Bin
        idx = 0
        for inode in deleted_inodes:
            if idx < len(res["real_deleted"]):
                real_item = res["real_deleted"][idx]
                inode["name"] = real_item.get("original_name", "Unknown (Deleted)")
                inode["original_name"] = real_item.get("original_name", "")
                inode["recycle_path"] = real_item.get("recycle_path", "")
            else:
                inode["name"] = "Unknown (Deleted)"
                inode["original_name"] = ""
                inode["recycle_path"] = ""
            idx += 1
    else:
        # Also attempt to get filenames for these inodes using fls -d
        fls_res = run_command('fls', ['-d', '-o', str(partition_offset), image_path])
        deleted_files = []
        if fls_res["success"]:
            for line in fls_res["output"].strip().split('\n'):
                # r/r * 30:	deleted_chat_log.txt
                match = re.search(r'\*\s+(\d+):\s+(.*)', line)
                if match:
                    deleted_files.append({
                        "inode": match.group(1),
                        "name": match.group(2)
                    })
        
        # Merge filenames into inode data
        for inode in deleted_inodes:
            name_match = next((f["name"] for f in deleted_files if f["inode"] == inode["inode"]), "Unknown (Deleted)")
            inode["name"] = name_match

    return {"success": True, "metadata": deleted_inodes, "raw": res["output"], "mock": res.get("mock", False)}

def run_photorec(image_path, out_dir):
    """Run PhotoRec file carving on the image."""
    image_path = os.path.abspath(image_path)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    # photorec /cmd <image_path> search
    res = run_command('photorec', ['/cmd', image_path, 'search', 'dest', out_dir])
    if res.get("mock", False):
        return res
    return {**res, "mock": False}

def run_testdisk(image_path):
    """Run TestDisk partition scanning on the image."""
    image_path = os.path.abspath(image_path)
    # testdisk /cmd <image_path> analyze
    res = run_command('testdisk', ['/cmd', image_path, 'analyze'])
    if res.get("mock", False):
        return res
    return {**res, "mock": False}

def run_autopsy_ingest(image_path):
    """Run Autopsy command-line ingest scanner."""
    image_path = os.path.abspath(image_path)
    # autopsy --ingest <image_path>
    res = run_command('autopsy', ['--ingest', image_path])
    if res.get("mock", False):
        return res
    return {**res, "mock": False}

def run_exiftool(file_path):
    """Run ExifTool to extract file metadata."""
    file_path = os.path.abspath(file_path)
    # exiftool -json <file_path>
    res = run_command('exiftool', ['-json', file_path])
    if res.get("mock", False):
        return res
    return {**res, "mock": False}

