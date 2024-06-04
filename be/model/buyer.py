import uuid
import json
import logging
from be.model import db_conn
from be.model import error
from pymongo.errors import PyMongoError


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

            store_col = self.db['store']
            order_details = []
            total_price = 0
            for book_id, count in id_and_count:
                result_col = store_col.find_one({"store_id": store_id, "book_id": book_id})

                if not result_col:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = result_col["stock_level"]
                book_info = json.loads(result_col["book_info"])
                price = book_info.get("price")
                total_price += price * count

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                query = {
                    "$and": [
                        {"store_id": store_id},
                        {"book_id": book_id},
                        {"stock_level": {"$gte": count}}
                    ]
                }
                new_values = {"$set": {"stock_level": stock_level-count}}
                result = store_col.update_one(query, new_values)
                if result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)
                order_details.append({
                    "order_id": order_id,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                })
               
            if order_details:
                self.db['new_order_detail'].insert_many(order_details)   
            new_order_info = {
                "order_id": order_id,
                "store_id": store_id,
                "user_id": user_id,
                "total_price": total_price,
                "state": "Pending",
            }
            self.db['new_order'].insert_one(new_order_info)        
        except PyMongoError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""
        
        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> tuple[int, str]:
        db = self.db
        try:
            result = db['new_order'].find_one({"order_id": order_id})
            if result is None:
                return error.error_invalid_order_id(order_id)

            order_id = result["order_id"]
            buyer_id = result["user_id"]
            store_id = result["store_id"]
            total_price = result.get("total_price", 0)

            if buyer_id != user_id:
                return error.error_authorization_fail()

        
            result = db['user'].find_one({"user_id": buyer_id}, {"balance": 1, "password": 1})
            if result is None:
                return error.error_invalid_order_id(order_id)
            balance = result['balance']
            if password != result['password']:
                return error.error_authorization_fail()

            seller_info = db['user_store'].find_one({"store_id": store_id})
            if seller_info is None:
                return error.error_non_exist_store_id(store_id)
            seller_id = seller_info['user_id']

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)
            
            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            buyer_update_result = db['user'].update_one(
                {"user_id": buyer_id, "balance": {"$gte": total_price}},
                {"$inc": {"balance": - total_price}}
            )
            if buyer_update_result.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            seller_update_result = db['user'].update_one(
                {"user_id": seller_id},
                {"$inc": {"balance": total_price}}
            )
            if seller_update_result.modified_count == 0:
                return error.error_non_exist_user_id(seller_id)

            update_result = db["new_order"].update_one(
                {"order_id": order_id},
                {"$set": {"state": "unshipped"}},
            )
            if update_result.modified_count == 0:
                return error.error_invalid_order_id(order_id)


        except PyMongoError as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))
       
        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> tuple[int, str]:
        db = self.db
        try:
            user_password_result = db['user'].find_one({"user_id": user_id}, {"password": 1})
            if user_password_result is None:
                return error.error_authorization_fail()

            if user_password_result['password'] != password:
                return error.error_authorization_fail()

            update_balance_result = db['user'].update_one(
                {"user_id": user_id},
                {"$inc": {"balance": add_value}}
            )
            if update_balance_result.modified_count == 0:
                return error.error_non_exist_user_id(user_id)
        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def confirm_order(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:          
            order_collection = self.db["new_order"]
            user_collection = self.db["user"]
            
            order = order_collection.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)
            
            if order["user_id"] != user_id:
                return error.error_authorization_fail()
            
            if order["state"] != "shipped":
                return error.error_wrong_state(order_id)
            
            user = user_collection.find_one({"user_id": user_id})
            if user is None or user["password"] != password:
                return error.error_authorization_fail()
            
            self.archive_order(order_id, "Received")

        except PyMongoError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"
    
    def list_orders(self, user_id: str, password: str, tle=30) -> (int, str, list):
        try:
            result = []

            order_collection = self.db["new_order"]
            order_archive_collection = self.db["archive_order"]
            user_collection = self.db["user"]
            
            user = user_collection.find_one({"user_id": user_id})
            if user is None or user["password"] != password:
                return error.error_authorization_fail() + (result,)

            orders = order_collection.find({"user_id": user_id})
            for order in orders:

                output = {
                    "order_id": order["order_id"],
                    "user_id": order["user_id"],
                    "store_id": order["store_id"],
                    "state": order["state"],
                    "total_price": order["total_price"],
                }
                result.append(output)

            archived_orders = order_archive_collection.find({"user_id": user_id})
            for archived_order in archived_orders:
                output = {
                    "order_id": archived_order["order_id"],
                    "user_id": archived_order["user_id"],
                    "store_id": archived_order["store_id"],
                    "state": archived_order["state"],
                    "total_price": archived_order["total_price"],
                }
                result.append(output)  # Append all archived orders to result            

        except PyMongoError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), []
        return 200, "ok", result
    
    def cancel(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:          
            order_collection = self.db["new_order"]
            user_collection = self.db["user"]
            
            order = order_collection.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)
            
            if order["user_id"] != user_id:
                return error.error_authorization_fail()
            
            user = user_collection.find_one({"user_id": user_id})
            if user is None or user["password"] != password:
                return error.error_authorization_fail()
            
            self.archive_order(order_id, "Cancelled")

        except PyMongoError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"

    def archive_order(self, order_id, state) -> None:
        try:
            assert state in ["Cancelled", "Received"]
            order_collection = self.db["new_order"]
            order_archive_collection = self.db["archive_order"]
            
            order_info = order_collection.find_one({"order_id": order_id})
            if order_info is None:
                raise PyMongoError(f"No order found with order_id: {order_id}")
            
            archived_order = order_info.copy()
            archived_order["state"] = state
            
            order_archive_collection.insert_one(archived_order)
            
            order_collection.delete_one({"order_id": order_id})

        except PyMongoError as e:
            logging.info("528, {}".format(str(e)))
            return
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return
        return
    
    def search(self, search_key, page=0) -> (int, str, list):
        try:
            if page > 0:
                page_size = 10
                page_prev = page_size * (page - 1)
                find_result = self.db["book"].find({
                    "$or": [
                        {"title": {"$regex": search_key, "$options": "i"}},
                        {"author": {"$regex": search_key, "$options": "i"}},
                        {"publisher": {"$regex": search_key, "$options": "i"}},
                        {"tags": {"$regex": search_key, "$options": "i"}},
                        {"content": {"$regex": search_key, "$options": "i"}}
                    ]
                }, {"id":1, "title":1, "author":1}).limit(page_size).skip(page_prev)                

            else:
                find_result = self.db["book"].find({
                    "$or": [
                        {"title": {"$regex": search_key, "$options": "i"}},
                        {"author": {"$regex": search_key, "$options": "i"}},
                        {"publisher": {"$regex": search_key, "$options": "i"}},
                        {"tags": {"$regex": search_key, "$options": "i"}},
                        {"content": {"$regex": search_key, "$options": "i"}}
                    ]
                }, {"id":1, "title":1, "author":1})
            rows = find_result

            if rows is None:
                return 200, "ok", []

            result = []
            for row in rows:
                book = {
                    "id": row['id'],
                    "title": row['title'],
                    "author": row['author']
                }
                result.append(book)

        except PyMongoError as e:
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
        except PyMongoError as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        
        return 200, "ok", result

    def search_in_store(self, store_id, search_key, page=0):
        try:
            page_size = 10
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            book_id_result = self.db['store'].find({'store_id': store_id}, {'book_id':1})
            book_id_list = []
            for item in book_id_result:
                book_id_list.append(item['book_id'])

            if page > 0:
                page_prev = page_size * (page - 1)
                find_result = self.db["book"].find({
                    "$and": [
                        {
                        "$or": [
                            {"title": {"$regex": search_key, "$options": "i"}},
                            {"author": {"$regex": search_key, "$options": "i"}},
                            {"publisher": {"$regex": search_key, "$options": "i"}},
                            {"tags": {"$regex": search_key, "$options": "i"}},
                            {"content": {"$regex": search_key, "$options": "i"}}
                            ]
                        },
                        {"id": {"$in": book_id_list}}]
                }, {"id":1, "title":1, "author":1, "price":1}).limit(page_size).skip(page_prev)                

            else:
                find_result = self.db["book"].find({
                    "$and": [
                        {
                        "$or": [
                            {"title": {"$regex": search_key, "$options": "i"}},
                            {"author": {"$regex": search_key, "$options": "i"}},
                            {"publisher": {"$regex": search_key, "$options": "i"}},
                            {"tags": {"$regex": search_key, "$options": "i"}},
                            {"content": {"$regex": search_key, "$options": "i"}}
                            ]
                        },
                        {"id": {"$in": book_id_list}}]
                }, {"id":1, "title":1, "author":1, "price":1})
            rows = find_result

            result = []
            for row in rows:
                book = {
                    "id": row["id"],
                    "title": row["title"],
                    "author": row["author"],
                    "price": row["price"]
                }
                result.append(book)

        except PyMongoError as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        return 200, "ok", result
    