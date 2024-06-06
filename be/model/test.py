import os
import sqlite3 as sqlite


Use_Large_DB = 1
page = 1
search_key = "三毛"
grandparent_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_s = os.path.join(grandparent_path, "fe/data/book.db")
db_l = os.path.join(grandparent_path, "fe/data/book_lx.db")
if Use_Large_DB:
    book_db = db_l
else:
    book_db = db_s
conn = sqlite.connect(book_db)

if page > 0:
    page_size = 10
    page_prev = page_size * (page-1)
    cursor = conn.execute(
        "SELECT id, title, author FROM book WHERE title LIKE ? OR author LIKE ? OR publisher LIKE ? OR tags LIKE ? OR content LIKE ? LIMIT ? OFFSET ?",
        ('%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%',
            '%' + search_key + '%', page_size, page_prev),
            )
else:
    cursor = conn.execute(
        "SELECT id, title, author FROM book WHERE title LIKE ? OR author LIKE ? OR publisher LIKE ? OR tags LIKE ? OR content LIKE ?",
        ('%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%',
            '%' + search_key + '%'),
            )

rows = cursor.fetchall()
result = []
for row in rows:
    book = {
        "id": row[0],
        "title": row[1],
        "author": row[2]
    }
    result.append(book)
print(result)