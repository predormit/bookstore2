import logging
import os
import sqlite3 as sqlite
import threading
import pymongo
import pymongo.errors

class Store:
    database: str

    def __init__(self, db_path):
        self.database = os.path.join(db_path, "be.db")
        self.init_tables()

    def init_tables(self):
        try:
            client = self.get_db_conn()
            db = client['bookstore']
            user = db['user']
            #user.delete_many({})
            user.create_index("user_id")
            user_store = db['user_store']
            #user_store.delete_many({})
            user_store.create_index([('user_id', 1), ('store_id', 1)], unique=True)
            store = db['store']
            #store.delete_many({})
            store.create_index([('store_id', 1), ('book_id', 1)], unique=True)
            new_order = db['new_order']
            #new_order.delete_many({})
            new_order.create_index([('order_id', 1)], unique=True)
            new_order_detail = db['new_order_detail']
            #new_order_detail.delete_many({})
            new_order_detail.create_index([('order_id', 1), ('book_id', 1)], unique=True)

            book = db['book']
            book.create_index("title")
            book.create_index("author")
            book.create_index("pulisher")
            book.create_index("tags")
            book.create_index("content")


        except pymongo.errors.PyMongoError as e:
            logging.error(e)


    def get_db_conn(self) -> pymongo.MongoClient:
        client = pymongo.MongoClient('mongodb://localhost:27017')
        return client


database_instance: Store = None
# global variable for database sync
init_completed_event = threading.Event()


def init_database(db_path):
    global database_instance
    database_instance = Store(db_path)


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()