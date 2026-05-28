import json
import os
import time
import logging
from typing import List, Dict, Any, Set, Tuple
from openai import OpenAI

# CONFIG

INPUT_JSONL = "data/processed/telegram_messages_with_ocr.jsonl"
OUTPUT_JSONL = "data/processed/labeled_messages.jsonl"
BATCH_INPUT = "data/processed/batch_input.jsonl"
BATCH_OUTPUT = "data/processed/batch_output.jsonl"

SYSTEM_PROMPT = """You are an expert financial fraud annotator with 20 years of experience labeling cryptocurrency pump-and-dump schemes on Telegram.

Your task is to classify EACH message into EXACTLY ONE of the following categories:

- hype_signal: Builds excitement, anticipation, or contains urgent coordination/direct trading instructions (e.g., "BUY NOW", countdowns, "let's go").
- coin_reveal: Explicitly discloses the target coin, trading pair, entry zones, targets, or leverage.
- outcome_reflection: Reports results after the event (e.g., profit percentages, recaps, post-pump analysis).
- noise: Anything else — chatter, promotions, empty messages, irrelevant content.

Prioritize: coin_reveal > outcome_reflection > hype_signal > noise.
If ambiguous → noise.

Return ONLY JSON: {"label": "...", "reason": "brief justification (max 100 chars)"}
"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

client = OpenAI()

def load_existing_keys() -> Set[Tuple[str, int]]:
    existing = set()
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    key = (obj.get("channel"), obj.get("message_id"))
                    if None not in key:
                        existing.add(key)
    logger.info(f"Found {len(existing)} already labeled messages")
    return existing

def merge_batch_results_into_labeled():
    """Merge batch results into labeled_messages.jsonl - ENSURES COMPLETE MERGE"""
    
    if not os.path.exists(BATCH_OUTPUT):
        logger.error(f"Batch output file not found: {BATCH_OUTPUT}")
        return False
    
    if not os.path.exists(INPUT_JSONL):
        logger.error(f"Input file not found: {INPUT_JSONL}")
        return False
    
    # Loading existing labeled keys TO avoid duplicates
    existing_keys = load_existing_keys()
    
    # Load batch results
    logger.info(f"Loading batch results from {BATCH_OUTPUT}...")
    id_to_result: Dict[str, Dict] = {}
    with open(BATCH_OUTPUT, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    obj = json.loads(line)
                    custom_id = obj.get("custom_id", "")
                    
                    if obj.get("response", {}).get("body", {}).get("choices"):
                        content = obj["response"]["body"]["choices"][0]["message"]["content"]
                        try:
                            data = json.loads(content)
                            
                            label = data.get("label", "noise")
                            if label == "call_to_action":
                                label = "hype_signal"
                                data["reason"] = f"Merged into hype_signal. Original: {data.get('reason', '')}"
                            
                            id_to_result[custom_id] = {
                                "label": label,
                                "reason": data.get("reason", "")[:150]
                            }
                        except json.JSONDecodeError:
                            id_to_result[custom_id] = {"label": "noise", "reason": "Parse error"}
                    else:
                        id_to_result[custom_id] = {"label": "noise", "reason": "No response"}
                        
                except Exception as e:
                    logger.warning(f"Failed to parse line {line_num}: {e}")
    
    logger.info(f"Loaded {len(id_to_result)} batch results")
    
    # Load original messages
    logger.info(f"Loading original messages from {INPUT_JSONL}")
    channel_msg_to_data: Dict[Tuple[str, int], Dict] = {}
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    msg = json.loads(line)
                    channel = msg.get("channel")
                    msg_id = msg.get("message_id")
                    if channel and msg_id is not None:
                        channel_msg_to_data[(channel, msg_id)] = msg
                except:
                    pass
    
    logger.info(f"Loaded {len(channel_msg_to_data)} original messages")
    
    # Merge results
    appended_count = 0
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as fout:
        for custom_id, result in id_to_result.items():
            try:
                # go through custom_id format "channel_message_id"
                if "_" not in custom_id:
                    continue
                    
                channel, msg_id_str = custom_id.rsplit("_", 1)
                msg_id = int(msg_id_str)
                key = (channel, msg_id)
                
                # Skip if already labeled
                if key in existing_keys:
                    continue
                
                # Getting original message data
                original_msg = channel_msg_to_data.get(key)
                if not original_msg:
                    logger.warning(f"Original message not found for {key}")
                    
                    msg = {
                        "channel": channel,
                        "message_id": msg_id,
                        "label": result["label"],
                        "reason": result["reason"]
                    }
                else:
                    
                    msg = original_msg.copy()
                    msg["label"] = result["label"]
                    msg["reason"] = result["reason"]
                
                # Writing to output
                fout.write(json.dumps(msg, ensure_ascii=False) + "\n")
                existing_keys.add(key)
                appended_count += 1
                
                if appended_count % 100 == 0:
                    logger.info(f"Appended {appended_count} messages...")
                    
            except Exception as e:
                logger.warning(f"Failed to process {custom_id}: {e}")
    
    logger.info(f"✓ Merged {appended_count} new messages into {OUTPUT_JSONL}")
    
    # Final verification
    final_count = len(load_existing_keys())
    logger.info(f"Total labeled messages after merge: {final_count}")
    
    return appended_count > 0

def main():
    e
    logger.info("Loading messages...")
    messages: List[Dict] = []
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))

    # 40% 
    target_n = int(len(messages) * 0.40)
    messages = messages[:target_n]

    existing = load_existing_keys()
    unlabeled = [
        m for m in messages
        if (m.get("channel"), m.get("message_id")) not in existing
        and m.get("message_id") is not None
    ]

    logger.info(f"{len(unlabeled)} unlabeled messages → creating batch")

    if not unlabeled:
        logger.info("All done!")
        return

    # Creating batch input file
    os.makedirs(os.path.dirname(BATCH_INPUT), exist_ok=True)
    with open(BATCH_INPUT, "w", encoding="utf-8") as f:
        for msg in unlabeled:
            text = (msg.get("final_text") or msg.get("text") or "").strip() or "[Empty]"
            custom_id = f"{msg['channel']}_{msg['message_id']}"
            task = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 200,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text}
                    ]
                }
            }
            f.write(json.dumps(task) + "\n")

    # Upload file
    logger.info("Uploading batch file...")
    file_obj = client.files.create(file=open(BATCH_INPUT, "rb"), purpose="batch")

    # Create batch job
    logger.info("Starting batch job...")
    batch_job = client.batches.create(
        input_file_id=file_obj.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    logger.info(f"Batch created: {batch_job.id} — polling for completion...")

    # Poll until done
    while batch_job.status in ["validating", "in_progress", "finalizing"]:
        time.sleep(30)
        batch_job = client.batches.retrieve(batch_job.id)
        logger.info(f"Status: {batch_job.status} — {batch_job.request_counts}")

    if batch_job.status == "completed":
        logger.info("Batch completed!")
        # Download output
        output_file = client.files.content(batch_job.output_file_id)
        with open(BATCH_OUTPUT, "wb") as f:
            f.write(output_file.content)
        
        # Merging ALL results into labeled_messages.jsonl
        logger.info("Merging ALL batch results into labeled_messages.jsonl...")
        merge_batch_results_into_labeled()
        
        logger.info("All done! Clean up batch files if desired.")
        
        # Final statistics
        final_existing = load_existing_keys()
        total_unlabeled_in_sample = len([m for m in messages 
                                        if (m.get("channel"), m.get("message_id")) not in final_existing])
        
        logger.info(f"=== FINAL STATISTICS ===")
        logger.info(f"Total in 40% sample: {len(messages)}")
        logger.info(f"Total labeled: {len(final_existing)}")
        logger.info(f"Remaining unlabeled in sample: {total_unlabeled_in_sample}")
        logger.info(f"Completion rate: {(len(final_existing)/len(messages))*100:.1f}%")
        
    else:
        logger.error(f"Batch failed: {batch_job.status}")

def cleanup_old_call_to_action():
    """Clean up any old call_to_action labels in existing file"""
    if not os.path.exists(OUTPUT_JSONL):
        return
    
    logger.info("Checking for old 'call_to_action' labels...")
    fixed_count = 0
    messages = []
    
    with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                msg = json.loads(line)
                if msg.get("label") == "call_to_action":
                    msg["label"] = "hype_signal"
                    msg["reason"] = f"Merged from call_to_action. Original: {msg.get('reason', '')}"
                    fixed_count += 1
                messages.append(msg)
    
    if fixed_count > 0:
        logger.info(f"Fixed {fixed_count} 'call_to_action' labels")
        # Rewrite file
        with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        logger.info("File cleaned and rewritten")
    else:
        logger.info("No 'call_to_action' labels found")

if __name__ == "__main__":
    # clean up any old call_to_action labels
    cleanup_old_call_to_action()
    
    main()
