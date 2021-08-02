import time
from datetime import datetime
import os

from apscheduler.schedulers.blocking import BlockingScheduler
import os
import time
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler


def tick():
    print('Tick! The time is: %s' % datetime.now())


if __name__ == '__main__':
    scheduler = BlockingScheduler()
    # scheduler.add_executor('processpool')
    scheduler.add_job(tick, 'cron', day_of_week='mon', hour=12, minute=0)
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        scheduler.start()
        time.sleep(1000000)
    except (KeyboardInterrupt, SystemExit):
        pass
