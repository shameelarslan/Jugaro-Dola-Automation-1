import sys
import io
from pathlib import Path

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.facebook.identity_verifier import classify_identity_signals, IdentityType

def test_identity_classifier_exact_fixtures():
    target_page = "Huang"
    print("\n" + "="*60)
    print("--- RUNNING IDENTITY CLASSIFIER EXACT REAL-DOM FIXTURE TESTS ---")
    print(f"Target Page: '{target_page}'")
    print("="*60 + "\n")

    # -------------------------------------------------------------------------
    # FIXTURE 1: Real-World Failure Scenario ("John Dee" + Professional Dashboard present)
    # -------------------------------------------------------------------------
    signals_f1 = [
        {"type": "profile_control", "text": "Your profile"},
        {"type": "nav_profile_link", "text": "John Dee"},
        {"type": "page_feature", "text": "Professional dashboard"}
    ]
    id_type_1, name_1 = classify_identity_signals(target_page, signals_f1)
    print(f"[FIXTURE 1] Profile Control='Your profile' | Nav='John Dee' | Feature='Professional dashboard'")
    print(f" -> Result IdentityType: {id_type_1.value}")
    print(f" -> Result Active Identity Name: '{name_1}'")

    assert id_type_1 != IdentityType.TARGET_PAGE_ACTIVE, "ERROR: Real-world regression! 'John Dee' was falsely classified as TARGET_PAGE_ACTIVE!"
    assert id_type_1 == IdentityType.PERSONAL_PROFILE_ACTIVE, f"Expected PERSONAL_PROFILE_ACTIVE, got {id_type_1.value}"
    assert name_1 == "John Dee", f"Expected 'John Dee', got '{name_1}'"
    print(" -> FIXTURE 1 PASSED cleanly! (Real-world regression successfully fixed)\n")

    # -------------------------------------------------------------------------
    # FIXTURE 2: Real-World "清浅Huang" Scenario (+ Professional Dashboard present)
    # -------------------------------------------------------------------------
    signals_f2 = [
        {"type": "profile_control", "text": "Your profile"},
        {"type": "nav_profile_link", "text": "清浅Huang"},
        {"type": "page_feature", "text": "Professional dashboard"}
    ]
    id_type_2, name_2 = classify_identity_signals(target_page, signals_f2)
    print(f"[FIXTURE 2] Profile Control='Your profile' | Nav='清浅Huang' | Feature='Professional dashboard'")
    print(f" -> Result IdentityType: {id_type_2.value}")
    print(f" -> Result Active Identity Name: '{name_2}'")

    assert id_type_2 != IdentityType.TARGET_PAGE_ACTIVE, "ERROR: Substring false-positive! '清浅Huang' matched 'Huang'!"
    assert id_type_2 == IdentityType.PERSONAL_PROFILE_ACTIVE, f"Expected PERSONAL_PROFILE_ACTIVE, got {id_type_2.value}"
    assert name_2 == "清浅Huang", f"Expected '清浅Huang', got '{name_2}'"
    print(" -> FIXTURE 2 PASSED cleanly!\n")

    # -------------------------------------------------------------------------
    # FIXTURE 3: True Active Page Scenario ("Huang")
    # -------------------------------------------------------------------------
    signals_f3 = [
        {"type": "profile_image_alt", "text": "Profile picture for Huang"},
        {"type": "nav_profile_link", "text": "Huang"}
    ]
    id_type_3, name_3 = classify_identity_signals(target_page, signals_f3)
    print(f"[FIXTURE 3] Profile Img Alt='Profile picture for Huang' | Nav='Huang'")
    print(f" -> Result IdentityType: {id_type_3.value}")
    print(f" -> Result Active Identity Name: '{name_3}'")

    assert id_type_3 == IdentityType.TARGET_PAGE_ACTIVE, f"Expected TARGET_PAGE_ACTIVE, got {id_type_3.value}"
    assert name_3 == "Huang", f"Expected 'Huang', got '{name_3}'"
    print(" -> FIXTURE 3 PASSED cleanly!\n")

    # -------------------------------------------------------------------------
    # FIXTURE 4: Different Active Page Scenario ("Tech News")
    # -------------------------------------------------------------------------
    signals_f4 = [
        {"type": "different_page", "text": "Tech News"}
    ]
    id_type_4, name_4 = classify_identity_signals(target_page, signals_f4)
    print(f"[FIXTURE 4] Active Page = 'Tech News' | Target = 'Huang'")
    print(f" -> Result IdentityType: {id_type_4.value}")
    print(f" -> Result Active Identity Name: '{name_4}'")

    assert id_type_4 == IdentityType.DIFFERENT_PAGE_ACTIVE, f"Expected DIFFERENT_PAGE_ACTIVE, got {id_type_4.value}"
    assert name_4 == "Tech News", f"Expected 'Tech News', got '{name_4}'"
    print(" -> FIXTURE 4 PASSED cleanly!\n")

    # -------------------------------------------------------------------------
    # FIXTURE 5: Ambiguous Signals Scenario
    # -------------------------------------------------------------------------
    signals_f5 = []
    id_type_5, name_5 = classify_identity_signals(target_page, signals_f5)
    print(f"[FIXTURE 5] Empty Signals | Target = 'Huang'")
    print(f" -> Result IdentityType: {id_type_5.value}")
    print(f" -> Result Active Identity Name: '{name_5}'")

    assert id_type_5 == IdentityType.IDENTITY_AMBIGUOUS, f"Expected IDENTITY_AMBIGUOUS, got {id_type_5.value}"
    print(" -> FIXTURE 5 PASSED cleanly!\n")

    print("="*60)
    print("--- ALL 5 REAL-DOM FIXTURE REGRESSION TESTS PASSED! ---")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_identity_classifier_exact_fixtures()
