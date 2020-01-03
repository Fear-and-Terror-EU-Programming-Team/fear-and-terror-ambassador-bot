import asyncio
import config

# a channel only gets auto-deleted when people leave
# if the channel is above a certain age
# This doesn't need to be persistent, on bot restart,
# all channels are unprotected
channel_time_protection_set = set()


async def channel_time_protection(voice_channel, callback=None):
    await asyncio.sleep(config.CHANNEL_TIME_PROTECTION_LENGTH_SECONDS)
    if len(voice_channel.members) == 0:
        await voice_channel.delete()

    if callback is not None:
        callback(voice_channel)


async def message_delayed_delete(message):
    await asyncio.sleep(config.MESSAGE_DELETE_DELAY_SECONDS)
    await message.delete()


