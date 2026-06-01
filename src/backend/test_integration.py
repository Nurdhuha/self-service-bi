import json
import urllib.request
import urllib.error
import os
from datetime import datetime
import sqlglot

# Import scenarios containing gold standard SQL queries
try:
    from update_scenarios import SCENARIOS
except ImportError:
    # If run from outside src/backend directory
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from update_scenarios import SCENARIOS

# Server URL
BASE_URL = "http://127.0.0.1:8000"

TEST_CASES = SCENARIOS

def send_post_request(endpoint: str, payload: dict) -> tuple:
    """Helper to send POST request using Python's built-in urllib (no external dependencies)."""
    url = f"{BASE_URL}{endpoint}"
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
    if not gen_sql:
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

def run_integration_tests():
    print("="*70)
    print("🚀 STARTING AUTOMATED TEXT-TO-SQL INTEGRATION TESTS (EX & ESM)")
    print("="*70)
    
    passed_count = 0
    failed_count = 0
    esm_passed_count = 0
    esm_failed_count = 0
    detailed_results = []
    
    for case in TEST_CASES:
        print(f"\n📋 Test Case {case['id']}: {case['name']}")
        print(f"👉 Prompt: \"{case['instruction']}\"")
        
        result_log = {
            "test_case_id": case["id"],
            "name": case["name"],
            "instruction": case["instruction"],
            "status": "failed",
            "esm_status": "failed",
            "generated_sql": "",
            "gold_sql": case.get("sql", ""),
            "error_detail": "",
            "columns_returned": [],
            "rows_retrieved": 0
        }
        
        # Step 1: Generate SQL
        print("⏳ Step 1: Generating SQL query...")
        gen_status, gen_resp = send_post_request("/api/generate-sql", {"instruction": case["instruction"]})
        
        if gen_status != 200:
            err_msg = f"SQL Generation Failed (HTTP {gen_status}): {gen_resp.get('detail')}"
            print(f"❌ {err_msg}")
            result_log["error_detail"] = err_msg
            detailed_results.append(result_log)
            failed_count += 1
            esm_failed_count += 1
            continue
            
        generated_sql = gen_resp.get("sql", "")
        print(f"✅ Generated SQL: {generated_sql}")
        result_log["generated_sql"] = generated_sql
        
        # Step 1.5: Exact Set Match (ESM) comparison
        gold_sql = case.get("sql", "")
        esm_passed = compare_ast(generated_sql, gold_sql)
        if esm_passed:
            print(f"🎯 ESM Match: Generated SQL matches gold standard AST!")
            result_log["esm_status"] = "passed"
            esm_passed_count += 1
        else:
            print(f"⚠️ ESM Mismatch: AST differs from gold standard SQL.")
            print(f"   👉 Gold SQL: {gold_sql}")
            result_log["esm_status"] = "failed"
            esm_failed_count += 1
        
        # Step 2: Execute SQL against Database
        print("⏳ Step 2: Executing generated SQL in database...")
        exec_status, exec_resp = send_post_request("/api/execute-sql", {"sql": generated_sql})
        
        if exec_status != 200:
            err_msg = f"SQL Database Execution Failed (HTTP {exec_status}): {exec_resp.get('detail')}"
            print(f"❌ {err_msg}")
            result_log["error_detail"] = err_msg
            detailed_results.append(result_log)
            failed_count += 1
            continue
            
        columns = exec_resp.get("columns", [])
        rows_count = exec_resp.get("rows_count", 0)
        print(f"✅ Database execution succeeded! Columns returned: {columns}")
        print(f"🎉 Rows retrieved: {rows_count}")
        
        result_log["status"] = "passed"
        result_log["columns_returned"] = columns
        result_log["rows_retrieved"] = rows_count
        detailed_results.append(result_log)
        
        passed_count += 1
        
    print("\n" + "="*70)
    print("🏁 INTEGRATION TEST RUN SUMMARY")
    print("="*70)
    print(f"✅ Total Execution (EX) Passed  : {passed_count}/{len(TEST_CASES)} ({passed_count/len(TEST_CASES)*100:.1f}%)")
    print(f"❌ Total Execution (EX) Failed  : {failed_count}/{len(TEST_CASES)} ({failed_count/len(TEST_CASES)*100:.1f}%)")
    print(f"🎯 Total Exact Set Match (ESM) Passed: {esm_passed_count}/{len(TEST_CASES)} ({esm_passed_count/len(TEST_CASES)*100:.1f}%)")
    print(f"⚠️ Total Exact Set Match (ESM) Failed: {esm_failed_count}/{len(TEST_CASES)} ({esm_failed_count/len(TEST_CASES)*100:.1f}%)")
    print("="*70)
    
    # Save the testing results summary to the responses folder
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(backend_dir))
        responses_dir = os.path.join(project_root, "responses")
        
        # Make sure responses folder exists
        os.makedirs(responses_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_run_summary_{timestamp}.json"
        filepath = os.path.join(responses_dir, filename)
        
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(TEST_CASES),
                "passed": passed_count,
                "failed": failed_count,
                "esm_passed": esm_passed_count,
                "esm_failed": esm_failed_count
            },
            "results": detailed_results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
            
        print(f"\n📂 Test run summary successfully saved to:")
        print(f"👉 {filepath}")
        
    except Exception as save_err:
        print(f"❌ Failed to save test results summary file: {str(save_err)}")

if __name__ == "__main__":
    run_integration_tests()
