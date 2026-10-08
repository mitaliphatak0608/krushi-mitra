import sys
from backend.sms_service import process_sms
from backend.sms_state import _sms_sessions
import backend.database as db

def run_tests():
    db.init_db()
    print("Running regression tests...")
    
    # Setup test profile manually for phone1
    phone1 = "+123"
    
    # Complete profile setup
    process_sms(phone1, "START")
    process_sms(phone1, "1") # en
    process_sms(phone1, "7.0") # landholding
    process_sms(phone1, "Marathwada") # region
    process_sms(phone1, "Jowar") # crop
    process_sms(phone1, "SC") # category
    process_sms(phone1, "50000") # income
    process_sms(phone1, "Kharif") # season
    process_sms(phone1, "1") # loan - yes
    process_sms(phone1, "2") # tax - no
    
    # We should be in RECOMMENDATIONS now. 
    # Let's find index of KCC, Karjmafi, Solar Pump, Farm Pond.
    session = _sms_sessions[phone1]
    schemes = session.get("recommended_schemes", [])
    
    # Map scheme_id to index (1-based)
    scheme_idx = {s["id"]: str(i+1) for i, s in enumerate(schemes)}
    
    # TEST 1
    print("\n--- TEST 1: KCC -> APPLY ---")
    kcc_idx = scheme_idx.get("KCC")
    if not kcc_idx:
        print("KCC not recommended!")
    else:
        res1 = process_sms(phone1, kcc_idx)
        print("Selected KCC:", "Kisan Credit Card" in res1["message"])
        res_apply = process_sms(phone1, "APPLY")
        print("Apply result mentions KCC?", "Kisan Credit Card" in res_apply["message"])
        print("Apply result mentions Karjmafi?", "Karjmafi" in res_apply["message"])
        if "Karjmafi" in res_apply["message"]:
            print("FAILED TEST 1")
        else:
            print("PASSED TEST 1")
            
    # TEST 2
    print("\n--- TEST 2: BACK -> Karjmafi -> APPLY ---")
    process_sms(phone1, "BACK")
    karj_idx = scheme_idx.get("KARJMAFI")
    if not karj_idx:
        print("KARJMAFI not recommended!")
    else:
        process_sms(phone1, karj_idx)
        res_apply = process_sms(phone1, "APPLY")
        print("Apply result mentions Karjmafi?", "Karjmafi" in res_apply["message"])
        if "Karjmafi" not in res_apply["message"]:
            print("FAILED TEST 2")
        else:
            print("PASSED TEST 2")

    # TEST 3
    print("\n--- TEST 3: BACK -> Solar Pump -> APPLY ---")
    process_sms(phone1, "BACK")
    solar_idx = scheme_idx.get("SOLAR_PUMP")
    process_sms(phone1, solar_idx)
    res_apply = process_sms(phone1, "APPLY")
    print("Apply mentions Solar Pump?", "Solar Pump" in res_apply["message"])

    # TEST 4
    print("\n--- TEST 4: BACK -> Farm Pond -> APPLY ---")
    process_sms(phone1, "BACK")
    pond_idx = scheme_idx.get("FARM_POND")
    process_sms(phone1, pond_idx)
    res_apply = process_sms(phone1, "APPLY")
    print("Apply mentions Farm Pond?", "Farm Pond" in res_apply["message"])

    # TEST 5
    print("\n--- TEST 5: Restart with START ---")
    process_sms(phone1, "START")
    session = _sms_sessions[phone1]
    if session.get("selected_scheme_id"):
        print("FAILED TEST 5: selected_scheme_id leaked")
    else:
        print("PASSED TEST 5")

    # TEST 6
    print("\n--- TEST 6: Independent Phones ---")
    phone2 = "+999"
    process_sms(phone2, "START")
    process_sms(phone2, "1")
    session1 = _sms_sessions[phone1]
    session2 = _sms_sessions[phone2]
    if session1["state"] == session2["state"]:
        print("FAILED TEST 6")
    else:
        print("PASSED TEST 6")

    # TEST 7
    print("\n--- TEST 7: Invalid vs Valid Query Intent Gate ---")
    invalid_queries = [
        "Tell me a joke",
        "What is Python?",
        "Who won cricket?",
        "What is the weather?",
        "Who is the Prime Minister?"
    ]
    valid_queries = [
        "What schemes are available?",
        "What documents are required?",
        "How can I apply?",
        "Tell me about KCC",
        "Can I get a solar pump?",
        "पीक विमा माहिती",
        "मला सौर पंपाची माहिती हवी आहे"
    ]
    
    # Reset to a stable state (e.g., RECOMMENDATIONS)
    process_sms(phone1, "START")
    process_sms(phone1, "1")
    for val in ["7.0", "Marathwada", "Jowar", "SC", "50000", "Kharif", "1", "2"]:
        process_sms(phone1, val)
        
    for q in invalid_queries:
        res = process_sms(phone1, q)
        if "❌ Invalid Query" not in res["message"]:
            print(f"FAILED TEST 7 (Invalid): Expected Invalid Query for '{q}'")
        else:
            print(f"PASSED TEST 7 (Invalid): '{q}'")
            
    for q in valid_queries:
        res = process_sms(phone1, q)
        if "❌ Invalid Query" in res["message"]:
            print(f"FAILED TEST 7 (Valid): Expected valid processing for '{q.encode('ascii', 'ignore').decode()}'")
        else:
            print(f"PASSED TEST 7 (Valid): '{q.encode('ascii', 'ignore').decode()}'")

    # TEST 8
    print("\n--- TEST 8: State Preservation on Invalid Query ---")
    
    # Go to recommendations state
    process_sms(phone1, "START")
    process_sms(phone1, "1")
    for val in ["7.0", "Marathwada", "Jowar", "SC", "50000", "Kharif", "1", "2"]:
        process_sms(phone1, val)
    
    # State should be RECOMMENDATIONS
    state = _sms_sessions[phone1]["state"]
    if state != "RECOMMENDATIONS":
        print(f"Setup failed, state is {state}")
        
    # Unrelated query -> remain in RECOMMENDATIONS
    process_sms(phone1, "What is Python?")
    new_state = _sms_sessions[phone1]["state"]
    if new_state != "RECOMMENDATIONS":
        print(f"FAILED TEST 8: State changed to {new_state} instead of RECOMMENDATIONS")
    else:
        print("PASSED TEST 8: Remain in RECOMMENDATIONS")
        
    # Select KCC -> Scheme details -> Unrelated query -> remain in SCHEME_DETAILS and keep selected_scheme_id
    schemes = _sms_sessions[phone1].get("recommended_schemes", [])
    scheme_idx = {s["id"]: str(i+1) for i, s in enumerate(schemes)}
    kcc_idx = scheme_idx.get("KCC")
    
    if kcc_idx:
        process_sms(phone1, kcc_idx)
        state_before = _sms_sessions[phone1]["state"]
        selected_before = _sms_sessions[phone1].get("selected_scheme_id")
        
        process_sms(phone1, "Who won cricket?")
        state_after = _sms_sessions[phone1]["state"]
        selected_after = _sms_sessions[phone1].get("selected_scheme_id")
        
        if state_after != "SCHEME_DETAILS" or selected_after != "KCC":
            print(f"FAILED TEST 8: State ({state_after}) or Scheme ({selected_after}) lost")
        else:
            print("PASSED TEST 8: Remain in SCHEME_DETAILS with selected_scheme_id KCC")

    # TEST 9: Persistence reload
    print("\n--- TEST 9: Persistence reload ---")
    _sms_sessions.clear()
    import backend.sms_state as sms_state
    restored = sms_state.get_session(phone1)
    if restored["state"] == "SCHEME_DETAILS" and restored.get("selected_scheme_id") == "KCC":
        print("PASSED TEST 9: Session restored correctly after restart")
    else:
        print(f"FAILED TEST 9: Session lost after restart (state={restored.get('state')})")
        
    # TEST 10: Messages saved
    print("\n--- TEST 10: Messages history ---")
    history = db.get_sms_history(phone1)
    if len(history) > 10:
        print(f"PASSED TEST 10: {len(history)} messages saved in history")
    else:
        print(f"FAILED TEST 10: Only {len(history)} messages saved in history")

    # TEST 11: Select KCC -> restart -> APPLY
    print("\n--- TEST 11: Restart survival of selected_scheme_id ---")
    _sms_sessions.clear()
    res_apply = process_sms(phone1, "APPLY")
    if "Kisan Credit Card" in res_apply["message"]:
         print("PASSED TEST 11: State survived restart to apply KCC")
    else:
         print("FAILED TEST 11: KCC lost on apply after restart")

if __name__ == "__main__":
    run_tests()
