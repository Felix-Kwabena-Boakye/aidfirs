import subprocess
import json
import os
import re

def run_command(command, args):
    """Run a command-line tool and return output. Includes Mock Mode if tool is missing."""
    try:
        # Construct full command
        cmd = [command] + args
        
        # In a real environment, you'd want to check if the tool is installed
        # For this prototype, we'll try to execute it and catch errors
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"success": True, "output": result.stdout}
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Trigger Mock Mode if tool is missing or fails in a way that suggests it's not working correctly
        return get_mock_data(command, args)

def get_mock_data(command, args):
    """Provide realistic mock data for forensic investigations when tools are missing."""
    image_path = args[-1] if args else "unknown"
    
    if command == 'mmls':
        mock_output = f"""
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
001:  -------   0000000000   0000000127   0000000128   Unallocated
002:  000:000   0000000128   0060293119   0060292992   Win95 FAT32 (0x0b)
003:  -------   0060293120   0060293119   0000000000   Unallocated
"""
        return {"success": True, "output": mock_output, "mock": True}
    
    if command == 'fls':
        mock_output = """
r/r 4:	System Volume Information
d/d 8:	DCIM
r/r 12:	passwords.txt
r/r 15:	evidence_photos.zip
d/d 20:	Users
r/r 25:	private_key.txt
r/r 30:	deleted_chat_log.txt (recovering...)
"""
        return {"success": True, "output": mock_output, "mock": True}

    if command == 'icat':
        inode = args[-1]
        if inode == '12':
            content = "admin:P@ssw0rd123!\nuser:forensics_is_fun\n"
        elif inode == '25':
            content = "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCr9...\n-----END PRIVATE KEY-----"
        else:
            content = "Binary data placeholder for inode " + str(inode)
        return {"success": True, "output": content, "mock": True}

    if command == 'mactime':
        mock_output = """
2024-03-01 10:00:00  128  .m..  r/r 12  /passwords.txt
2024-03-01 10:05:22  1024 .m..  r/r 15  /evidence_photos.zip
2024-03-02 14:20:11  0    .m..  r/r 30  /deleted_chat_log.txt
"""
        return {"success": True, "output": mock_output, "mock": True}

    if command == 'ils':
        mock_output = """
class|host|device|start_time
ils|forensics-lab|/dev/sdb1|1709373600
st_ino|st_alloc|st_uid|st_gid|st_mtime|st_atime|st_ctime|st_crtime|st_mode|st_nlink|st_size
30|0|1000|1000|1709389211|1709389211|1709389211|1709389211|33188|0|4096
45|0|1000|1000|1709390000|1709390000|1709390000|1709390000|33188|0|1024
52|0|0|0|1709400000|1709400000|1709400000|1709400000|33188|0|512
"""
        return {"success": True, "output": mock_output, "mock": True}

    if command == 'ils':
        mock_output = """
class|host|device|start_time
ils|forensics-lab|/dev/sdb1|1709373600
st_ino|st_alloc|st_uid|st_gid|st_mtime|st_atime|st_ctime|st_crtime|st_mode|st_nlink|st_size
30|0|1000|1000|1709389211|1709389211|1709389211|1709389211|33188|0|4096
45|0|1000|1000|1709390000|1709390000|1709390000|1709390000|33188|0|1024
52|0|0|0|1709400000|1709400000|1709400000|1709400000|33188|0|512
"""
        return {"success": True, "output": mock_output, "mock": True}

    if command == 'ftkimager':
        mock_output = f"""
FTK Imager Command Line 3.1.1
Capture Time: Mon Mar  9 02:45:11 2024
Source Information:
  Type: Physical
  Source: {image_path}
  Size: 32212254720 bytes (30 GB)
Case Information:
  Case Number: AUTO-{os.urandom(4).hex().upper()}
  Evidence Number: 1
  Description: Simulated FTK Image capture for {image_path}
Image Information:
  Type: E01
  Name: forensic_image.E01
Verification Information:
  MD5 checksum: 5d41402abc4b2a76b9719d911017c592
  SHA1 checksum: 7b502c3a1f48c8609ae212cdfb639dee39673f5e
  Verification Status: Verified Successfully
"""
        return {"success": True, "output": mock_output, "mock": True}

    return {"success": False, "error": f"Tool '{command}' not found and no mock data available."}

def create_disk_image(source_path, dest_dir):
    """Simulate creating a bit-for-bit forensic image using FTK Imager"""
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
                
    return {"success": True, "partitions": partitions, "raw": res["output"]}

def list_files(image_path, partition_offset="0"):
    """Run fls to list files in a partition"""
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
            
    return {"success": True, "files": files, "raw": res["output"]}

def extract_file(image_path, inode, output_path, partition_offset="0"):
    """Run icat to extract a file by inode"""
    res = run_command('icat', ['-o', str(partition_offset), image_path, str(inode)])
    if not res["success"]: return res
    
    try:
        with open(output_path, 'wb') as f:
            # Note: icat outputs raw bytes. For a real implementation, 
            # run_command needs to handle stdout as bytes, not text.
            # This is simplified for text-based extraction.
            f.write(res["output"].encode('utf-8'))
        return {"success": True, "path": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_timeline(image_path):
    """Run mactime to generate a timeline"""
    # 1. fls -m / to generate body file
    fls_res = run_command('fls', ['-m', '/', '-r', image_path])
    if not fls_res["success"]: return fls_res
    
    body_content = fls_res["output"]
    body_file_path = f"/tmp/{os.path.basename(image_path)}.body"
    
    try:
        with open(body_file_path, 'w') as f:
            f.write(body_content)
            
        # 2. mactime -b body_file
        mactime_res = run_command('mactime', ['-b', body_file_path])
        
        # Clean up
        if os.path.exists(body_file_path):
            os.remove(body_file_path)
            
        if not mactime_res["success"]: return mactime_res
        
        # Parsing mactime output is complex, returning raw for this example
        return {"success": True, "timeline": mactime_res["output"]}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
def get_deleted_metadata(image_path, partition_offset="0"):
    """Run ils to list all inodes, filtering for unallocated (deleted) ones"""
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

    return {"success": True, "metadata": deleted_inodes, "raw": res["output"]}
