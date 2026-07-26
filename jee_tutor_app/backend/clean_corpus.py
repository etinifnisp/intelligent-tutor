import json
import os
import re
import sys
import unicodedata
import time
from google import genai

REPLACEMENTS = {
    # Syriac math symbols
    "ܼ": "Z",
    "ܮ": "L",
    "݌": "p",
    "ܷ": "U",
    "݆": "j",
    "ܺ": "X",
    "ܻ": "Y",
    "ܩ": "G",
    "ܪ": "H",
    "ܾ": "b",
    "ܯ": "M",
    "݉": "m",
    "ܴ": "R",
    "ݒ": "v",
    "ܭ": "K",
    "ܶ": "T",
    "ܧ": "E",
    "ݔ": "x",
    "ݕ": "y",
    "ܽ": "a",
    "ݐ": "t",
    "ߙ": "alpha",
    "ߚ": "beta",
    "߱": "omega",
    # Oriya numbers / punctuation / math symbols
    "ି": "-",
    "଼": "8",
    "ଵ": "1",
    "ସ": "4",
    "ଽ": "9",
    "ଶ": "2",
    "଴": "0",
    "ଷ": "3",
    "଻": "7",
    "ହ": "5",
    "଺": "6",
    "େ": "e",
    "୓": "O",
    "୵": "w",
    "ୟ": "a",
    "୲": "t",
    "ୣ": "e",
    "୰": "r",
    "ୠ": "b",
    "୳": "u",
    "୬": "n",
    "ା": "a",
    "ଓ": "i",
    "ଔ": "j",
    "ୀ": "=",
    "ୱ": "s",
    "୧": "i",
    # Tamil symbols
    "ொ": "Q",
    "ெ": "M",
    "ி": "V",
    "௙": "f",
    "௢": "o",
    "ௗ": "L",
    "௄": "K",
    "௤": "q",
    "௔": "a",
    "௕": "b",
    "௣": "d",
    "௡": "n",
    "஺": "A",
    "஻": "B",
    "௞": "k",
    "௥": "r",
    "்": "T",
    "௖": "e",
    "ோ": "o",
    "௧": "t",
    "௘": "e",
    "௩": "v",
    "௅": "L",
    "௫": "x",
    "௝": "j",
    "ஶ": "infinity",
    "௬": "y",
    # Telugu symbols
    "గ": "pi",
    "ఢ": "epsilon",
    "బ": "0",
    "ఙ": "eta",
    "మ": "2",
    "భ": "1",
    "య": "A",
    "ర": "r",
    "ఱ": "r",
    "ఛ": "tau",
    "ఉ": "U",
    "ష": "-",
    # Malayalam math symbols
    "൬": "(",
    "൰": ")",
    "൅": "+",
    "െ": "-",
    "ൌ": "=",
    "ൈ": "x",
    "്": "!=",
    "൫": "(",
    "൯": ")",
    "൐": ">",
    "൜": "{",
    "ൠ": "}",
    # Other common math symbols mis-mapped
    "−": "-",
    "–": "-",
    "×": "x"
}

def clean_text(text):
    if not text:
        return text
    # 1. Standardize replacements
    for bad_char, good_char in REPLACEMENTS.items():
        text = text.replace(bad_char, good_char)
    # 2. Normalize unicode (NFKC normalizes italic mathematical characters)
    text = unicodedata.normalize('NFKC', text)
    return text

def has_devanagari(text):
    if not text:
        return False
    # Range of Devanagari script is U+0900 to U+097F
    return any(0x0900 <= ord(c) <= 0x097F for c in text)

def translate_to_english(client, text):
    prompt = f"""
    The following is an Indian IIT-JEE question. It contains Hindi (Devanagari) words or a mix of English and Hindi translation.
    Please rewrite this question to be entirely and cleanly in English.
    Keep the question context, numerical values, choices/options (e.g. A/B/C/D), formulas, and final answer EXACTLY equivalent.
    Only remove the Hindi text by replacing it with its clear English translation or version.
    Do not add any additional commentary, notes, or chat remarks, just output the translated and cleaned English question directly.
    
    Original Text:
    {text}
    
    Cleaned English Text:
    """
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                sleep_time = 35.0
                match = re.search(r"Please retry in (\d+\.?\d*)s", err_str)
                if match:
                    sleep_time = float(match.group(1)) + 1.0
                print(f"Rate limited (429). Sleeping for {sleep_time:.2f} seconds before retry (attempt {attempt+1}/5)...", flush=True)
                time.sleep(sleep_time)
            else:
                print(f"Translation failed with unexpected error: {e}", flush=True)
                return text
    return text

def main():
    path = "jee_corpus.json"
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} questions.", flush=True)
    client = genai.Client()
    
    # Pre-clean non-English math characters for all questions
    pre_cleaned_count = 0
    for q in data:
        raw_text = q.get("raw_text", "")
        cleaned = clean_text(raw_text)
        if cleaned != raw_text:
            q["raw_text"] = cleaned
            pre_cleaned_count += 1
            
    if pre_cleaned_count > 0:
        print(f"Pre-cleaned math characters in {pre_cleaned_count} questions. Saving...", flush=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    # Count Devanagari questions
    devanagari_indices = [i for i, q in enumerate(data) if has_devanagari(q.get("raw_text", ""))]
    total_to_translate = len(devanagari_indices)
    print(f"Found {total_to_translate} questions containing Devanagari text.", flush=True)
    
    for count, idx in enumerate(devanagari_indices):
        q = data[idx]
        print(f"[{count+1}/{total_to_translate}] Translating Q{q.get('question_number')} (Index {idx})...", flush=True)
        
        translated = translate_to_english(client, q["raw_text"])
        cleaned_translated = clean_text(translated)
        
        # Update and save immediately
        q["raw_text"] = cleaned_translated
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Saved Q{q.get('question_number')}. Remaining: {total_to_translate - (count + 1)}", flush=True)
        time.sleep(2.0)
        
    print("All translations and cleanups completed successfully!", flush=True)

if __name__ == "__main__":
    main()
