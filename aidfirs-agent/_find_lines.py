with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'target_device' in lower and ('devices' in lower or 'err_msg' in lower or 'failed' in lower):
        print(f"{i}:{repr(line)}")