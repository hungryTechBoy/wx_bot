# coding: utf-8
import datetime
import functools
from typing import List

from wechaty import Contact

from conf import schwarzenegger_group_id, schwarzenegger_group_name
from model.punch_in import UserTab, db, SchwarzeneggerPunchInTab

command_name = {
    "打卡": {
        "command": "本周第(\d+)次打卡",
        "成功": "你做的很棒！请再接再厉！",
        "已经请假": "你已经请假，请取消请假后再打卡。",
        "次数不对": "你上次打卡为第 %s 次，请勿跳卡。",
    },
    "请假": {
        "command": "我本周请假",
        "成功": "好的，你已经请假，希望下周看到你努力的身影。"
    },
    "取消请假": {
        "command": "取消我的请假",
        "成功": "好的，你已经成功取消请假，请继续加油打卡哦。"
    },
    "查询打卡": {
        "command": "查询本周打卡次数",
        "成功": "你的本周打卡次数为%s次"
    }
}


def db_connect_wrapper(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if db.is_closed():
            db.connect()
        result = await func(*args, **kwargs)
        db.close()
        return result

    return wrapper


def check_group_member(contact_list: List[Contact], room_name):
    contact_map = {c.get_id(): c for c in contact_list}
    member_ids = [c.get_id() for c in contact_list]
    now = datetime.datetime.now()
    in_db_ids = set([user.user_id for user in
                     UserTab.select().where(UserTab.group_name == schwarzenegger_group_name)])
    in_punch_in_ids = set([punch.user_id for punch in
                           SchwarzeneggerPunchInTab.select().
                          where(SchwarzeneggerPunchInTab.group_name == schwarzenegger_group_name,
                                SchwarzeneggerPunchInTab.week == get_zero_week(),
                                )])
    member_ids_set = set(member_ids)
    user_list = []
    for id in member_ids_set - in_db_ids:
        user = UserTab(user_id=id, name=contact_map[id].name,
                       gender=contact_map[id].gender(),
                       group_id=schwarzenegger_group_id,
                       group_name=room_name,
                       ctime=now
                       )
        user_list.append(user)
    punch_list = []
    for id in member_ids_set - in_punch_in_ids:
        punch = SchwarzeneggerPunchInTab(
            user_id=id,
            name=contact_map[id].name,
            group_id=schwarzenegger_group_id,
            group_name=room_name,
            punch_in_count=0,
            ask_leave=False,
            reason="",
            week=get_zero_week(),
            ctime=now,
            mtime=now,
        )
        punch_list.append(punch)

    with db.atomic():
        UserTab.bulk_create(user_list, batch_size=100)
        SchwarzeneggerPunchInTab.bulk_create(punch_list, batch_size=100)

        del_user_ids = in_db_ids - member_ids_set
        if len(del_user_ids) > 0:
            UserTab.delete().where(UserTab.user_id.in_(del_user_ids)).execute()

        del_punch_ids = in_punch_in_ids - member_ids_set
        if len(del_punch_ids):
            SchwarzeneggerPunchInTab.delete().where(
                SchwarzeneggerPunchInTab.user_id.in_(del_user_ids),
                SchwarzeneggerPunchInTab.week == get_zero_week(),
            ).execute()


def get_or_create_punch(contact: Contact, room_name):
    now = datetime.datetime.now()
    punch, created = SchwarzeneggerPunchInTab.get_or_create(user_id=contact.get_id(),
                                                            group_id=schwarzenegger_group_id,
                                                            week=get_zero_week(),
                                                            defaults={'name': contact.name,
                                                                      'group_name': room_name,
                                                                      "ask_leave": False,
                                                                      "punch_in_count": 0,
                                                                      "ctime": now,
                                                                      "mtime": now
                                                                      })
    return punch


def punch_in(contact: Contact, room_name, count):
    now = datetime.datetime.now()
    punch = get_or_create_punch(contact, room_name)
    if punch.ask_leave:
        return command_name["打卡"]["已经请假"]
    if count - punch.punch_in_count != 1:
        return command_name["打卡"]["次数不对"] % punch.punch_in_count

    punch.punch_in_count = count
    punch.mtime = now
    punch.save()
    return command_name["打卡"]["成功"]


def ask_for_leave(contact: Contact, room_name, reason):
    punch = get_or_create_punch(contact, room_name)
    punch.ask_leave = True
    punch.mtime = datetime.datetime.now()
    punch.reason = reason
    punch.save()
    return command_name["请假"]["成功"]


def cancel_leave(contact: Contact, room_name):
    punch = get_or_create_punch(contact, room_name)
    punch.ask_leave = False
    punch.mtime = datetime.datetime.now()
    punch.save()
    return command_name["取消请假"]["成功"]


def query_count(contact: Contact, room_name):
    punch = get_or_create_punch(contact, room_name)
    return command_name["查询打卡"]["成功"] % punch.punch_in_count


# def count_grade_every_week():
#     query = SchwarzeneggerPunchInTab.select().where(
#         SchwarzeneggerPunchInTab.group_id == schwarzenegger_group_id,
#         SchwarzeneggerPunchInTab.week == get_pre_zero_week(),
#         SchwarzeneggerPunchInTab.ask_leave == False,
#         SchwarzeneggerPunchInTab.punch_in_count < NEED_PUNCH_COUNT
#     ).order_by(SchwarzeneggerPunchInTab.punch_in_count)
#
#     low_grade_list = []
#     for q in query:
#         low_grade_list.append("@%s 本周缺卡%s次\n" % (q.name, NEED_PUNCH_COUNT - q.punch_in_count))
#
#     query = SchwarzeneggerPunchInTab.select().where(
#         SchwarzeneggerPunchInTab.group_id == schwarzenegger_group_id,
#         SchwarzeneggerPunchInTab.week == get_pre_zero_week(),
#         SchwarzeneggerPunchInTab.ask_leave == False,
#         SchwarzeneggerPunchInTab.punch_in_count >= NEED_PUNCH_COUNT
#     ).order_by(SchwarzeneggerPunchInTab.punch_in_count.desc()).limit(3)


def get_zero_week():
    now = datetime.datetime.now()
    zero_week = now - datetime.timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second,
                                         microseconds=now.microsecond)
    return zero_week


def get_pre_zero_week():
    now = datetime.datetime.now()
    zero_week = now - datetime.timedelta(days=now.weekday() + 7, hours=now.hour, minutes=now.minute, seconds=now.second,
                                         microseconds=now.microsecond)
    return zero_week
