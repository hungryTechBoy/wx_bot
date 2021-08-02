from peewee import *
from playhouse.pool import PooledMySQLDatabase

from conf import DATABASE_NAME, USER, HOST, PORT

# db = MySQLDatabase(DATABASE_NAME, user=USER, host=HOST, port=PORT)
db = PooledMySQLDatabase(DATABASE_NAME, user=USER, host=HOST, port=PORT, stale_timeout=25200)  # 7小时


class BaseModel(Model):
    class Meta:
        database = db
        legacy_table_names = False


class SchwarzeneggerPunchInTab(BaseModel):
    id = BigIntegerField()
    user_id = CharField()
    name = CharField()
    group_id = CharField()
    group_name = CharField()
    punch_in_count = IntegerField()
    ask_leave = BooleanField()
    reason = TextField()
    week = DateTimeField()
    ctime = DateTimeField()
    mtime = DateTimeField()


class UserTab(BaseModel):
    id = BigIntegerField()
    user_id = CharField()
    name = CharField()
    gender = IntegerField()
    group_id = CharField()
    group_name = CharField()
    ctime = DateTimeField()
