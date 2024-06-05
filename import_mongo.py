import sqlite3
from pymongo import MongoClient
import pandas as pd

conn = sqlite3.connect('./fe/data/book_lx.db')
rows = pd.read_sql('SELECT * FROM book', conn)
book_records = rows.to_dict(orient='records')

client = MongoClient('mongodb://localhost:27017/')
db = client['bookstore']
collections = db['book']
collections.delete_many({})
collections.insert_many(book_records)
print('book in mongodb\ndatabase: "bookstore"\ncollection:"book"')

conn.close()
client.close()