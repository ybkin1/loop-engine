import sys
sys.path.insert(0, r'C:\Users\Administrator\ZCodeProject\loop-engine')
from loop_core.intent_router import _detect_change_type, BUG_FIX_KEYWORDS, QUALITY_FIX_KEYWORDS

test = '补一下单元测试'
result = _detect_change_type(test)
print("Input:", repr(test))
print("Result:", result.value)

# Check each keyword
for kw in BUG_FIX_KEYWORDS:
    if kw in test:
        print("  BUG_FIX match:", repr(kw))

for kw in QUALITY_FIX_KEYWORDS:
    if kw in test:
        print("  QUALITY_FIX match:", repr(kw))
