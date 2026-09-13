import sqlite3
conn = sqlite3.connect("civic_services.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS complaints (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, category TEXT, priority TEXT, location TEXT, status TEXT, citizen_name TEXT)""")
dummy = [("Water pipe burst on Main Blvd", "Main water pipeline burst creating heavy flooding across street", "Water", "High", "Qasimabad, Hyderabad", "Pending", "Usama Arain"), ("Pani ki nali toot gayi", "Gali mein bohat paani aa raha hai, nali band hai", "Drainage", "High", "Latifabad, Hyderabad", "In Progress", "Ali Khan"), ("Garbage dumping near market", "Overflowing waste bin creating foul smell in residential market", "Waste", "Medium", "Clifton, Karachi", "Resolved", "Ahmed Raza"), ("Active electrical wire sparking", "Explosion risk near live electrical transformer on pole", "Electricity", "Critical", "Gulshan-e-Iqbal, Karachi", "Pending", "Bilal Ahmed"), ("Large pothole on highway", "Damaged road surface causing severe traffic congestion", "Road", "Medium", "Hyderabad Bypass", "In Progress", "Kamran Akmal")]
cursor.executemany("INSERT INTO complaints (title, description, category, priority, location, status, citizen_name) VALUES (?, ?, ?, ?, ?, ?, ?)", dummy)
conn.commit()
conn.close()
print("Success! Dummy complaints added.")