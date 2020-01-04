import asyncio
import config
import pytz
import transaction
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta

jobstores = {
    'default': SQLAlchemyJobStore(
        url='sqlite:///' + config.SCHEDULER_DB_FILENAME)
}

_scheduler = None

def init_scheduler():
    '''Initializes the scheduler. Must be run **after**
    config has been initialized.'''
    print("Starting scheduler...")
    global _scheduler
    _scheduler = AsyncIOScheduler(jobstores=jobstores,
            job_defaults={
                'misfire_grace_time': None
            }
    )
    _scheduler.start()

def message_delayed_delete(message, delay=config.DEFAULT_MESSAGE_DELETE_DELAY):
    return delayed_execute(_message_delayed_delete,
            [message.id, message.channel.id],
            timedelta(seconds = config.DEFAULT_MESSAGE_DELETE_DELAY))

async def _auto_commit(draft_message_id, info_message_id, channel_id):
    channel = config.bot.get_channel(channel_id)
    draft_message = await channel.fetch_message(draft_message_id)
    info_message = await channel.fetch_message(info_message_id)

async def _message_delayed_delete(message_id, channel_id):
    channel = config.bot.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    await message.delete()

def delayed_execute(func, args, timedelta):
    exec_time = datetime.now(config.TIMEZONE) + timedelta

    id = _scheduler.add_job(_execute_wrapper, 'date',
            args=[func]+args, run_date = exec_time).id
    return id

# wrap function to include transaction.commit
async def _execute_wrapper(func, *args, **kwargs):
    ret = func(*args, **kwargs)
    if asyncio.iscoroutine(ret):
        ret = await ret
    transaction.commit()
    return ret

def deschedule(job_id):
    _scheduler.remove_job(job_id)

