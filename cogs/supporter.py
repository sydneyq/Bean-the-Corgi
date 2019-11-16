import discord
from discord.ext import commands
from discord.utils import get
from .meta import Meta
from database import Database
import secret
import json
import os
import asyncio

class Support(commands.Cog):

    def __init__(self, client, database, meta):
        self.client = client
        self.dbConnection = database
        self.meta = meta

        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, 'docs/store.json')
        filename2 = os.path.join(dirname, 'docs/emojis.json')
        filename3 = os.path.join(dirname, 'docs/ids.json')
        filename4 = os.path.join(dirname, 'docs/supportersettings.json')
        filename5 = os.path.join(dirname, 'docs/topics.json')

        with open(filename) as json_file:
            self.store = json.load(json_file)

        with open(filename2) as json_file:
            self.emojis = json.load(json_file)

        with open(filename3) as json_file:
            self.ids = json.load(json_file)

        with open(filename4) as json_file:
            self.settings = json.load(json_file)

        with open(filename5) as json_file:
            self.topics = json.load(json_file)

    def getSupporterProfile(self, member: discord.Member = None):
        if member is None:
            return

        id = member.id

        profile = self.dbConnection.findSupporterProfile({"id": id})
        if profile is None:
            self.dbConnection.insertSupporterProfile({'id': id, 'active':True, 'allows_dm':True, 'allows_public':True, 'nsfw': False, 'ping_offline': True, 'ping_topics_only': False, 'allows_all_topics': True, 'topics': [], 'badges':[], 'helppts': 0})
            profile = self.dbConnection.findSupporterProfile({"id": id})

        return profile

    def getHelpPoints(self, member: discord.Member):
        user = self.meta.getProfile(member)
        return user['helped']

    def getSupporterBadges(self, member: discord.Member):
        user = self.meta.getProfile(member)

        str = ''
        if (self.meta.isCertified(member)):
            str = str + self.emojis['Certified']
        if user['helped'] >= 10:
            str = str + self.emojis['HelpPts10'] + ' '
            if user['helped'] >= 20:
                str = str + self.emojis['HelpPts20'] + ' '
                if user['helped'] >= 30:
                    str = str + self.emojis['HelpPts30'] + ' '
        return str

    def toggleSetting(self, member: discord.Member, setting):
        supporter = self.getSupporterProfile(member)
        val = supporter[setting]
        self.dbConnection.updateSupporterProfile({"id": member.id}, {"$set": {setting: val}})
        return True

    def embedTopics(self):
        desc = ''
        for topic in self.topics:
            desc += f"\n**{topic['id']}:** {topic['name']}"

        embed = discord.Embed(
            title = 'Toggle a topic by using `+ttopic [topicID]`.',
            description = desc,
            color = discord.Color.teal()
        )
        return embed

    #support-ticket reset
    @commands.command(aliases=['sp', 'listenerprofile', 'lp', 'supportprofile'])
    async def supporterprofile(self, ctx, other: discord.Member = None):
        if other == None:
            id = ctx.author.id
            member = ctx.author
        else:
            id = other.id
            member = other

        supporter = self.getSupporterProfile(member)

        color = discord.Color.teal()
        if (self.meta.isCertified(member)):
            color = discord.Color.gold()

        embed = discord.Embed(
            title = member.name + '\'s Supporter Profile',
            color = color
        )
        embed.set_thumbnail(url = member.avatar_url)
        embed.set_footer(text = 'You can change your Supporter settings by using "+sset".', icon_url = 'https://media.discordapp.net/attachments/591611902459641856/593267453363224588/Bean_Icon.png')

        #Help Pts
        embed.add_field(name=self.emojis['HelpPoint'] + " Help Points", value='`' + str(self.getHelpPoints(member)) + '`', inline=True)

        #Acknowledgements
        badges = self.getSupporterBadges(member)

        numBadges = 0
        if badges == '':
            badges = 'No badges yet.'
        else:
            numBadges = badges.count('<')
        embed.add_field(name="Support Badges (`" + str(numBadges) + "`)", value=badges, inline=True)

        #Options
        op = ''
        if (supporter['active']):
            op += f"**Allows NSFW topics:** {supporter['nsfw']}"
            op += f"\n**Allows Support DMs:** {supporter['allows_dm']}"
            op += f"\n**Allows Support Tickets:** {supporter['allows_public']}"
            op += f"\n**Can be pinged while offline:** {supporter['ping_offline']}"
            op += f"\n**Ping for Topics only:** {supporter['ping_topics_only']}"
            if not(supporter['allows_all_topics']):
                op += f"\n**Topics:** {supporter['topics']}"
            else:
                op += f"\n**Topics:** All"
        else:
            op = 'Not currently open to supporting.'
        embed.add_field(name='Settings', value=op, inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=['ssettings', 'sset'])
    async def supportersettings(self, ctx):
        embed = discord.Embed(
            title = 'Which setting would you like to change?',
            description = '🔰 - Active\n⚠ - NSFW\n💖 - Allow Support DMs\n💞 - Allow Support Tickets\n🔔 - Ping Offline\n📌 - Ping Topics Only\n🦋 - Topics\n⛔ - Cancel',
            color = discord.Color.teal()
        )
        msg = await ctx.send(embed = embed)

        for setting in self.settings:
            await msg.add_reaction(setting['symbol'])
        await msg.add_reaction('⛔')

        emoji = ''

        def check(reaction, user):
            nonlocal emoji
            emoji = str(reaction.emoji)
            reactions = ['🔰', '⚠', '💖', '💞', '🔔', '📌', '🦋', '⛔']
            return user == ctx.author and (str(reaction.emoji) in reactions)

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send('Settings toggle timed out.')
        else:
            if emoji == '⛔':
                embed = discord.Embed(
                    title = 'Settings toggle canceled.',
                    color = discord.Color.teal()
                )
                await ctx.send(embed = embed)
                return

            s = ''
            for setting in self.settings:
                if emoji == setting['symbol']:
                    s = setting['var']

            if s != 'topics':
                self.toggleSetting(ctx.author, s)
                await ctx.send(embed = self.meta.embedDone())
                return
            else:
                await ctx.send(embed = self.embedTopics())
                return
        return

    @commands.command()
    async def topics(self, ctx):
        await ctx.send(embed = self.embedTopics())
        return

    @commands.command(aliases=['ttopic', 'addtopic', 'removetopic'])
    async def toggletopic(self, ctx, t_id:int):
        topic = ''
        for t in self.topics:
            if t['id'] == t_id:
                topic = t

        if (topic == ''):
            await ctx.send(embed = self.meta.embedOops())
            return

        if t_id == 0:
            self.toggleSetting(ctx.author, 'allows_all_topics')
            await ctx.send(embed = self.meta.embedDone())
            return

        supporter = self.getSupporterProfile(ctx.author)
        supporter_topics = supporter['topics']

        if topic['name'] in supporter_topics:
            supporter_topics.remove(topic['name'])
        else:
            supporter_topics.append(topic['name'])
            supporter_topics = sorted(supporter_topics)

        self.dbConnection.updateSupporterProfile({"id": ctx.author.id}, {"$set": {'topics': supporter_topics}})
        return

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        id = member.id
        user = self.meta.getProfile(member)
        self.dbConnection.removeProfile({"id": id})

def setup(client):
    database_connection = Database()
    meta_class = Meta(database_connection)
    client.add_cog(Support(client, database_connection, meta_class))
