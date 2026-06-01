import unittest
import sqlglot
import sys
import os

# Ensure the backend directory is in the path so we can import modules
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from update_scenarios import SCENARIOS

class TestScenarioOfflineAudit(unittest.TestCase):
    def test_scenarios_count(self):
        """Ensure exactly 120 distinct business scenarios are defined."""
        self.assertEqual(len(SCENARIOS), 120, f"Dataset must contain exactly 120 scenarios. Currently: {len(SCENARIOS)}")

    def test_unique_scenario_attributes(self):
        """Ensure no duplicates in IDs, names, or instructions."""
        ids = [s["id"] for s in SCENARIOS]
        names = [s["name"] for s in SCENARIOS]
        instructions = [s["instruction"].strip().lower() for s in SCENARIOS]

        self.assertEqual(len(set(ids)), 120, "Scenario IDs must be unique.")
        self.assertEqual(len(set(names)), 120, "Scenario names must be unique.")
        self.assertEqual(len(set(instructions)), 120, "Scenario instructions must be unique.")

    def test_sql_syntax_validity(self):
        """Ensure all gold standard SQL queries parse successfully without syntax errors."""
        for s in SCENARIOS:
            sql = s.get("sql", "")
            self.assertTrue(len(sql) > 0, f"Scenario {s['id']} has empty SQL query.")
            try:
                # Parse using postgres dialect
                parsed = list(sqlglot.parse(sql, read="postgres"))
                self.assertTrue(len(parsed) > 0, f"Scenario {s['id']} parsed to empty statement.")
            except Exception as e:
                self.fail(f"Scenario {s['id']} SQL syntax error: {str(e)}\nSQL: {sql}")

    def test_ast_safety_shield(self):
        """Ensure all 120 gold standard queries successfully pass the AST SQL Security Shield."""
        for s in SCENARIOS:
            sql = s.get("sql", "").strip()
            try:
                parsed_statements = sqlglot.parse(sql, read="postgres")
                is_safe = True
                
                for statement in parsed_statements:
                    if statement is None:
                        continue
                    for node in statement.walk():
                        if isinstance(node, (
                            sqlglot.exp.Drop,
                            sqlglot.exp.Delete,
                            sqlglot.exp.Update,
                            sqlglot.exp.Insert,
                            sqlglot.exp.Alter,
                            sqlglot.exp.Create,
                            sqlglot.exp.TruncateTable
                        )):
                            is_safe = False
                            break
                    if not is_safe:
                        break
                
                self.assertTrue(is_safe, f"Scenario {s['id']} was flagged as unsafe by the AST Safety Shield! SQL: {sql}")
            except Exception as e:
                self.fail(f"Scenario {s['id']} encountered parsing error under safety shield: {str(e)}")

    def test_unsafe_queries_are_blocked(self):
        """Ensure malicious or destructive queries are successfully blocked by the AST Safety Shield logic."""
        malicious_queries = [
            "DROP TABLE olist_orders_dataset;",
            "SELECT * FROM olist_orders_dataset; DELETE FROM customers;",
            "INSERT INTO products (product_id) VALUES ('fake');",
            "UPDATE order_items SET price = 0.0;",
            "ALTER TABLE sellers ADD COLUMN hacked TEXT;",
            "TRUNCATE TABLE geolocation;",
            "CREATE TABLE test (id INT);"
        ]
        
        for sql in malicious_queries:
            parsed_statements = sqlglot.parse(sql.strip(), read="postgres")
            is_safe = True
            for statement in parsed_statements:
                if statement is None:
                    continue
                for node in statement.walk():
                    if isinstance(node, (
                        sqlglot.exp.Drop,
                        sqlglot.exp.Delete,
                        sqlglot.exp.Update,
                        sqlglot.exp.Insert,
                        sqlglot.exp.Alter,
                        sqlglot.exp.Create,
                        sqlglot.exp.TruncateTable
                    )):
                        is_safe = False
                        break
                if not is_safe:
                    break
            self.assertFalse(is_safe, f"Unsafe query successfully bypassed the security shield: {sql}")

if __name__ == "__main__":
    unittest.main()
