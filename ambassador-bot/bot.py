#!/usr/bin/env python3

import discord
import config
import emojis
import functools
import transaction
from discord.ext import commands
from discord.utils import get
from database import db

bot = commands.Bot(command_prefix=config.BOT_CMD_PREFIX)

# no need to edit manually, will be populated by decorators
emoji_handlers = {}


def emoji_handler(emoji=None, channel_id=-1):
    # looks weird. is weird. blame python.
    def decorator(func):
        global emoji_handlers
        if channel_id not in emoji_handlers:
            emoji_handlers[channel_id] = {}
        emoji_handlers[channel_id] = func
        # don't actually wrap anything
        return func
    return decorator


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await register_application(message)
    await bot.process_commands(message)
    transaction.commit()

async def register_application(message):
    if message.channel.id != config.APPLICATION_CHANNEL:
        return
    await message.channel.send("New application")

@emoji_handler(emoji=emojis.UPVOTE, channel_id=config.APPLICATION_CHANNEL)
async def commit_application(rp):
    await rp.channel.send(f"Application from "
                          f"{rp.member.mention} committed.")

@bot.event
async def on_raw_reaction_add(payload):
    rp = await unwrap_payload(payload)
    if is_admin(rp.member):
        await handle_react(rp)
    else:
        await rp.message.remove_reaction(rp.emoji, rp.member)


async def on_raw_reaction_remove(payload):
    rp = await unwrap_payload(payload)
    if is_admin(rp.member):
        await handle_react(rp)
    else:
        await rp.message.remove_reaction(rp.emoji, rp.member)


async def handle_react(rp):
    if rp.channel.id not in emoji_handlers:
        return
    if str(rp.emoji) not in emoji_handlers[rp.channel.id]:
        return
    # call appropriate handler
    await emoji_handlers[rp.channel.id][str(rp.emoji)]()
    transaction.commit()


async def applications_process(rp):
    voting = bot.get_channel(config.VOTING_CHANNEL)
    archive = bot.get_channel(config.ARCHIVE_CHANNEL)
    await voting.send(f"{rp.message.author.mention} ```{rp.message.content}```")
    await archive.send(f"{rp.message.author.mention} ```{rp.message.content}```")
    await rp.channel.send(f"{rp.message.author.mention} yahYEET")
    await rp.message.delete()


async def voting_process(rp):
    reaction = get(rp.message.reactions, emoji=rp.emoji.name)
    if str(rp.emoji) == Emojis.HEAVY_CHECK_MARK and reaction.count == 1:
        print("Yahh")
    if str(rp.emoji) == Emojis.WHITE_CHECK_MARK and reaction.count == 1:
        print("Yeet")


async def unwrap_payload(payload):
    rp = ReactionPayload()
    await rp._init(payload)
    return rp


class ReactionPayload():
    # this might be a bit heavy on the API
    async def _init(self, payload):
        self.guild = bot.get_guild(payload.guild_id)
        self.member = await self.guild.fetch_member(payload.user_id)
        self.emoji = payload.emoji
        self.channel = bot.get_channel(payload.channel_id)
        self.message = await self.channel.fetch_message(payload.message_id)


def is_admin(user):
    return any([role.id in config.BOT_ADMIN_ROLES for role in user.roles])



if __name__ == "__main__":
    bot.run(config.BOT_TOKEN)
