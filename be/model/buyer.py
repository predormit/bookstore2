import uuid
import json
import logging
import os
from be.model import db_conn
from be.model import error
from fe.conf import Use_Large_DB
import psycopg2
import sqlite3 as sqlite
from threading import Timer


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
        self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            order_id = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            #store_col = self.db['store']
            order_details = []
            total_price = 0
            for book_id, count in id_and_count:
                #result_col = store_col.find_one({"store_id": store_id, "book_id": book_id})
                cursor = self.cur.execute(
                    "SELECT book_id, stock_level, book_info FROM store "
                    "WHERE store_id = %s AND book_id = %s;",
                    (store_id, book_id),
                )
                row = self.cur.fetchone()
                if row is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = row[1]
                book_info = json.loads(row[2])
                price = book_info.get("price")
                total_price += price * count

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                self.cur.execute(
                    "UPDATE store SET stock_level = stock_level - %s "
                    "WHERE store_id = %s AND book_id = %s AND stock_level >= %s",
                    (count, store_id, book_id, count),
                )
                if self.cur.rowcount == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)
                order_details.append({
                    "order_id": order_id,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                })

            for detail in order_details:
                self.cur.execute(
                    "INSERT INTO new_order_detail (order_id, book_id, count, price) VALUES (%s, %s, %s, %s);",
                    (detail["order_id"], detail["book_id"], detail["count"], detail["price"])
                )
            self.cur.execute(
                "INSERT INTO new_order (order_id, store_id, user_id, total_price, state) VALUES (%s, %s, %s, %s, %s);",
                (order_id, store_id, user_id, total_price, "Pending")
            )

            self.conn.commit()
        except psycopg2.Error as e:
            logging.info("528, {}".format(str(e)))
            self.conn.rollback()
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""
        
        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> tuple[int, str]:
        cur = self.cur
        try:
            self.cur.execute(
                "SELECT user_id, store_id,total_price FROM new_order WHERE order_id = %s;",
                (order_id,)
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)

            buyer_id = row[0]
            store_id = row[1]
            total_price = row[2]

            if buyer_id != user_id:
                return error.error_authorization_fail()

            self.cur.execute(
                'SELECT balance, password FROM "user" WHERE user_id = %s;',
                (buyer_id,)
            )
            row = self.cur.fetchone()
            #result = db['user'].find_one({"user_id": buyer_id}, {"balance": 1, "password": 1})
            if row is None:
                return error.error_invalid_order_id(order_id)
            balance = row[0]
            if password != row[1]:
                return error.error_authorization_fail()

            self.cur.execute(
                "SELECT user_id FROM user_store WHERE store_id = %s;",
                (store_id,)
            )
            row = self.cur.fetchone()
            #seller_info = db['user_store'].find_one({"store_id": store_id})
            if row is None:
                return error.error_non_exist_store_id(store_id)
            seller_id = row[0]

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)
            #
            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            self.cur.execute(
                'UPDATE "user" SET balance = balance - %s '
                'WHERE user_id = %s AND balance >= %s',
                (total_price, buyer_id, total_price),
            )
            if self.cur.rowcount == 0:
                return error.error_not_sufficient_funds(order_id)
            #
            self.cur.execute(
                'UPDATE "user" SET balance = balance + %s '
                'WHERE user_id = %s',
                (total_price, seller_id),
            )
            if self.cur.rowcount == 0:
                return error.error_non_exist_user_id(seller_id)
            #
            '''
            self.cur.execute(
                'UPDATE "new_order" SET state = "unshipped" '
                'WHERE order_id = %s;',
                (order_id,)
            )
            '''
            self.cur.execute(
                "UPDATE new_order SET state = 'unshipped' WHERE order_id = %s;",
                (order_id,)
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"


    def add_funds(self, user_id, password, add_value) -> tuple[int, str]:
        cur = self.cur
        try:
            cursor = cur.execute(
                'SELECT password FROM "user" WHERE user_id = %s', (user_id,)
            )
            user_password_result = cur.fetchone()
            if user_password_result is None:
                return error.error_authorization_fail()

            if user_password_result[0] != password:
                return error.error_authorization_fail()

            cur.execute(
                'UPDATE "user" SET balance = balance + %s WHERE user_id = %s',
                (add_value, user_id),
            )
            if cur.rowcount == 0:
                return error.error_non_exist_user_id(user_id)
            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def confirm_order(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:          
            #order_collection = self.db["new_order"]
            #user_collection = self.db["user"]
            cursor = self.cur.execute(
                'SELECT user_id,state FROM "new_order" WHERE order_id = %s', (order_id,)
            )
            row = self.cur.fetchone()
            #order = order_collection.find_one({"order_id": order_id})
            if row is None:
                return error.error_invalid_order_id(order_id)
            
            if row[0] != user_id:
                return error.error_authorization_fail()
            
            if row[1] != "shipped":
                return error.error_wrong_state(order_id)
            cursor = self.cur.execute(
                'SELECT password FROM "user" WHERE user_id = %s', (user_id,)
            )
            row = self.cur.fetchone()
            #user = user_collection.find_one({"user_id": user_id})
            if row is None or row[0] != password:
                return error.error_authorization_fail()
            
            self.archive_order(order_id, "received")
            self.conn.commit()
        except psycopg2.Error as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"
    
    def list_orders(self, user_id: str, password: str, tle=30) -> (int, str, list):
        try:
            result = []
            cursor = self.cur.execute(
                'SELECT password FROM "user" WHERE user_id = %s', (user_id,)
            )
            row = self.cur.fetchone()
            if row is None or row[0] != password:
                return error.error_authorization_fail() + (result,)
            #
            cursor = self.cur.execute(
                'SELECT order_id,user_id,store_id,state,total_price FROM new_order WHERE user_id = %s', (user_id,)
            )
            orders = self.cur.fetchall()
            if orders is None:
                return error.error_authorization_fail() + (result,)

            for order in orders:

                output = {
                    "order_id": order[0],
                    "user_id": order[1],
                    "store_id": order[2],
                    "state": order[3],
                    "total_price": order[4],
                }
                result.append(output)

            cursor = self.cur.execute(
                'SELECT order_id,user_id,store_id,state,total_price FROM "archive_order" WHERE user_id = %s', (user_id,)
            )
            archive_orders = self.cur.fetchall()
            for archived_order in archive_orders:
                output = {
                    "order_id": archived_order[0],
                    "user_id": archived_order[1],
                    "store_id": archived_order[2],
                    "state": archived_order[3],
                    "total_price": archived_order[4],
                }
                result.append(output)  # Append all archived orders to result            

            self.conn.commit()
        except psycopg2.Error as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), []
        finally:
            self.cur.close()
            self.conn.close()

        return 200, "ok", result
    
    def cancel(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:          
            #order_collection = self.db["new_order"]
            #user_collection = self.db["user"]

            cursor = self.cur.execute(
                'SELECT user_id FROM "new_order" WHERE order_id = %s', (order_id,)
            )
            order = self.cur.fetchone()
            #order = order_collection.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)
            
            if order[0] != user_id:
                return error.error_authorization_fail()

            cursor = self.cur.execute(
                'SELECT password FROM "user" WHERE user_id = %s', (user_id,)
            )
            user = self.cur.fetchone()
            #user = user_collection.find_one({"user_id": user_id})
            if user is None or user[0] != password:
                return error.error_authorization_fail()
            
            self.archive_order(order_id, "cancelled")
            self.conn.commit()
        except psycopg2.Error as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"

    def archive_order(self, order_id, state) -> None:
        try:
            assert state in ["received", "cancelled"]
            self.cur.execute(
                "SELECT user_id, store_id, total_price, status FROM new_order WHERE order_id = %s;",
                (order_id,)
            )
            row = self.cur.fetchone()
            if not row:
                return error.error_invalid_order_id(order_id)

            buyer_id, store_id, total_price, status = row


            if status != "shipped":
                return


            self.cur.execute(
                "INSERT INTO archive_order(order_id, user_id, store_id, state, total_price) "
                "VALUES (%s, %s, %s, %s, %s)",
                (order_id, buyer_id, store_id, state, total_price),
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)
            
            self.cur.execute(
                "DELETE FROM new_order WHERE order_id = %s;",
                (order_id,)
            )

            self.conn.commit()

        except psycopg2.Error as e:
            logging.info("528, {}".format(str(e)))
            return
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return
        return
    
    def search(self, search_key, page=0) -> (int, str, list):
        try:
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
                page_prev = page_size * (page - 1)
                cursor = conn.execute(
                    "SELECT id, title, author, price FROM book WHERE title LIKE ? OR author LIKE ? OR publisher LIKE ? OR tags LIKE ? OR content LIKE ? LIMIT ? OFFSET ?",
                    ('%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%',
                     '%' + search_key + '%', page_size, page_prev),
                     )
            else:
                cursor = conn.execute(
                    "SELECT id, title, author, price FROM book WHERE title LIKE ? OR author LIKE ? OR publisher LIKE ? OR tags LIKE ? OR content LIKE ?",
                    ('%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%',
                     '%' + search_key + '%'),
                     )

            rows = cursor.fetchall()

            result = []
            for row in rows:
                book = {
                    "id": row[0],
                    "title": row[1],
                    "author": row[2],
                    "price": row[3]
                }
                result.append(book)

        except sqlite.Error as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        return 200, "ok", result

    def search_many(self, key_list):
        try:
            search_book = []
            for key in key_list:
                code, message, search_result = self.search(key, 0)
                if code != 200:
                    continue
                search_book += search_result
            found_book = {}
            for item in search_book:
                if item['id'] in found_book.keys():
                    continue
                found_book[item['id']] = item
            result = list(found_book.values())
        except sqlite.Error as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []

        return 200, "ok", result

    def search_in_store(self, store_id, search_key, page=0):
        try:
            grandparent_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_s = os.path.join(grandparent_path, "fe/data/book.db")
            db_l = os.path.join(grandparent_path, "fe/data/book_lx.db")
            if Use_Large_DB:
                book_db = db_l
            else:
                book_db = db_s
            conn = sqlite.connect(book_db)

            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)


            cursor = conn.execute(
                    "SELECT id, title, author, price FROM book WHERE title LIKE ? OR author LIKE ? OR publisher LIKE ? OR tags LIKE ? OR content LIKE ?",
                    ('%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%', '%' + search_key + '%',
                     '%' + search_key + '%',)
                     )
            rows = cursor.fetchall()
            if  rows is None:
                return 200, "ok", []
            result = []
            for row in rows:
                self.cur.execute(
                    "SELECT book_info FROM store WHERE store_id = %s AND book_id = %s;",
                    (store_id, row[0],)
                )
                store_rows = self.cur.fetchone()
                if store_rows is None:
                    continue
                else:
                    book = {
                        "id": row[0],
                        "title": row[1],
                        "author": row[2],
                        "price": row[3]
                    }   
                    result.append(book)

        except sqlite.Error as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok", result

    