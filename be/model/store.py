import logging
import os
import sqlite3 as sqlite
import threading
#import pymongo
#import pymongo.errors
import psycopg2

class Store:
    database: str

    def __init__(self, db_path):
        self.init_tables()

    def init_tables(self):
        try:
            conn = self.get_db_conn()
            cursor = conn.cursor()

            cursor.execute(
                "TRUNCATE TABLE new_order_detail, new_order, archive_order, store, user_store, \"user\" RESTART IDENTITY CASCADE"
            )
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS "user" ('
                'user_id TEXT PRIMARY KEY, password TEXT NOT NULL, '
                'balance BIGINT NOT NULL, token TEXT, terminal TEXT);'
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS user_store("
                "user_id TEXT, store_id TEXT, PRIMARY KEY(user_id, store_id));"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS store( "
                "store_id TEXT, book_id TEXT, book_info TEXT, stock_level INTEGER,"
                " PRIMARY KEY(store_id, book_id))"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS new_order( "
                "order_id TEXT PRIMARY KEY, user_id TEXT, store_id TEXT,total_price BIGINT,state TEXT)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS new_order_detail( "
                "order_id TEXT, book_id TEXT, count INTEGER, price INTEGER,  "
                "PRIMARY KEY(order_id, book_id))"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS archive_order( "
                "order_id TEXT PRIMARY KEY, user_id TEXT, store_id TEXT, state TEXT,total_price BIGINT)"
            )


        except psycopg2.Error as e:
            logging.error(e)
            conn.rollback()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_db_conn(self) -> psycopg2.extensions.connection:
        conn = psycopg2.connect(database="bookstore2", user="postgres", password="password", host="localhost", port="5432")
        return conn


database_instance: Store = None
# global variable for database sync
init_completed_event = threading.Event()


def init_database(db_path):
    global database_instance
    database_instance = Store(db_path)


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()