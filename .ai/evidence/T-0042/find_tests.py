"""Fix test_bypass_matrix.py — update curl/wget known limitation tests.
These were xfail tests verifying that curl/wget are UNDETECTABLE (known limitation).
Now that we've added detection, these tests should verify the OPPOSITE: they ARE detected.
"""
import re

path = r'C:\Users\Administrator\ZCodeProject\loop-engine\tests\test_bypass_matrix.py'
content = open(path, encoding='utf-8').read()
lines = content.splitlines()

# Find the two test methods
curl_line = None
wget_line = None
for i, line in enumerate(lines):
    if 'def test_lim_curl_download_undetectable' in line:
        curl_line = i
    if 'def test_lim_wget_download_undetectable' in line:
        wget_line = i

print(f"curl test at line {curl_line + 1 if curl_line else 'NOT FOUND'}")
print(f"wget test at line {wget_line + 1 if wget_line else 'NOT FOUND'}")

if curl_line is not None:
    # Find the function body (indented lines after def)
    start = curl_line
    end = start + 1
    while end < len(lines) and (lines[end].startswith('    ') or lines[end].strip() == ''):
        end += 1
    print(f"curl test: lines {start+1}-{end}")
    for j in range(start, min(end, start+20)):
        print(f"  {j+1}: {lines[j]}")

if wget_line is not None:
    start = wget_line
    end = start + 1
    while end < len(lines) and (lines[end].startswith('    ') or lines[end].strip() == ''):
        end += 1
    print(f"wget test: lines {start+1}-{end}")
    for j in range(start, min(end, start+20)):
        print(f"  {j+1}: {lines[j]}")
