# coding: utf-8
import asyncio
import re
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from wechaty import Wechaty, Contact, Message
from wechaty.utils import qr_terminal
from wechaty_puppet import get_logger, ScanStatus

from conf import ref_line, schwarzenegger_group_name, bot_name, need_con, my_nickname
from helper import check_group_member, command_name, punch_in, ask_for_leave, cancel_leave, query_count, \
    db_connect_wrapper, count_grade_every_week, cancel_pre_punch, auto_chat_bot

log = get_logger('RoomBot')


class MyBot(Wechaty):
    lock = Lock()
    last_msg_time = datetime.now()

    def on_scan(self, qr_code: Optional[str], status: ScanStatus,
                data: Optional[str] = None):
        qr_terminal(qr_code, 1)
        log.info("{0}\n[{1}] Scan QR Code in above url to login: ".format(qr_code, status))

    def on_error(self, payload):
        log.info(str(payload))

    def on_logout(self, contact: Contact):
        log.info('user %s logouted' % contact.name)

    async def on_login(self, contact: Contact):
        log.info('user %s login ' % contact.name)

    @db_connect_wrapper
    async def on_message(self, msg: Message):
        content = msg.text()
        is_punch = "本周第N次打卡" in content
        is_ask_leave = re.search(command_name["请假"]["command"], content)
        topic = await msg.room().topic() if msg.room() else ''
        if not (msg.room() and topic == schwarzenegger_group_name and need_con in content) \
                or msg.talker().name == bot_name \
                or (is_punch and is_ask_leave) \
                or re.search(ref_line, content):
            return
        try:
            self.lock.acquire()
            hour_late = self.last_msg_time + timedelta(seconds=10)
            if msg.date() > hour_late:
                check_group_member(await msg.room().member_list(), topic)
                self.last_msg_time = datetime.now()
            self.lock.release()

            if re.search(command_name["打卡"]["command"], content):
                count = int(re.search(command_name["打卡"]["command"], content).group(1))
                say_msg = punch_in(msg.talker(), topic, count)
            elif re.search(command_name["取消请假"]["command"], content):
                say_msg = cancel_leave(msg.talker(), topic)
            elif re.search(command_name["查询打卡"]["command"], content):
                say_msg = query_count(msg.talker(), topic)
            elif re.search(command_name["本周统计"]["command"], content):
                say_msg = count_grade_every_week(current_week=True)
            elif re.search(command_name["上周统计"]["command"], content):
                say_msg = count_grade_every_week(current_week=False)
            elif re.search(command_name["取消打卡"]["command"], content):
                say_msg = cancel_pre_punch(msg.talker(), topic)
            elif re.search(command_name["聊天"]["command"], content):
                say_msg = auto_chat_bot(content)
            elif is_ask_leave:
                if re.search(my_nickname, content):
                    say_msg = ask_for_leave(msg.talker(), topic, content)
                else:
                    say_msg = "请同时艾特打卡机器人和群主%s请假" % my_nickname
            else:
                say_msg = """没有找到命令，请检查你的输入
支持的命令:
"@没有感情的打卡机器 本周第N次打卡"-->打卡，注意N只能为数字，且不能跳着打卡
"@没有感情的打卡机器 @Valar·Morghulis 我本周请假" -->请假
"@没有感情的打卡机器 取消我的请假" -->取消我的请假
"@没有感情的打卡机器 查询本周打卡次数" --> 查询本周已打卡次数
"@没有感情的打卡机器 取消上次打卡" --> 取消上次打卡
"""
            say_msg = "@%s %s" % (msg.talker().name, say_msg)
            await msg.say(say_msg, mention_ids=[msg.talker().get_id()])
        except AssertionError as e:
            pass
        except Exception as e:
            log.exception(e)
            say_msg = "@%s %s" % (msg.talker().name, "发生异常，请重新输入")
            await msg.say(say_msg, mention_ids=[msg.talker().get_id()])


async def main():
    bot = MyBot()
    await bot.start()


if __name__ == '__main__':
    asyncio.run(main())
