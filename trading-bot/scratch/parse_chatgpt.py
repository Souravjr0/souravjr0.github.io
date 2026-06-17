import json
from pathlib import Path

dir_path = Path(r"C:\Users\Sourav Biswas\.gemini\antigravity\brain\840fc9ae-9188-48c6-80eb-9c8d923f795f\.system_generated\steps\508")
enqueue_file = dir_path / "enqueue_0.json"

try:
    data = json.loads(enqueue_file.read_text(encoding='utf-8'))
    
    extracted_strings = []
    
    def extract_strings_recursive(obj):
        if isinstance(obj, str):
            extracted_strings.append(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                extract_strings_recursive(k)
                extract_strings_recursive(v)
        elif isinstance(obj, list):
            for item in obj:
                extract_strings_recursive(item)

    extract_strings_recursive(data)
    print(f"Extracted {len(extracted_strings)} total raw strings.")
    
    # Filter and decode
    unique_messages = []
    for s in extracted_strings:
        try:
            # Decode escapes if any
            s = bytes(s, "utf-8").decode("unicode_escape")
        except Exception:
            pass
        
        s_clean = s.strip()
        # Keep strings that are longer than 25 characters, contain spaces/newlines, or relevant keywords
        if len(s_clean) > 25 and (" " in s_clean or "\n" in s_clean or "indicator" in s_clean.lower() or "bot" in s_clean.lower()):
            if s_clean not in unique_messages:
                unique_messages.append(s_clean)
                
    print(f"Filtered to {len(unique_messages)} unique candidate messages.")
    
    clean_out = dir_path / "extracted_chat_messages.md"
    with open(clean_out, "w", encoding="utf-8") as f:
        f.write("# Extracted Chat Messages from ChatGPT Share Link\n\n")
        for i, msg in enumerate(unique_messages):
            f.write(f"### Message Segment {i+1}\n")
            f.write(f"{msg}\n\n---\n\n")
            
    print(f"Saved extracted messages to {clean_out}")

except Exception as e:
    print("General error:", e)

