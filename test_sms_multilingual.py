import json
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.sms_service import process_sms

def print_res(res):
    print(f"[{res.get('language')}] -> {res.get('state')}")
    print(res.get('message'))
    print("-" * 40)

# Test Marathi Flow
print_res(process_sms('+91', 'START'))
print_res(process_sms('+91', '3')) # Marathi
print_res(process_sms('+91', '2.5')) # Q1
print_res(process_sms('+91', 'Marathwada')) # Q2
print_res(process_sms('+91', 'Soybean')) # Q3
print_res(process_sms('+91', 'General')) # Q4
print_res(process_sms('+91', '45000')) # Q5
print_res(process_sms('+91', 'Kharif')) # Q6
print_res(process_sms('+91', '1')) # Q7 loan yes
print_res(process_sms('+91', '2')) # Q8 tax no (eligible for PM Kisan)

# Scheme Details in Marathi
print_res(process_sms('+91', '1'))

# Hindi Web
print_res(process_sms('+91_hi', 'START'))
print_res(process_sms('+91_hi', '2'))
print_res(process_sms('+91_hi', 'वेब'))
