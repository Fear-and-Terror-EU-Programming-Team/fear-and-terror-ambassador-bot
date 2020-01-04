import config
import discord
import emojis
import persistent
import scheduling
import time
from database import db
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Draft(persistent.Persistent):

    applicant_id : int
    draft_message_id : int
    info_message_id : int
    commit_job_id : str = None

    async def create(draft_message):
        info_msg = await draft_message.channel.send(
                f"{draft_message.author.mention} "
                f"Thanks for applying to Fear and Terror. "
                f"You now have the chance to edit your application before "
                f"sending it to our review team. "
                f"Once you're done, click the {emojis.COMMIT_APPLICATION} "
                f"emoji. "
                f"If you want to retract your application and delete your "
                f"message, click the {emojis.DELETE_APPLICATION} emoji."
                f"\n\n"
                f"Otherwise, your application will be sent off automatically "
                f"in {config.AUTOCOMMIT_DELAY_MINUTES} minutes.")
        await draft_message.add_reaction(emojis.COMMIT_APPLICATION)
        await draft_message.add_reaction(emojis.DELETE_APPLICATION)

        # add draft to database
        draft = Draft(draft_message.author.id, draft_message.id, info_msg.id)
        db.drafts[draft_message.id] = draft

        # schedule autocommit
        job_id = scheduling.delayed_execute(Application.create, [draft],
                timedelta(seconds=config.AUTOCOMMIT_DELAY_MINUTES)) # TODO minutes
        draft.commit_job_id = job_id

        return draft

    async def delete(self):
        application_channel = \
                config.bot.get_channel(config.APPLICATION_CHANNEL)
        draft_message = \
                await application_channel.fetch_message(self.draft_message_id)
        info_message = \
                await application_channel.fetch_message(self.info_message_id)

        await draft_message.delete()
        await info_message.delete()

        del db.drafts[draft_message.id]


@dataclass
class Application(persistent.Persistent):

    applicant_id : int
    voting_message_id : int
    archive_message_id : int
    frozen : bool = False
    vote_close_job_id : str = None

    async def create(draft):
        '''Commits a draft, copying it to
        the voting and archive channel.'''
        draft_message = await config.application_channel \
                .fetch_message(draft.draft_message_id)
        applicant = draft_message.author
        ambassador_role = draft_message.guild.get_role(config.AMBASSADOR_ROLE)

        # build voting and archive message content
        app_content = draft_message.content
        app_content = app_content.replace("```", "") # strip code blocks
        voting_content = (f"{ambassador_role.mention}\n{applicant.mention}\n"
                        f"```{app_content}```")
        archive_content = (f"{applicant.mention}\n"
                        f"```{app_content}```")

        # Re-post message in voting and archive channel
        voting_message = await config.voting_channel.send(voting_content)
        archive_message = await config.archive_channel.send(archive_content)

        await voting_message.add_reaction(emojis.UPVOTE)
        await voting_message.add_reaction(emojis.DOWNVOTE)
        await voting_message.add_reaction(emojis.FREEZE_APPLICATION)

        await draft.delete()

        info_msg = await config.application_channel.send(
                f"{applicant.mention} Your application has been sent.")
        scheduling.message_delayed_delete(info_msg)

        app = Application(applicant.id, voting_message.id, archive_message.id)
        db.applications[voting_message.id] = app

        # schedule automatic vote-clos
        job_id = scheduling.delayed_execute(app.check_votes, [True],
                timedelta(seconds=config.AUTO_VOTE_CLOSE_HOURS)) # TODO hours
        app.vote_close_job_id = job_id

        return app

    async def check_votes(self, force_close=False):
        voting_message = await config.voting_channel.fetch_message(
                self.voting_message_id)
        upvotes, downvotes = _count_votes(voting_message)

        # -1 so we don't count bot's reaction as vote
        accepted = upvotes - 1 >= config.APPROVE_THRESHOLD
        declined = downvotes - 1 >= config.DECLINE_THRESHOLD

        if force_close:
            accepted = upvotes > downvotes
            declined = not accepted

        # vote_close_job_id will be None if this is a scheduled vote_close
        if accepted or declined and self.vote_close_job_id is not None:
            # deschedule automatic vote-close
            scheduling.deschedule(self.vote_close_job_id)
            self.vote_close_job_id = None

        if accepted:
            await self.accept()
        elif declined:
            await self.decline()

    async def accept(self):
        applicant = config.archive_channel.guild.get_member(self.applicant_id)
        archive_message = await config.archive_channel.fetch_message(
                self.archive_message_id)
        voting_message = await config.voting_channel.fetch_message(
                self.voting_message_id)

        # remove app from DB
        del db.applications[voting_message.id]

        await voting_message.edit(content=f"{emojis.ARCHIVE_ACCEPTED} "
                                        f"Application has been accepted!")
        scheduling.message_delayed_delete(voting_message)
        await archive_message.add_reaction(emojis.ARCHIVE_ACCEPTED)
        applicant_role = archive_message.guild.get_role(config.APPLICANT_ROLE)
        await applicant.add_roles(applicant_role)
        await config.applicant_talk_channel.send(f"{applicant.mention} "
                f"Congratulations, your application has been accepted! "
                f"Please check {config.applicant_info_channel.mention} to "
                f"find out how to proceed.")

        # add as accepted user to DB
        pu = ProcessedUser(applicant.id, datetime.now(config.TIMEZONE), True)
        assert applicant.id not in db.denied
        assert applicant.id not in db.accepted
        db.accepted[applicant.id] = pu

    async def decline(self):
        applicant = config.archive_channel.guild.get_member(self.applicant_id)
        archive_message = await config.archive_channel.fetch_message(
                self.archive_message_id)
        voting_message = await config.voting_channel.fetch_message(
                self.voting_message_id)

        # remove app from DB
        del db.applications[voting_message.id]

        await voting_message.edit(content=f"{emojis.ARCHIVE_DENIED} "
                                        f"Application has been denied!")
        scheduling.message_delayed_delete(voting_message)

        # "Message Plague"
        await config.ambassador_channel.send(
                f"{config.ambassador_manager.mention} "
                f"Denied {applicant.mention}")

        await archive_message.add_reaction(emojis.ARCHIVE_DENIED)

        # add as declined user to DB
        cur_time = datetime.now(config.TIMEZONE)
        delta = timedelta(seconds=config.REAPPLY_COOLDOWN_DAYS) # TODO days
        reapply_time = cur_time + delta
        pu = ProcessedUser(applicant.id, cur_time, False, reapply_time)
        assert applicant.id not in db.denied
        assert applicant.id not in db.accepted
        db.denied[applicant.id] = pu
        # schedule cooldown wear-off
        scheduling.delayed_execute(ProcessedUser.delete, [pu], delta)

        # send DM
        try:
            time_str = reapply_time.strftime("%Y-%m-%d %H:%M:%S EST")
            await applicant.send(f"Hey {applicant.mention}, thank you for "
                f"applying to Fear and Terror. "
                f"Unfortunately, your application has been denied. "
                f"Feel free to re-apply in two weeks ({time_str}).\n\n"
                f"We don't collect statements from the individual voters but "
                f"the most common reasons for denying an application are "
                f"perceived lack of effort and being underage. "
                f"If you decide to re-apply, make sure to give thorough "
                f"responses to all the questions so we know you're serious "
                f"about joining FaT.")
        except discord.errors.Forbidden:
            await ambassador_channel.send(f"{ambassador_manager.mention}, "
                        f"{applicant.mention} did not receive the denied DM. "
                        f"He probably has the ambassador bot blocked.")

    async def freeze(self):
        # deschedule vote auto-close
        scheduling.deschedule(self.vote_close_job_id)
        self.vote_close_job_id = None

        self.frozen = True
        voting_message = await config.voting_channel.fetch_message(
                self.voting_message_id)
        await voting_message.clear_reactions()
        await voting_message.add_reaction(emojis.HOLD_H)
        await voting_message.add_reaction(emojis.HOLD_O)
        await voting_message.add_reaction(emojis.HOLD_L)
        await voting_message.add_reaction(emojis.HOLD_D)
        await voting_message.add_reaction(emojis.FORCE_ACCEPT)
        await voting_message.add_reaction(emojis.FORCE_DECLINE)


@dataclass
class ProcessedUser(persistent.Persistent):
    user_id : int
    processed_datetime : datetime
    accepted : bool = True

    # datetime after which the user can re-apply,
    # only valid if accepted is False
    reapply_datetime : datetime = None

    def delete(self):
        if self.accepted:
            del db.accepted[self.user_id]
        else:
            del db.denied[self.user_id]


def _count_votes(message):
    upvotes = 0
    downvotes = 0
    for r in message.reactions:
        if str(r.emoji) == emojis.UPVOTE:
            upvotes = r.count
        elif str(r.emoji) == emojis.DOWNVOTE:
            downvotes = r.count

    return (upvotes, downvotes)

