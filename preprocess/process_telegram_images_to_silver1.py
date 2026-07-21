import os
from pathlib import Path
import duckdb
from tqdm import tqdm

from paddleocr import PaddleOCR
import easyocr


# -------------------------
# Resolve project paths (CRITICAL)
# -------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "telegram.duckdb"

print("[i] Using DuckDB at:", DB_PATH)


# -------------------------
# OCR INITIALIZATION
# -------------------------
def _init_paddle_ocr():
    for opts in [
        {"use_textline_orientation": True, "lang": "en"},
        {"use_angle_cls": True, "lang": "en"},
        {"lang": "en"},
    ]:
        try:
            return PaddleOCR(**opts)
        except Exception:
            continue
    raise RuntimeError("Failed to initialize PaddleOCR")


print("[*] Initializing OCR engines...")
paddle_ocr = _init_paddle_ocr()
easy_ocr = easyocr.Reader(["en"], gpu=False)


def ocr_with_both_engines(image_path: str) -> str:
    texts = []

    try:
        result = paddle_ocr.ocr(image_path, cls=True)
        if result and isinstance(result[0], list):
            for line in result[0]:
                texts.append(line[1][0])
    except Exception:
        pass

    try:
        texts.extend(
            easy_ocr.readtext(image_path, detail=0, paragraph=False)
        )
    except Exception:
        pass

    return " | ".join(t.upper() for t in texts if t.strip())


# -------------------------
# Connect DB
# -------------------------
con = duckdb.connect(DB_PATH)


bronze_count = con.execute("SELECT COUNT(*) FROM telegram_bronze").fetchone()[0]
silver_count = con.execute("SELECT COUNT(*) FROM telegram_silver").fetchone()[0]

print(f"[i] Bronze rows: {bronze_count}")
print(f"[i] Silver rows: {silver_count}")

# -------------------------
# Fetch only NEW rows
# -------------------------
rows = con.execute("""
SELECT
    b.channel,
    b.message_id,
    b.message_ts,
    b.raw_text,
    b.image_path
FROM telegram_bronze b
LEFT JOIN telegram_silver s
  ON b.channel = s.channel
 AND b.message_id = s.message_id
WHERE s.message_id IS NULL
ORDER BY b.message_ts
""").fetchall()

print(f"[*] New rows to process into Silver: {len(rows)}")

if not rows:
    print("[✓] Nothing to process. Silver is up to date.")
    con.close()
    exit(0)


insert_sql = """
INSERT OR IGNORE INTO telegram_silver VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?
)
"""

for channel, message_id, message_ts, raw_text, image_path in tqdm(rows):

    ocr_text = ""
    has_image = False

    if image_path and os.path.exists(image_path):
        has_image = True
        ocr_text = ocr_with_both_engines(image_path)

    clean_text = (raw_text or "").strip()

    merged_text = (
        clean_text + "\n\n[IMAGE_TEXT]\n" + ocr_text
        if ocr_text else clean_text
    )

    con.execute(insert_sql, (
        channel,
        message_id,
        message_ts,
        clean_text,
        ocr_text,
        merged_text,
        None,      # detected_coins (later)
        has_image,
    ))

con.close()
print("[✓] Silver OCR processing complete")
