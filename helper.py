# coding: utf-8
import datetime
import functools
import urllib
from typing import List

import requests
from wechaty import Contact

from conf import schwarzenegger_group_id, schwarzenegger_group_name, NEED_PUNCH_COUNT, bot_id, bot_name, need_con
from model.punch_in import UserTab, db, SchwarzeneggerPunchInTab

punch_interval = 6
command_name = {
    "打卡": {
        "command": "本周第(\d+)次打卡",
        "成功": "你做的很棒！请再接再厉！",
        "已经请假": "你已经请假，请取消请假后再打卡。",
        "次数不对": "你上次打卡为第 %s 次，请勿跳卡。",
        "间隔过短": "打卡失败，距离上次打卡时间需要超过%s小时" % punch_interval
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
    },
    "本周统计": {
        "command": "查询本周数据统计",
    },
    "上周统计": {
        "command": "查询上周数据统计",
    },
    "取消打卡": {
        "command": "取消上次打卡",
        "成功": "成功取消上次打卡，你的本周打卡次数为%s次"
    },
    "聊天": {
        "command": "#聊天#",
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
    contact_map = {c.name: c for c in contact_list}
    member_names = [c.name for c in contact_list]
    now = datetime.datetime.now()
    in_db_names = set([user.name for user in
                       UserTab.select().where(UserTab.group_name == schwarzenegger_group_name)])
    in_punch_in_names = set([punch.name for punch in
                             SchwarzeneggerPunchInTab.select().
                            where(SchwarzeneggerPunchInTab.group_name == schwarzenegger_group_name,
                                  SchwarzeneggerPunchInTab.week == get_zero_week(),
                                  )])
    member_names_set = set(member_names)
    user_list = []
    for name in member_names_set - in_db_names:
        user = UserTab(user_id=contact_map[name].get_id(), name=name,
                       gender=contact_map[name].gender(),
                       group_id=schwarzenegger_group_id,
                       group_name=room_name,
                       ctime=now
                       )
        user_list.append(user)
    punch_list = []
    for name in member_names_set - in_punch_in_names:
        if name == bot_name:
            continue
        punch = SchwarzeneggerPunchInTab(
            user_id=contact_map[name].get_id(),
            name=name,
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

        del_user_names = in_db_names - member_names_set
        if len(del_user_names):
            UserTab.delete().where(UserTab.name.in_(del_user_names)).execute()

        del_punch_names = in_punch_in_names - member_names_set
        if len(del_punch_names):
            SchwarzeneggerPunchInTab.delete().where(
                SchwarzeneggerPunchInTab.name.in_(del_user_names),
                SchwarzeneggerPunchInTab.week == get_zero_week(),
            ).execute()


def get_or_create_punch(contact: Contact, room_name):
    now = datetime.datetime.now()
    punch, created = SchwarzeneggerPunchInTab.get_or_create(name=contact.name,
                                                            group_id=schwarzenegger_group_id,
                                                            week=get_zero_week(),
                                                            defaults={'user_id': contact.get_id(),
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
    if punch.punch_in_count > 0 and (punch.mtime + datetime.timedelta(hours=6) > now):
        return command_name["打卡"]["间隔过短"]

    punch.punch_in_count = count
    punch.mtime = now
    punch.save()
    return command_name["打卡"]["成功"]


def ask_for_leave(contact: Contact, room_name, reason):
    punch = get_or_create_punch(contact, room_name)
    punch.ask_leave = True
    punch.reason = reason
    punch.save()
    return command_name["请假"]["成功"]


def cancel_leave(contact: Contact, room_name):
    punch = get_or_create_punch(contact, room_name)
    punch.ask_leave = False
    punch.save()
    return command_name["取消请假"]["成功"]


def cancel_pre_punch(contact: Contact, room_name):
    punch = get_or_create_punch(contact, room_name)
    if punch.punch_in_count > 0:
        punch.punch_in_count -= 1
        punch.save()
    return command_name["取消打卡"]["成功"] % punch.punch_in_count


def query_count(contact: Contact, room_name):
    punch = get_or_create_punch(contact, room_name)
    return command_name["查询打卡"]["成功"] % punch.punch_in_count


def count_grade_every_week(current_week):
    out_str_list = []
    if current_week:
        out_str_list.append("\n本周数据统计如下")
        week_fun = get_zero_week
    else:
        out_str_list.append("\n上周数据统计如下")
        week_fun = get_pre_zero_week

    out_str_list.append("缺卡数据明细:")
    query = SchwarzeneggerPunchInTab.select().where(
        SchwarzeneggerPunchInTab.group_id == schwarzenegger_group_id,
        SchwarzeneggerPunchInTab.week == week_fun(),
        SchwarzeneggerPunchInTab.ask_leave == False,
        SchwarzeneggerPunchInTab.punch_in_count < NEED_PUNCH_COUNT
    ).order_by(SchwarzeneggerPunchInTab.punch_in_count)
    for q in query:
        if q.name == bot_name:
            continue
        out_str_list.append("@%s 缺卡%s次" % (q.name, NEED_PUNCH_COUNT - q.punch_in_count))

    out_str_list.append("打卡排行榜:")
    query = SchwarzeneggerPunchInTab.select().where(
        SchwarzeneggerPunchInTab.group_id == schwarzenegger_group_id,
        SchwarzeneggerPunchInTab.week == week_fun(),
        SchwarzeneggerPunchInTab.ask_leave == False,
        SchwarzeneggerPunchInTab.punch_in_count >= NEED_PUNCH_COUNT
    ).order_by(SchwarzeneggerPunchInTab.punch_in_count.desc()).limit(3)
    for q in query:
        out_str_list.append("@%s 打卡%s次" % (q.name, q.punch_in_count))

    out_str_list.append("请假明细:")
    query = SchwarzeneggerPunchInTab.select().where(
        SchwarzeneggerPunchInTab.group_id == schwarzenegger_group_id,
        SchwarzeneggerPunchInTab.week == week_fun(),
        SchwarzeneggerPunchInTab.ask_leave == True,
    )
    for q in query:
        out_str_list.append("@%s 请假" % (q.name))

    return '\n'.join(out_str_list)


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


def qingyunke(msg):
    url = 'http://api.qingyunke.com/api.php?key=free&appid=0&msg={}'.format(urllib.parse.quote(msg))
    html = requests.get(url)
    return html.json()["content"].replace("{br}", '\n')


def auto_chat_bot(content):
    content = content.replace(need_con, "")
    content = content.replace(command_name["聊天"]["command"], "")
    return qingyunke(content)
