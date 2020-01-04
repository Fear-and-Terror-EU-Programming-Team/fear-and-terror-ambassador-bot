import asyncio

def synchronized(func, lock=None):
    func.__lock__ = lock or asyncio.Lock()

    async def synced_func(*args, **kws):
        async with func.__lock__:
            return await func(*args, **kws)

    synced_func.__name__ = func.__name__
    return synced_func
