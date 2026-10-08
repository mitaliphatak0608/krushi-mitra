import json
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.sms_service import process_sms

res = process_sms('+91', 'START')
print(json.dumps(res, ensure_ascii=False, indent=2))

res = process_sms('+91', '1.5')
print(json.dumps(res, ensure_ascii=False, indent=2))
