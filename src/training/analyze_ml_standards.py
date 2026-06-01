import os
import json
import re
import collections

DATASET_PATH = "../../data/processed/dataset_latih.jsonl"
RESPONSES_DIR = "../../responses"

def analyze_table_frequencies(dataset_abs: str):
    print("="*65)
    print("📊 PILAR 1: TRAINING DATA TABLE FREQUENCY ANALYSIS")
    print("="*65)
    
    if not os.path.exists(dataset_abs):
        print(f"❌ Training dataset not found at: {dataset_abs}")
        return
        
    frequencies = collections.Counter()
    total_samples = 0
    
    with open(dataset_abs, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                total_samples += 1
                data = json.loads(line)
                context = data.get("context", "").lower()
                # Find all table references in context string, e.g. "Table customers (col)"
                tables = re.findall(r'table\s+(\w+)', context)
                for t in tables:
                    frequencies[t] += 1
                    
    if not frequencies:
        print("⚠️ No table declarations found in prompt context strings.")
        return
        
    total_refs = sum(frequencies.values())
    print(f"Total Training Samples Analyzed: {total_samples}")
    print(f"Total Table Context References  : {total_refs}\n")
    print(f"{'Table Name':<18} | {'Occurrences':<12} | {'Representation %':<16}")
    print("-"*65)
    
    for table, count in frequencies.most_common():
        percentage = (count / total_samples) * 100
        # Color code warnings for under-represented tables (< 10%)
        warn_status = "⚠️ LOW" if percentage < 10.0 else "✅ BALANCED"
        print(f"{table:<18} | {count:<12} | {percentage:>5.1f}% ({warn_status})")
        
    print("\n💡 Suggestion: For tables marked 'LOW' (< 10% representation), generate 30-50 new, complex training samples to prevent structural overfitting.")

def classify_query_complexity(sql_str: str) -> str:
    """Classify SQL complexity based on join depths, aggregations, and subquery structures."""
    sql_lower = sql_str.lower()
    join_count = sql_lower.count("join")
    subquery_count = sql_lower.count("select") - 1
    
    if subquery_count > 0 or "union" in sql_lower or "except" in sql_lower or "intersect" in sql_lower:
        return "Extra Hard"
    elif join_count >= 2 or "extract(" in sql_lower or "date" in sql_lower or "like" in sql_lower:
        return "Hard"
    elif join_count == 1 or "group by" in sql_lower or "avg(" in sql_lower or "sum(" in sql_lower:
        return "Medium"
    else:
        return "Easy"

def run_complexity_slicing(responses_dir_abs: str):
    print("\n" + "="*75)
    print("🎯 PILAR 2: TEST RUN COMPLEXITY SLICING & ACCURACY (EX & ESM)")
    print("="*75)
    
    if not os.path.exists(responses_dir_abs):
        print(f"❌ Responses directory not found at: {responses_dir_abs}")
        return
        
    # Find the latest test run summary JSON file
    summary_files = [f for f in os.listdir(responses_dir_abs) if f.startswith("test_run_summary_") and f.endswith(".json")]
    if not summary_files:
        print("⚠️ No test run summary JSON files found in responses directory.")
        return
        
    # Sort by timestamp in filename
    summary_files.sort(reverse=True)
    latest_file = os.path.join(responses_dir_abs, summary_files[0])
    print(f"📂 Analyzing Latest Test Summary: {os.path.basename(latest_file)}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        summary_data = json.load(f)
        
    results = summary_data.get("results", [])
    if not results:
        print("⚠️ No test case results found in the summary file.")
        return
        
    # Metrics by complexity slice
    slice_metrics = {
        "Easy": {"total": 0, "passed": 0, "esm_passed": 0},
        "Medium": {"total": 0, "passed": 0, "esm_passed": 0},
        "Hard": {"total": 0, "passed": 0, "esm_passed": 0},
        "Extra Hard": {"total": 0, "passed": 0, "esm_passed": 0}
    }
    
    for r in results:
        sql = r.get("generated_sql", "")
        status = r.get("status", "failed")
        esm_status = r.get("esm_status", "failed")
        
        comp = classify_query_complexity(sql)
        slice_metrics[comp]["total"] += 1
        if status == "passed":
            slice_metrics[comp]["passed"] += 1
        if esm_status == "passed":
            slice_metrics[comp]["esm_passed"] += 1
            
    print(f"\n{'Complexity Slice':<16} | {'Total':<6} | {'EX Passed':<10} | {'EX Acc':<8} | {'ESM Passed':<10} | {'ESM Acc':<8}")
    print("-"*75)
    
    for comp, metrics in slice_metrics.items():
        total = metrics["total"]
        passed = metrics["passed"]
        esm_passed = metrics["esm_passed"]
        accuracy = (passed / total * 100) if total > 0 else 0.0
        esm_accuracy = (esm_passed / total * 100) if total > 0 else 0.0
        acc_str = f"{accuracy:>5.1f}%" if total > 0 else "N/A"
        esm_acc_str = f"{esm_accuracy:>5.1f}%" if total > 0 else "N/A"
        
        print(f"{comp:<16} | {total:<6} | {passed:<10} | {acc_str:<8} | {esm_passed:<10} | {esm_acc_str:<8}")
        
    print("\n💡 Suggestion: Monitor accuracy drops in 'Hard' and 'Extra Hard' slices during future epochs to diagnose model reasoning boundaries.")
    print("="*75)

if __name__ == "__main__":
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_abs = os.path.normpath(os.path.join(backend_dir, DATASET_PATH))
    responses_dir_abs = os.path.normpath(os.path.join(backend_dir, RESPONSES_DIR))
    
    analyze_table_frequencies(dataset_abs)
    run_complexity_slicing(responses_dir_abs)

