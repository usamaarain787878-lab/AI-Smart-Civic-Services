import sqlite3
from collections import Counter

class CivicAnalytics:
    def __init__(self, db_path="database/civic_services.db"):
        self.db_path = db_path

    def get_summary_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT category, priority, status FROM complaints")
            rows = cursor.fetchall()
        except Exception:
            rows = []
        finally:
            conn.close()

        if not rows:
            return {"total": 0, "categories": {}, "priorities": {}, "status": {}}

        categories = Counter([r[0] for r in rows if r[0]])
        priorities = Counter([r[1] for r in rows if r[1]])
        statuses = Counter([r[2] for r in rows if r[2]])

        return {
            "total_complaints": len(rows),
            "category_distribution": dict(categories),
            "priority_distribution": dict(priorities),
            "status_breakdown": dict(statuses)
        }

if __name__ == "__main__":
    analytics = CivicAnalytics()
    print("Analytics Output:", analytics.get_summary_stats())