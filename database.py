import sqlite3

DATABASE_FILE = 'analyser_360.db'
class Database:
    def get_db(self):
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        self.db = conn

    def create_database(self):
        conn = self.db
        cursor = conn.cursor()
        # user_records
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_records (
            user_id VARCHAR(45) PRIMARY KEY,
            user_name TEXT,
            user_password_hash TEXT,
            user_authkey TEXT ,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_email TEXT
        )
        ''')
        # Chats_history
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_chats (
            query_id INTEGER PRIMARY KEY,
            user_id VARCHAR(45),
            sheet_link TEXT,
            query TEXT,
            response TEXT,
            response_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # Sheets_history
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sheets (
            sheet_id TEXT PRIMARY KEY,
            user_id VARCHAR(45),
            sheet_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        return True
        #conn.close()
    def execute_query(self, query, values):
        conn = self.db
        cursor = conn.cursor()
        cursor.execute(query,values)
        conn.commit()
        return True
        #conn.close()

    def query_data(self, query, values):
        conn = self.db
        cursor = conn.cursor()
        cursor.execute(query,values)
        results = cursor.fetchall()
        #conn.close()
        return [dict(row) for row in results]


    def close_connection(self):
        self.db.close()