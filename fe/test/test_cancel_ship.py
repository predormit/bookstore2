import pytest
import uuid
from fe.access.new_buyer import register_new_buyer
from fe.access.new_seller import register_new_seller
from fe.test.gen_book_data import GenBook
from fe.access import book
from fe import conf


class TestCancelShip:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.user_id = "test_cancel_ship_{}".format(str(uuid.uuid1()))
        self.password = self.user_id
        self.buyer = register_new_buyer(self.user_id, self.password)
        self.seller_id = "test_cancel_ship_seller_id_{}".format(str(uuid.uuid1()))
        self.seller_password = self.seller_id
        # self.seller = register_new_seller(self.seller_id, self.seller_password)
        self.store_id = "test_cancel_ship_store_id_{}".format(str(uuid.uuid1()))
        # code = self.seller.create_store(self.store_id)
        # assert code == 200
        # book_db = book.BookDB(conf.Use_Large_DB)
        # self.books = book_db.get_book_info(0, 5)
        # for bk in self.books:
        #     code = self.seller.add_book(self.store_id, 0, bk)
        #     assert code == 200
        self.gen_book = GenBook(self.seller_id, self.store_id)
        ok,buy_book_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        self.seller = self.gen_book.seller
        assert ok
        status_code,self.order_id = self.buyer.new_order(self.store_id,buy_book_list)
        assert status_code == 200
        code = self.buyer.add_funds(100000000000)
        assert code == 200
        code = self.buyer.payment(self.order_id)
        assert code == 200
        yield

    def test_ok(self):
        code = self.seller.cancel_ship(self.seller_id, self.store_id, self.order_id)
        assert code == 200

    def test_error_store_id(self):
        self.store_id = self.store_id + "_x"
        code = self.seller.cancel_ship(self.seller_id, self.store_id, self.order_id)
        assert code != 200

    def test_error_seller_id(self):
        self.seller_id = self.seller_id + "_x"
        code = self.seller.cancel_ship(self.seller_id, self.store_id, self.order_id)
        assert code != 200

    def test_error_order_id(self):
        self.order_id = self.order_id + "_x"
        code = self.seller.cancel_ship(self.seller_id, self.store_id, self.order_id)
        assert code != 200