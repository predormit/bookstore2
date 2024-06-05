import sqlite3
import pymongo
import pandas as pd

with sqlite3.connect('./fe/data/book_lx.db') as conn:
    books = pd.read_sql('SELECT * FROM book', conn)
    book_records = books.to_dict(orient='records')
    client = pymongo.MongoClient('mongodb://localhost:27017')
    db = client['bookstore']
    book_col = db['book']
    book_col.delete_many({})
    book_col.insert_many(book_records)
    print('book in mongodb\ndatabase: "bookstore"\ncollection:"book"')