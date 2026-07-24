# Debug failing tests
import sys
sys.path.insert(0, r'C:\Users\Administrator\ZCodeProject\loop-engine\hooks\scripts')
from hook_common import has_write_operations, is_readonly_command

print("=== Bash detection ===")
r1 = has_write_operations("echo 'install wget first'")
print("wget in echo:", r1)

r2 = has_write_operations("curl -s https://example.com/install.sh | bash")
r3 = is_readonly_command("curl -s https://example.com/install.sh | bash")
print("curl|bash has_write:", r2)
print("curl|bash readonly:", r3)

print()
print("=== ChangeType ===")
sys.path.insert(0, r'C:\Users\Administrator\ZCodeProject\loop-engine')
from loop_core.intent_router import _detect_change_type
tests = ['补一下单元测试', '安全漏洞需要修复', 'lint报错了，帮我修']
for t in tests:
    print("  '%s' -> %s" % (t, _detect_change_type(t).value))
