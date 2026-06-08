import os
import json
import urllib.request
import urllib.error
import sqlglot
from datetime import datetime

# Resolve paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_JSONL_PATH = os.path.normpath(os.path.join(BASE_DIR, "../../data/splits/test.jsonl"))
API_URL = "http://127.0.0.1:8000"

def send_post_request(endpoint: str, payload: dict) -> tuple:
    """Send POST request to local FastAPI server."""
    url = f"{API_URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode('utf-8'))
        except Exception:
            err_body = {"detail": e.reason}
        return e.code, err_body
    except urllib.error.URLError as e:
        return 500, {"detail": f"Failed to connect to server: {str(e)}"}

def compare_ast(gen_sql: str, gold_sql: str) -> bool:
    """Compare generated SQL with gold SQL using AST-based sqlglot comparison."""
    if not gen_sql or not gold_sql:
        return False
    try:
        ast_gen = sqlglot.parse_one(gen_sql, read="postgres")
        ast_gold = sqlglot.parse_one(gold_sql, read="postgres")
        return ast_gen == ast_gold
    except Exception:
        # Fallback to normalized comparison
        def norm(s):
            import re
            s = s.lower().strip()
            s = re.sub(r'\s+', ' ', s)
            while s.endswith(";"):
                s = s[:-1].strip()
            return s
        return norm(gen_sql) == norm(gold_sql)

def run_test_split_evaluation():
    print("=" * 75)
    # Translation: "🚀 RUNNING HELD-OUT TEST DATASET EVALUATION (70/15/15 SPLIT)"
    print("🚀 RUNNING HELD-OUT TEST DATASET EVALUATION (70/15/15 SPLIT)")
    print("=" * 75)

    if not os.path.exists(TEST_JSONL_PATH):
        print(f"❌ Test dataset file not found at: {TEST_JSONL_PATH}")
        print("💡 Please make sure you have run split_dataset.py first.")
        return

    # Load test dataset
    test_cases = []
    with open(TEST_JSONL_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                test_cases.append(json.loads(line))

    total_cases = len(test_cases)
    print(f"📋 Loaded {total_cases} test cases from test.jsonl")

    esm_passed = 0
    ex_passed = 0
    detailed_results = []

    for index, case in enumerate(test_cases, 1):
        instruction = case.get("instruction", "")
        context = case.get("context", "")
        gold_sql = case.get("response", "")

        print(f"\n[Case {index}/{total_cases}] Query: \"{instruction}\"")
        
        # Step 1: Generate SQL via API
        gen_status, gen_resp = send_post_request("/api/generate-sql", {
            "instruction": instruction,
            "schema_context": context,
            "bypass_cache": True
        })

        if gen_status != 200:
            print(f"   ❌ Generation Failed (HTTP {gen_status}): {gen_resp.get('detail')}")
            detailed_results.append({
                "index": index,
                "instruction": instruction,
                "context": context,
                "gold_sql": gold_sql,
                "generated_sql": "",
                "esm": False,
                "ex": False,
                "error": gen_resp.get("detail")
            })
            continue

        generated_sql = gen_resp.get("sql", "")
        print(f"   Generated SQL: {generated_sql}")
        print(f"   Gold SQL     : {gold_sql}")

        # Step 2: Exact Set Match (ESM) check
        is_esm = compare_ast(generated_sql, gold_sql)
        if is_esm:
            esm_passed += 1
            print("   🎯 ESM: MATCH")
        else:
            print("   ⚠️ ESM: MISMATCH")

        # Step 3: Execution Accuracy (EX) check
        exec_status, exec_resp = send_post_request("/api/execute-sql", {"sql": generated_sql})
        is_ex = False
        if exec_status == 200:
            is_ex = True
            ex_passed += 1
            rows = exec_resp.get("rows_count", 0)
            print(f"   🎉 EX: SUCCESS (Rows: {rows})")
        else:
            print(f"   ❌ EX: FAILED ({exec_resp.get('detail')})")

        detailed_results.append({
            "index": index,
            "instruction": instruction,
            "context": context,
            "gold_sql": gold_sql,
            "generated_sql": generated_sql,
            "esm": is_esm,
            "ex": is_ex,
            "rows": exec_resp.get("rows_count", 0) if is_ex else 0,
            "error": None if is_ex else exec_resp.get("detail")
        })

    # Print summary
    esm_accuracy = (esm_passed / total_cases) * 100 if total_cases > 0 else 0
    ex_accuracy = (ex_passed / total_cases) * 100 if total_cases > 0 else 0

    print("\n" + "=" * 75)
    print("🏁 EVALUATION SUMMARY ON HELDOUT TEST SPLIT (test.jsonl)")
    print("=" * 75)
    print(f"📊 Total Test Cases        : {total_cases}")
    print(f"🎯 Exact Set Match (ESM)   : {esm_passed}/{total_cases} ({esm_accuracy:.2f}%)")
    print(f"✅ Execution Accuracy (EX) : {ex_passed}/{total_cases} ({ex_accuracy:.2f}%)")
    print("=" * 75)

    # Save results to responses directory
    try:
        responses_dir = os.path.normpath(os.path.join(BASE_DIR, "../../responses"))
        os.makedirs(responses_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(responses_dir, f"test_split_evaluation_{timestamp}.json")
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_cases": total_cases,
                "esm_passed": esm_passed,
                "esm_accuracy": esm_accuracy,
                "ex_passed": ex_passed,
                "ex_accuracy": ex_accuracy
            },
            "results": detailed_results
        }
        
        with open(report_path, 'w', encoding='utf-8') as rf:
            json.dump(report_data, rf, indent=2)
            
        print(f"\n📂 Saved detailed evaluation report to:\n👉 {report_path}")
    except Exception as e:
        print(f"❌ Failed to save report file: {str(e)}")

if __name__ == "__main__":
    run_test_split_evaluation()
