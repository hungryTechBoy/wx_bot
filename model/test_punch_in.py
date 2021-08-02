import datetime
import time
from unittest import TestCase

from helper import db_connect_wrapper
from model.punch_in import UserTab, db


class TestUserTab(TestCase):
    def test_create(self):
        # user=UserTab(user_id="123457",ctime=datetime.datetime.now())
        # user.save()

        # print([user.id for user in UserTab.select().where(UserTab.user_id.in_({"123457"}))])

        # now = datetime.datetime.now()
        # print(UserTab.select().where(UserTab.ctime > datetime.datetime(now.year, 1, 1),UserTab.id>0))
        # for user in UserTab.select().where(UserTab.ctime > datetime.datetime(now.year, 1, 1)):
        #     print(user.id)
        count = 10
        for i in range(count):
            test(i)
            time.sleep(3)


@db_connect_wrapper
def test(i):
    print([user.id for user in UserTab.select()])
    print("count is %s" % i)
