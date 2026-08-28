"""
Isolated CSS / ARIA / Text Selectors Registry for Dola.com UI.
Allows easy updating of UI selectors if Dola modifies its frontend layout.
"""

class DolaSelectors:
    # Textarea / Prompt input field selectors
    PROMPT_INPUTS = [
        "textarea[placeholder*='Ask']",
        "textarea[placeholder*='Message']",
        "textarea[placeholder*='Dola']",
        "textarea",
        "div[contenteditable='true']"
    ]

    # Submit / Send Button selectors (ordered most specific → most generic)
    SEND_BUTTONS = [
        "button[data-testid='send-button']",
        "button[type='submit']",
        "button[aria-label='Send message']",
        "button[aria-label*='Send']",
        "button[aria-label*='send']",
        "button[aria-label*='submit']",
        "button[aria-label*='Submit']",
        "form button[type='submit']",
        "div.send-button",
        "button.send-btn",
        "button.submit-btn",
        "[data-testid='chat-send']",
        "button:has(svg[class*='send'])",
        "div[role='button'][aria-label*='Send']",
        "div[role='button']:has(svg)"
    ]

    # Mode / Video creation options button
    CREATE_VIDEO_BTN = [
        "button:has-text('Create Video')",
        "div:has-text('Create Video')",
        "[aria-label*='Video']"
    ]

    # Model selector dropdown & options
    MODEL_DROPDOWN = [
        "button:has-text('Model')",
        "div:has-text('Model')",
        "button:has-text('Seedance')"
    ]
    MODEL_SEEDANCE_2 = [
        "li:has-text('Dreamina Seedance 2.0 Fast')",
        "div:has-text('Dreamina Seedance 2.0 Fast')",
        "li:has-text('Seedance 2.0')",
        "div:has-text('Seedance 2.0')"
    ]

    # Aspect Ratio dropdown & options
    RATIO_DROPDOWN = [
        "button:has-text('Ratio')",
        "div:has-text('Ratio')",
        "button:has-text('9:16')",
        "button:has-text('16:9')",
        "button:has-text('4:3')",
        "button:has-text('1:1')",
        "[aria-label*='ratio' i]",
        "[aria-label*='aspect' i]",
        "button:has-text('Aspect Ratio')",
    ]
    RATIO_9_16 = [
        # Direct button (ratio already visible as button)
        "button[data-value='9:16']",
        "button[value='9:16']",
        "[data-ratio='9:16']",
        "[data-value='9:16']",
        # List / option items
        "li:has-text('9:16')",
        "div[role='option']:has-text('9:16')",
        "div[role='menuitem']:has-text('9:16')",
        # Generic text containers
        "div:has-text('9:16')",
        "span:has-text('9:16')",
        "button:has-text('9:16')",
        # aria
        "[aria-label='9:16']",
        "[title='9:16']",
    ]

    # Chat Message Blocks / Containers
    CHAT_MESSAGE_NODES = [
        "div[data-id]",
        "div.chat-message",
        "div.message-item",
        "div[role='article']",
        "div.flex-col > div.relative"
    ]

    # Download Button / Video Card selectors
    DOWNLOAD_BUTTONS = [
        ".purza-dl-btn",
        "button:has-text('Download')",
        "a[download]",
        "svg[data-icon='download']",
        "button[aria-label*='Download']"
    ]

    # User Profile / Logged In indicator
    PROFILE_INDICATORS = [
        "img[alt*='avatar']",
        "div.avatar",
        "button[aria-label*='Profile']",
        "div.user-profile"
    ]
