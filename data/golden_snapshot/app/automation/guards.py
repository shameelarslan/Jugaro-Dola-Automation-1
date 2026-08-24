"""
Creator Studio & Waitlist Guard.
Detects accidental redirects to Creator Studio, Waitlists, or external Meta pages.
"""

from app.utils.logger import log_error, log_warning

def check_creator_studio_or_waitlist_guard(page) -> bool:
    """
    Returns True if an unexpected Creator Studio or Waitlist page is detected.
    Inspects URL patterns and page DOM text.
    """
    try:
        url = page.url.lower()
        guard_keywords = ["creatorstudio", "waitlist", "business.facebook.com/latest", "meta_business_suite"]

        for kw in guard_keywords:
            if kw in url:
                log_warning(f"[GUARD] Creator Studio / Waitlist URL detected: {page.url}", tag="GUARD")
                log_warning("[GUARD] This is NOT proof of Page activation.", tag="GUARD")
                return True

        # Check DOM text content for Waitlist or Creator Studio indicators
        page_content = page.content().lower()
        if "join waitlist" in page_content or "creator studio" in page_content:
            log_warning("[GUARD] Creator Studio / Waitlist content detected in page DOM.", tag="GUARD")
            log_warning("[GUARD] This is NOT proof of Page activation.", tag="GUARD")
            return True

        return False
    except Exception as e:
        log_error(f"[GUARD ERROR] Exception during guard check: {str(e)}", tag="GUARD")
        return False
