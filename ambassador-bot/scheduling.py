import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(
        url='sqlite:///' + config.SCHEDULER_DB_FILENAME)
}

scheduler = AsyncIOScheduler(jobstores=jobstores)
scheduler.start()

def message_delayed_delete(message, delay=config.DEFAULT_MESSAGE_DELETE_DELAY):
    pass
    # TODO
    #scheduler.add_job(lambda
