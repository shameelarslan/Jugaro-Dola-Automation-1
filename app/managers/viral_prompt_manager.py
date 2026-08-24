import os
import re
import html
import subprocess
from html.parser import HTMLParser
from typing import List, Dict, Any, Optional
from app.core.logger import logger

class _ViralPromptHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_h1 = False
        self.in_title = False
        self.in_content = False
        self.title = ""
        self.content_chunks = []
        self.image_url = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "h1":
            self.in_h1 = True
        elif tag == "title":
            self.in_title = True
        elif tag == "div" and attrs_dict.get("class") == "content":
            self.in_content = True
        elif tag == "img":
            src = attrs_dict.get("src")
            if src and not self.image_url:
                self.image_url = src

    def handle_endtag(self, tag):
        if tag == "h1":
            self.in_h1 = False
        elif tag == "title":
            self.in_title = False
        elif tag == "div" and self.in_content:
            self.in_content = False

    def handle_data(self, data):
        if self.in_h1 or (self.in_title and not self.title):
            self.title += data
        elif self.in_content:
            self.content_chunks.append(data)

class ViralPromptManager:
    """
    Manages loading, parsing, searching, and exporting 200+ viral HTML prompt files.
    """
    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self.prompts_dir = storage_dir
        else:
            # Default to data/viral_prompts relative to app base
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.prompts_dir = os.path.join(base_dir, "data", "viral_prompts")
            
        os.makedirs(self.prompts_dir, exist_ok=True)
        self._cached_prompts: List[Dict[str, Any]] = []

    def get_prompts_directory(self) -> str:
        return self.prompts_dir

    def open_folder_in_explorer(self):
        """Opens the viral prompts folder in Windows Explorer."""
        try:
            os.makedirs(self.prompts_dir, exist_ok=True)
            if os.name == 'nt':
                os.startfile(self.prompts_dir)
            else:
                subprocess.Popen(["xdg-open", self.prompts_dir])
        except Exception as e:
            logger.error(f"Failed to open viral prompts folder: {e}", category="PROMPTS")

    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parses an individual HTML prompt file and returns structured prompt data."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                html_text = f.read()

            parser = _ViralPromptHTMLParser()
            parser.feed(html_text)

            title = parser.title.strip()
            if not title:
                # Fallback to filename without extension
                base = os.path.basename(file_path)
                title = os.path.splitext(base)[0]

            content = "".join(parser.content_chunks).strip()
            if not content:
                # Regex fallback for <div class="content">...</div>
                match = re.search(r'<div class="content">(.*?)</div>', html_text, re.DOTALL)
                if match:
                    raw = match.group(1)
                    clean = re.sub(r'<[^>]+>', '', raw)
                    content = html.unescape(clean).strip()

            if not content:
                # Fallback to entire body text if content div is not found
                clean = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL)
                clean = re.sub(r'<script[^>]*>.*?</script>', '', clean, flags=re.DOTALL)
                clean = re.sub(r'<[^>]+>', '', clean)
                content = html.unescape(clean).strip()

            # Auto-categorization
            category = self._detect_category(title, content)

            rel_name = os.path.basename(file_path)
            prompt_id = f"viral_{abs(hash(file_path)) % 1000000:06d}"

            return {
                "id": prompt_id,
                "file_path": file_path,
                "filename": rel_name,
                "title": title,
                "content": content,
                "category": category,
                "image_url": parser.image_url,
                "char_count": len(content),
                "word_count": len(content.split())
            }
        except Exception as e:
            logger.error(f"Error parsing viral prompt file {file_path}: {e}", category="PROMPTS")
            return None

    def _detect_category(self, title: str, content: str) -> str:
        """Determines best-fit category based on content tags and keywords."""
        text = (title + " " + content[:400]).lower()
        if any(w in text for w in ["comedy", "prank", "living statue", "funny", "slapstick", "humor", "joke", "hilarious", "parody"]):
            return "Comedy & Pranks"
        elif any(w in text for w in ["survival", "game", "gaming", "minecraft", "gta", "roblox", "quest", "level", "royal survival", "challenge", "escape", "battle"]):
            return "Survival & Gaming"
        elif any(w in text for w in ["anime", "manga", "2d", "doodle", "stickman", "cartoon", "animation", "3d animation"]):
            return "Anime & Animation"
        elif any(w in text for w in ["dog", "cat", "husky", "animal", "pet", "lion", "tiger", "bear", "puppy", "duck"]):
            return "Animals & Pets"
        elif any(w in text for w in ["baby", "family", "mom", "dad", "parent", "kid", "child"]):
            return "Baby & Family"
        elif any(w in text for w in ["emotional", "drama", "heartbreak", "life story", "love story", "sad", "tear", "struggle"]):
            return "Emotional & Drama"
        elif any(w in text for w in ["sports", "legend", "athlete", "football", "cricket", "basketball", "gym", "workout"]):
            return "Sports & Fitness"
        elif any(w in text for w in ["horror", "scary", "mystery", "ghost", "abandoned", "haunted", "creepy", "dark"]):
            return "Horror & Mystery"
        elif any(w in text for w in ["asmr", "cooking", "food", "recipe", "satisfying", "relaxing", "mukbang", "planter", "diy"]):
            return "ASMR & DIY Cooking"
        elif any(w in text for w in ["sci-fi", "future", "futuristic", "robot", "cyberpunk", "space", "alien", "tech", "ai"]):
            return "Tech & Futuristic"
        elif any(w in text for w in ["pov", "storytelling", "documentary", "history", "unbelievable", "facts", "explainer", "cinematic"]):
            return "Storytelling & POV"
        return "Trending Viral"

    def load_all_prompts(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Loads and parses all .html prompt files from the directory."""
        if self._cached_prompts and not force_refresh:
            return self._cached_prompts

        prompts = []
        if os.path.exists(self.prompts_dir):
            for entry in sorted(os.listdir(self.prompts_dir)):
                if entry.lower().endswith(".html") or entry.lower().endswith(".htm"):
                    full_path = os.path.join(self.prompts_dir, entry)
                    data = self.parse_file(full_path)
                    if data and data.get("content"):
                        prompts.append(data)

        self._cached_prompts = prompts
        logger.info(f"Loaded {len(prompts)} viral prompts from {self.prompts_dir}", category="PROMPTS")
        return prompts

    def search_prompts(self, query: str = "", category: str = "All Categories") -> List[Dict[str, Any]]:
        """Searches loaded viral prompts by keyword and category."""
        all_p = self.load_all_prompts()
        query = query.strip().lower()

        filtered = []
        for p in all_p:
            if category != "All Categories" and p["category"] != category:
                continue
            if query:
                if query not in p["title"].lower() and query not in p["content"].lower() and query not in p["category"].lower():
                    continue
            filtered.append(p)

        return filtered

    def get_categories(self) -> List[str]:
        """Returns unique categories sorted alphabetically."""
        all_p = self.load_all_prompts()
        cats = set(p["category"] for p in all_p)
        return ["All Categories"] + sorted(list(cats))

    def add_to_my_prompts(self, prompt: Dict[str, Any]) -> bool:
        """Saves a viral prompt into the user's primary SQLite prompt database."""
        try:
            from app.managers.prompt_manager import PromptManager
            title = prompt.get("title", "Viral Prompt")
            content = prompt.get("content", "").strip()
            if not content:
                return False
            added, _ = PromptManager.save_prompts([content], deduct_duplicates=True)
            logger.info(f"Successfully saved viral prompt '{title}' to user SQLite database", category="PROMPTS")
            return True
        except Exception as e:
            logger.error(f"Error adding viral prompt to user database: {e}", category="PROMPTS")
            return False

# Global Singleton Instance
viral_prompt_manager = ViralPromptManager()
