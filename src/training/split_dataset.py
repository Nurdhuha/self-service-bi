import os
import json
import random

RAW_PATH = "../../data/processed/dataset_latih.jsonl"
OUTPUT_DIR = "../../data/splits"

def split_dataset():
    # 1. Resolve relative paths
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    raw_file_abs = os.path.normpath(os.path.join(backend_dir, RAW_PATH))
    output_dir_abs = os.path.normpath(os.path.join(backend_dir, OUTPUT_DIR))
    
    if not os.path.exists(raw_file_abs):
        print(f"❌ Master dataset file not found at: {raw_file_abs}")
        return
        
    print(f"📂 Loading master dataset from: {raw_file_abs}")
    
    # 2. Load all samples
    records = []
    with open(raw_file_abs, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    total_raw = len(records)
    print(f"🔍 Loaded {total_raw} raw samples.")
    
    # 3. Fuzzy De-duplication based on lowercase, stripped instructions
    unique_records = []
    seen_instructions = set()
    for r in records:
        inst = r["instruction"].strip().lower()
        # Strip simple punctuation to catch near-duplicates
        inst_clean = "".join([c for c in inst if c.isalnum() or c.isspace()])
        if inst_clean not in seen_instructions:
            seen_instructions.add(inst_clean)
            unique_records.append(r)
            
    total_unique = len(unique_records)
    print(f"✨ De-duplication complete: {total_unique} unique samples remaining (removed {total_raw - total_unique} duplicates).")
    
    # 4. Deterministic Shuffling
    # Using a fixed seed ensures reproducibility across runs
    random.seed(42)
    random.shuffle(unique_records)
    
    # 5. Calculate Partition Sizes (70% Train, 15% Val, 15% Test)
    train_size = int(total_unique * 0.70)
    val_size = int(total_unique * 0.15)
    test_size = total_unique - train_size - val_size
    
    train_set = unique_records[:train_size]
    val_set = unique_records[train_size:train_size + val_size]
    test_set = unique_records[train_size + val_size:]
    
    # 6. Save split files
    os.makedirs(output_dir_abs, exist_ok=True)
    
    splits = [
        ("train.jsonl", train_set),
        ("val.jsonl", val_set),
        ("test.jsonl", test_set)
    ]
    
    for filename, dataset in splits:
        filepath = os.path.join(output_dir_abs, filename)
        with open(filepath, 'w', encoding='utf-8') as out_f:
            for item in dataset:
                out_f.write(json.dumps(item) + "\n")
                
    print(f"📊 Dataset successfully partitioned & saved:")
    print(f"   👉 Train Set      : {len(train_set)} records -> {os.path.join(OUTPUT_DIR, 'train.jsonl')}")
    print(f"   👉 Validation Set : {len(val_set)} records -> {os.path.join(OUTPUT_DIR, 'val.jsonl')}")
    print(f"   👉 Test Set       : {len(test_set)} records -> {os.path.join(OUTPUT_DIR, 'test.jsonl')}")

if __name__ == "__main__":
    split_dataset()
