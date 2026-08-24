import sys
import io
from enum import Enum
from typing import Tuple, List, Dict, Optional
from playwright.sync_api import Page
from app.utils.logger import log_info, log_error, log_warning
from app.automation.guards import check_creator_studio_or_waitlist_guard

class IdentityType(Enum):
    TARGET_PAGE_ACTIVE = "TARGET_PAGE_ACTIVE"
    DIFFERENT_PAGE_ACTIVE = "DIFFERENT_PAGE_ACTIVE"
    PERSONAL_PROFILE_ACTIVE = "PERSONAL_PROFILE_ACTIVE"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"


def clean_identity_name(raw_name: str) -> str:
    """Removes common Facebook UI prefixes/suffixes to extract pure identity name."""
    clean = raw_name.strip()
    for prefix in [
        "profile picture for",
        "picture for",
        "switch to",
        "account controls for",
        "account:",
        "profile of",
    ]:
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):].strip()
    for suffix in [
        "'s timeline",
        "'s profile",
        "'s account",
    ]:
        if clean.lower().endswith(suffix):
            clean = clean[:-len(suffix)].strip()
    return clean


def classify_identity_signals(
    target_page_name: str,
    signals: List[Dict[str, str]]
) -> Tuple[IdentityType, str]:
    """
    Pure logic identity classifier based on Strict Evidence Hierarchy.
    STRONG CURRENT ACTIVE IDENTITY evidence > generic Page features.
    If personal identity evidence exists and there is no explicit active Page identity matching target_page_name:
      -> MUST classify as PERSONAL_PROFILE_ACTIVE.
    NEVER choose TARGET_PAGE_ACTIVE from generic Page UI or weak evidence.
    """
    target_clean = target_page_name.strip().lower()

    if not signals:
        log_info("[IDENTITY DEBUG] personal_profile_evidence = []", tag="IDENTITY_DEBUG")
        log_info("[IDENTITY DEBUG] page_identity_evidence = []", tag="IDENTITY_DEBUG")
        log_info("[IDENTITY DEBUG] target_page_evidence = []", tag="IDENTITY_DEBUG")
        log_info("[IDENTITY DEBUG] final_classification = IDENTITY_AMBIGUOUS (Active: Unknown)", tag="IDENTITY_DEBUG")
        return IdentityType.IDENTITY_AMBIGUOUS, "Unknown (No identity evidence detected)"

    personal_profile_evidence: List[str] = []
    page_identity_evidence: List[str] = []
    target_page_evidence: List[str] = []

    for sig in signals:
        raw_text = sig.get("text", "").strip()
        sig_type = sig.get("type", "")

        # Skip generic uninformative labels & generic page features
        if not raw_text or raw_text.lower() in [
            "your profile",
            "facebook",
            "home",
            "menu",
            "account controls and settings",
            "professional dashboard",
            "insights",
            "ad center",
            "page settings",
        ]:
            continue

        cleaned_name = clean_identity_name(raw_text)
        if not cleaned_name or cleaned_name.lower() in ["your profile", "facebook", "home"]:
            continue

        if cleaned_name.lower() == target_clean:
            target_page_evidence.append(cleaned_name)
        elif sig_type == "different_page":
            page_identity_evidence.append(cleaned_name)
        else:
            personal_profile_evidence.append(cleaned_name)

    log_info(f"[IDENTITY DEBUG] personal_profile_evidence = {personal_profile_evidence}", tag="IDENTITY_DEBUG")
    log_info(f"[IDENTITY DEBUG] page_identity_evidence = {page_identity_evidence}", tag="IDENTITY_DEBUG")
    log_info(f"[IDENTITY DEBUG] target_page_evidence = {target_page_evidence}", tag="IDENTITY_DEBUG")

    final_type: IdentityType = IdentityType.IDENTITY_AMBIGUOUS
    active_name: str = "Unknown"

    # Hierarchy Evaluation
    if target_page_evidence and not personal_profile_evidence:
        final_type = IdentityType.TARGET_PAGE_ACTIVE
        active_name = target_page_name
    elif personal_profile_evidence:
        final_type = IdentityType.PERSONAL_PROFILE_ACTIVE
        active_name = personal_profile_evidence[0]
    elif page_identity_evidence:
        final_type = IdentityType.DIFFERENT_PAGE_ACTIVE
        active_name = page_identity_evidence[0]
    else:
        final_type = IdentityType.IDENTITY_AMBIGUOUS
        active_name = "Unknown (Ambiguous evidence)"

    log_info(f"[IDENTITY DEBUG] final_classification = {final_type.value} (Active: {active_name})", tag="IDENTITY_DEBUG")

    # Runtime Safety Assertion
    if final_type == IdentityType.PERSONAL_PROFILE_ACTIVE:
        if active_name.lower() != target_clean:
            assert final_type != IdentityType.TARGET_PAGE_ACTIVE, \
                "Safety Assertion Violation: PERSONAL_PROFILE_ACTIVE cannot be TARGET_PAGE_ACTIVE!"

    return final_type, active_name


class IdentityVerifier:
    """
    Strict Active Facebook Page Identity Verifier with Real-DOM Diagnostic Mode.
    Inspects specific active identity elements in the DOM.
    """
    def __init__(self, page: Page):
        self.page = page

    def verify_active_identity(self, expected_page_name: str) -> Tuple[bool, str, IdentityType, List[str]]:
        """
        Inspects current Facebook DOM to determine active identity type and name.
        Returns (is_verified, active_identity_name, identity_type, diagnostic_logs).
        """
        log_info(f"[PAGE VERIFY] Target Page requested: '{expected_page_name}'", tag="PAGE_VERIFY")

        # 1. Creator Studio / Waitlist Guard Check
        if check_creator_studio_or_waitlist_guard(self.page):
            log_error("[GUARD] Creator Studio / Waitlist detected", tag="GUARD")
            log_error("[PAGE VERIFY] FAILED", tag="PAGE_VERIFY")
            return False, "Creator Studio / Waitlist", IdentityType.IDENTITY_AMBIGUOUS, []

        collected_signals: List[Dict[str, str]] = []
        diagnostic_logs: List[str] = []

        log_info("[REAL-DOM DIAGNOSTIC] Beginning active identity DOM inspection...", tag="DIAGNOSTIC")

        # Evidence Signal 1: Top Navigation Bar Profile Button Image Alt & Tooltip
        try:
            profile_selectors = [
                "[aria-label='Your profile'] img",
                "[aria-label='Account Controls and Settings'] img",
                "div[role='banner'] [aria-label*='Profile'] img",
                "div[role='navigation'] [aria-label*='Profile'] img",
            ]
            for selector in profile_selectors:
                elems = self.page.query_selector_all(selector)
                for elem in elems:
                    if elem.is_visible():
                        alt = (elem.get_attribute("alt") or "").strip()
                        if alt and alt.lower() != "profile picture":
                            sig = {"type": "profile_image_alt", "text": alt, "selector": selector}
                            collected_signals.append(sig)
                            diag = f"Signal 1 (Profile Img Alt): text='{alt}' | selector='{selector}' | visible=True"
                            diagnostic_logs.append(diag)
                            log_info(f"[REAL-DOM DIAGNOSTIC] {diag}", tag="DIAGNOSTIC")
                            break
                if collected_signals:
                    break
        except Exception as e:
            log_warning(f"[REAL-DOM DIAGNOSTIC] Signal 1 error: {str(e)}", tag="DIAGNOSTIC")

        # Evidence Signal 2: Left Navigation Bar Active Identity Heading / Link
        try:
            nav_profile_selectors = [
                "div[role='navigation'] a[href*='/me/'] span",
                "div[role='navigation'] a[href*='/profile.php'] span",
                "div[role='navigation'] h2 + a span",
            ]
            for selector in nav_profile_selectors:
                elem = self.page.query_selector(selector)
                if elem and elem.is_visible():
                    nav_text = elem.inner_text().strip()
                    href = elem.evaluate("el => el.closest('a') ? el.closest('a').href : ''") or ""
                    if nav_text:
                        sig = {"type": "nav_profile_link", "text": nav_text, "href": href, "selector": selector}
                        collected_signals.append(sig)
                        diag = f"Signal 2 (Nav Profile Link): text='{nav_text}' | href='{href}' | visible=True"
                        diagnostic_logs.append(diag)
                        log_info(f"[REAL-DOM DIAGNOSTIC] {diag}", tag="DIAGNOSTIC")
                        break
        except Exception as e:
            log_warning(f"[REAL-DOM DIAGNOSTIC] Signal 2 error: {str(e)}", tag="DIAGNOSTIC")

        # Execute Strict Pure Logic Identity Classifier
        identity_type, active_identity = classify_identity_signals(expected_page_name, collected_signals)

        log_info(f"[PAGE CHECK] Identity type: {identity_type.value}", tag="PAGE_CHECK")
        log_info(f"[PAGE CHECK] Active identity: {active_identity}", tag="PAGE_CHECK")
        log_info(f"[PAGE CHECK] Target Page: {expected_page_name}", tag="PAGE_CHECK")

        if identity_type == IdentityType.TARGET_PAGE_ACTIVE:
            log_info("[PAGE CHECK] TARGET_ALREADY_ACTIVE", tag="PAGE_CHECK")
            log_info(f"[PAGE CHECK] Target Page '{expected_page_name}' is already active", tag="PAGE_CHECK")
            log_info("[PAGE VERIFY] SUCCESS", tag="PAGE_VERIFY")
            return True, expected_page_name, identity_type, diagnostic_logs
        else:
            log_info("[PAGE CHECK] TARGET_NOT_ACTIVE", tag="PAGE_CHECK")
            log_info("[PAGE SWITCH] PAGE_SWITCH_REQUIRED", tag="PAGE_SWITCH")
            return False, active_identity, identity_type, diagnostic_logs
