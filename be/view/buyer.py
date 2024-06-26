from flask import Blueprint
from flask import request
from flask import jsonify
from be.model.buyer import Buyer

bp_buyer = Blueprint("buyer", __name__, url_prefix="/buyer")


@bp_buyer.route("/new_order", methods=["POST"])
def new_order():
    user_id: str = request.json.get("user_id")
    store_id: str = request.json.get("store_id")
    books: [] = request.json.get("books")
    id_and_count = []
    for book in books:
        book_id = book.get("id")
        count = book.get("count")
        id_and_count.append((book_id, count))

    b = Buyer()
    code, message, order_id = b.new_order(user_id, store_id, id_and_count)
    return jsonify({"message": message, "order_id": order_id}), code


@bp_buyer.route("/payment", methods=["POST"])
def payment():
    user_id: str = request.json.get("user_id")
    order_id: str = request.json.get("order_id")
    password: str = request.json.get("password")
    b = Buyer()
    code, message = b.payment(user_id, password, order_id)
    return jsonify({"message": message}), code


@bp_buyer.route("/add_funds", methods=["POST"])
def add_funds():
    user_id = request.json.get("user_id")
    password = request.json.get("password")
    add_value = request.json.get("add_value")
    b = Buyer()
    code, message = b.add_funds(user_id, password, add_value)
    return jsonify({"message": message}), code

@bp_buyer.route("/confirm_order", methods=["POST"])
def confirm_order():
    user_id = request.json.get("user_id")
    password = request.json.get("password")
    order_id = request.json.get("order_id")
    b = Buyer()
    code, message = b.confirm_order(user_id, password, order_id)
    return jsonify({"message": message}), code

@bp_buyer.route("/list_orders", methods=["POST"])
def list_orders():
    user_id = request.json.get("user_id")
    password = request.json.get("password")
    b = Buyer()
    code, message, orders = b.list_orders(user_id, password)
    return jsonify({"message": message, "orders": orders}), code

@bp_buyer.route("/cancel", methods=["POST"])
def cancel():
    user_id = request.json.get("user_id")
    password = request.json.get("password")
    order_id = request.json.get("order_id")
    b = Buyer()
    code, message = b.cancel(user_id, password, order_id)
    return jsonify({"message": message}), code

@bp_buyer.route("/goodsrejected", methods=["POST"])
def goodsrejected():
    user_id = request.json.get("user_id")
    password = request.json.get("password")
    order_id = request.json.get("order_id")
    b = Buyer()
    code, message = b.goodsrejected(user_id, password, order_id)
    return jsonify({"message": message}), code

@bp_buyer.route("/search", methods=["POST"])
def search():
    search_key: str = request.json.get("search_key")
    page: int = request.json.get("page")
    b = Buyer()
    code, message, result = b.search(search_key, page)
    return jsonify({"message": message, "result": result}), code

@bp_buyer.route("/search_many", methods=["POST"])
def search_many():
    search_key: list = request.json.get("search_key")
    b = Buyer()
    code, message, result = b.search_many(search_key)
    return jsonify({"message": message, "result": result}), code

@bp_buyer.route("/search_in_store", methods=["POST"])
def search_in_store():
    search_key: str = request.json.get("search_key")
    store_id: str = request.json.get("store_id")
    page: int = request.json.get("page")
    b = Buyer()
    code, message, result = b.search_in_store(store_id, search_key, page)
    return jsonify({"message": message, "result": result}), code

@bp_buyer.route("/get_book_info", methods=["POST"])
def check_books_info():
    book_list: list = request.json.get("book")
    b = Buyer()
    code, message, result = b.get_book_info(book_list)
    return jsonify({"message": message, "result": result}), code

@bp_buyer.route("/archive_order", methods=["POST"])
def archive_order():
    order_id = request.json.get("order_id")
    state = request.json.get("state")
    b = Buyer()
    code, message = b.archive_order(order_id, state)
    return jsonify({"message": message}), code
