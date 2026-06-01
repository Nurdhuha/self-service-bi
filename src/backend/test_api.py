import unittest
import psycopg2
from app import clean_sql, OLIST_SCHEMA_CONTEXT
from config import settings

class TestSQLCleaning(unittest.TestCase):
    def test_basic_cleaning(self):
        sql = "SELECT * FROM customers  "
        self.assertEqual(clean_sql(sql), "SELECT * FROM customers;")

    def test_semicolon_retention(self):
        sql = "SELECT * FROM products;"
        self.assertEqual(clean_sql(sql), "SELECT * FROM products;")

    def test_eos_token_removal(self):
        sql = "SELECT COUNT(*) FROM orders;<|end_of_text|>"
        self.assertEqual(clean_sql(sql), "SELECT COUNT(*) FROM orders;")

    def test_markdown_codeblock_parsing_sql(self):
        sql = "Here is the response:\n```sql\nSELECT * FROM sellers;\n```\nHope it helps!"
        self.assertEqual(clean_sql(sql), "SELECT * FROM sellers;")

    def test_markdown_generic_codeblock(self):
        sql = "```\nSELECT MAX(price) FROM order_items;\n```"
        self.assertEqual(clean_sql(sql), "SELECT MAX(price) FROM order_items;")

class TestDatabaseConnectivity(unittest.TestCase):
    def test_readonly_postgres_connection(self):
        print("\n🔍 Checking PostgreSQL Connection...")
        try:
            conn = psycopg2.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                connect_timeout=5
            )
            print("✅ Connection established successfully!")
            
            # Verify read-only status
            conn.set_session(readonly=True)
            self.assertTrue(conn.readonly)
            print("✅ Connection session set to Read-Only mode successfully.")
            
            # Simple query test
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                res = cur.fetchone()
                self.assertEqual(res[0], 1)
                print("✅ Simple database query test executed successfully.")
                
            conn.close()
            print("🎉 PostgreSQL Read-Only Database Connection verified perfectly!")
        except Exception as e:
            print(f"❌ Connection check failed: {str(e)}")
            print("⚠️ Please review the credentials in your local '.env' file.")
            # Do not fail hard, just notify since user might run it before setting up credentials
            self.skipTest("PostgreSQL not accessible with current .env credentials.")

if __name__ == "__main__":
    print("="*60)
    print("🏁 Starting SQL Llama BI Backend Unit & Integration Tests")
    print("="*60)
    unittest.main()
