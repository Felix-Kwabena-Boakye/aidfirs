import sys

with open('aidfirs-agent/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''        if not target_device and devices:
            target_device = devices[0]
            print(f"[Job-{job_id}] Warning: No precise device match found. Defaulting to first active device: {target_device.drive_letter}")

        if not target_device:
            err_msg = "No connected USB/HDD drive detected to perform forensic operations."'''

new_block = '''        if not target_device:
            err_msg = f"Device not found locally. Please connect device {device_id} to this agent."'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('aidfirs-agent/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Replacement made.")
else:
    print("FAILED: Old block not found in file.")
    # Debug: print the exact area around lines 138-144 to find differences
    lines = content.split('\n')
    for i in range(137, min(145, len(lines))):
        print(f"Line {i+1}: {repr(lines[i])}")