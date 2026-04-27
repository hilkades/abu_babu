from __future__ import annotations

from pathlib import Path
import re


class BadwordsStore:
    _path = Path(__file__).resolve().parents[2] / "badwords.txt"

    @classmethod
    def load_set(cls) -> set[str]:
        if not cls._path.exists():
            cls._path.write_text("", encoding="utf-8")
            return set()
        words: set[str] = set()
        for line in cls._path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            words.add(raw.casefold())
        return words

    @classmethod
    def split_rules(cls, words: set[str] | None = None) -> tuple[set[str], list[str]]:
        source = words if words is not None else cls.load_set()
        literals: set[str] = set()
        regexes: list[str] = []
        for raw in source:
            rule = str(raw).strip()
            if not rule:
                continue
            if cls._looks_like_regex(rule):
                if not cls._is_unsafe_regex(rule):
                    regexes.append(rule)
            else:
                normalized = rule.casefold()
                if not cls._is_unsafe_literal(normalized):
                    literals.add(normalized)
        return literals, regexes

    @classmethod
    def add(cls, word: str) -> bool:
        normalized = word.strip().casefold()
        if not normalized:
            return False
        words = cls.load_set()
        if normalized in words:
            return False
        words.add(normalized)
        cls._save(words)
        return True

    @classmethod
    def remove(cls, word: str) -> bool:
        normalized = word.strip().casefold()
        if not normalized:
            return False
        words = cls.load_set()
        if normalized not in words:
            return False
        words.remove(normalized)
        cls._save(words)
        return True

    @classmethod
    def merge(cls, words_to_merge: set[str] | list[str]) -> int:
        normalized = {str(w).strip().casefold() for w in words_to_merge if str(w).strip()}
        if not normalized:
            return 0
        words = cls.load_set()
        before = len(words)
        words |= normalized
        added = len(words) - before
        if added > 0:
            cls._save(words)
        return added

    @classmethod
    def _save(cls, words: set[str]) -> None:
        content = "\n".join(sorted(words))
        if content:
            content += "\n"
        cls._path.write_text(content, encoding="utf-8")

    @staticmethod
    def _looks_like_regex(rule: str) -> bool:
        # Keep plain words as fast substring checks, regex-like rules as patterns.
        if rule == "*":
            return True
        meta = set(r".^$*+?{}[]\|()")
        return any(ch in meta for ch in rule)

    @staticmethod
    def _is_unsafe_regex(rule: str) -> bool:
        # Patterns that match empty string or are universal are too broad for badwords.
        simple_universal = {".*", ".+", ".", "^.*$", "^.+$", r"\w*", r"\w+", r"\s*", r"\S*"}
        compact = rule.replace(" ", "")
        if compact in simple_universal:
            return True
        try:
            if re.search(rule, "", flags=re.IGNORECASE):
                return True
        except re.error:
            # Keep invalid regex as non-dangerous here; caller may handle fallback.
            return False
        return False

    @staticmethod
    def _is_unsafe_literal(rule: str) -> bool:
        # Very short or generic phrases create too many false positives in live chats.
        if len(rule) <= 3:
            return True
        too_generic = {
            "none",
            "бесплатный",
            "очень хороший",
            "работает быстро",
            "без обмана",
            "сотрудничество",
            "новый проект",
            "в команду",
            "без опыта",
            "легально",
            "стабильный доход",
            "подробности в лс",
            "в лс",
            "пишите +",
            "пиши +",
            "дополнительный доход",
            "работа онлайн",
            "удаленка",
            "удаленка",
            "vpn",
            "впн",
            "usd",
            "$",
            r"\$",
            "➕",
            "🔞",
        }
        return rule in too_generic
