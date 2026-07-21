import re
import emoji
from unidecode import unidecode


# -------------------------
# Emoji Normalization Map
# -------------------------
EMOJI_MAP = {
    "🚀": " rocket ",
    "💎": " diamond ",
    "🙌": " hands ",
    "💎🙌": " diamond hands ",
    "🐸": " frog ",
    "🐕": " dog ",
    "🐶": " dog ",
    "📈": " chart up ",
    "🔥": " fire ",
    "🤑": " money ",
    "🟢": " green ",
    "🔴": " red ",
    "🌙": " moon ",
    "🌕": " moon ",
    "📉": " chart down "
}


# -------------------------
# Regex Patterns
# -------------------------
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
MULTISPACE_PATTERN = re.compile(r"\s+")

# P E P E → PEPE
SPACED_TICKER_PATTERN = re.compile(
    r"\b([A-Z])(?:\s|_|\.){1,3}([A-Z])(?:\s|_|\.){1,3}([A-Z]+)\b"
)

# ZECUSDT → ZEC USDT (CRYPTO-SAFE)
PAIR_JOINED_PATTERN = re.compile(
    r"\b([A-Z]{2,10})(USDT|USD|BTC|ETH|BNB)\b"
)


# -------------------------
# Core Normalization
# -------------------------
def normalize_text(text: str) -> str:
    """
    Crypto-aware normalization:
    - Unicode normalization
    - Emoji → words
    - Remove URLs
    - Fix spaced tickers (P E P E → PEPE)
    - Split joined trading pairs (ZECUSDT → ZEC USDT)
    - Lowercase + whitespace cleanup
    """

    if not isinstance(text, str):
        text = str(text)

    # 1️ Unicode normalization (ＰＥＰＥ → PEPE)
    text = unidecode(text)

    # 2️ Emoji replacement (explicit crypto emojis)
    for emj, replacement in EMOJI_MAP.items():
        text = text.replace(emj, replacement)

    # 3️ Convert remaining emojis to text
    text = emoji.demojize(text, delimiters=(" ", " "))

    # 4️ Remove URLs
    text = URL_PATTERN.sub(" ", text)

    # 5️ Fix spaced / obfuscated tickers
    def _merge_spaced(match):
        return "".join(match.groups())

    text = SPACED_TICKER_PATTERN.sub(_merge_spaced, text.upper())

    # 6️  Split joined trading pairs (ONLY known quotes)
    # Example: ZECUSDT → ZEC USDT
    text = PAIR_JOINED_PATTERN.sub(r"\1 \2", text)

    # 7️ Normalize case and whitespace
    text = text.lower()
    text = MULTISPACE_PATTERN.sub(" ", text).strip()

    return text
