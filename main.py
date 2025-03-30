import configparser
import mysql.connector
import datetime
import time
import json
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get

config = configparser.ConfigParser()
config.read('config.ini')

databaseConnectionDetails = {
    'host': config['mainDB']['host'],
    'database': config['mainDB']['db'],
    'user': config['mainDB']['user'],
    'password': config['mainDB']['pass'],
    'collation': "utf8mb4_general_ci"
}

tempCache = {}

embedList = []
embed = discord.Embed(title="ALLOWLIST", color=0x60d1d8)
embedList.append(embed)
embed = discord.Embed(title="Käsiteltäväksi luokiteltava allowlist hakemus:", description="```- OOC\n   IRL Ikä?\n   Kerro itsestäsi roolipelaajana?\n- IC\n   Hahmokuvaus kolmannesta persoonasta kerrottuna.``` \n\n**HUOM 1!**\nHakemuksen maksimipituus on **1500 merkkiä**, mikäli hakemuksesi on tätä pidempi tullaan se hylkäämään automaattisesti.\n\n**HUOM 2!**\nHakemuksesi käsittelee anonyyminä ylläpidon valitsemat käsittelijät, joiden äänestystuloksista päätetään hakemuksesi lopputulos **(Ylläpito pidättää oikeuden vaikuttaa päätökseen erityistilanteessa.)** .\n\n**HUOM 3!**\nJos hakemuksesi hylätään, tulee sinun odottaa **24 tuntia (vuorokausi)** ennen uuden hakemuksen lähettämistä.\n\nLähetä hakemuksesi tälle kanavalle ja botti siirtää sen automaattisesti hakemuksen käsittelijöille.\n\n**Q** Mihin jätän allowlist hakemuksen?\n**A** Lähetä hakemuksesi tälle kanavalle ja se siirtyy automaattisesti käsittelijöille. Kaikki muut lähetystavat esim. yksityisviesti johtavat automaattiseen hylkyyn.", color=0x60d1d8)
embedList.append(embed)

#footer = "Tämä on virallinen viesti botilta Unknown#2796 (Testiversio)" - Otettu pois käytöstä oman vision takia.

async def canSendDMtoMember(member: discord.Member) -> bool:
    try:
        await member.send()
    except discord.Forbidden:
        return False
    except discord.HTTPException:
        return True
    
async def canSendDMtoUser(user: discord.User) -> bool:
    try:
        await user.send()
    except discord.Forbidden:
        return False
    except discord.HTTPException:
        return True

class PersistentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        super().__init__(command_prefix=".",intents=intents)

    async def setup_hook(self) -> None:
        self.add_view(VoteButtons())
        self.add_view(Buttons())
        # self.add_view(InterviewButtons()) - Suunniteltu haastatteluja varten, mutta poistettu käytöstä kesken kehityksen ja jätetty kesken
        self.add_view(GetRole())
        self.add_view(ConnectButtons())
        self.add_view(OpenTicketButton())
        self.add_view(ConfirmButtons())
        self.add_view(CloseButton())
        self.add_view(ReopenButton())
        

bot = PersistentBot()

@tasks.loop(seconds=60)  # Tarkista äänestykset minuutin välein
async def CheckApplys():
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

    cursor = databaseConnection.cursor()
    cursor.execute('SELECT discord, message, votes, enddate, status FROM applies WHERE enddate <= "' + str(now) + '";')
    status = 'inprogress'
    ended_applys = cursor.fetchall()
    for apply in ended_applys:
        discordid, message, votes, enddate, status = apply
        apply_votes = json.loads(votes) or {}
        upvotes = {}
        downvotes = {}
        for user in apply_votes:
            vote = apply_votes[user]            
            if vote == 'true':
                upvotes[len(upvotes)+1] = user
            elif vote == 'false':
                downvotes[len(downvotes)+1] = user
        if status != 'done':
            cursor.execute("SELECT value FROM settings WHERE `name` = 'appliesVote_channelId';")

            result = cursor.fetchone()
            channel_id = result and result[0] or False
            if channel_id:
                cursor.execute("SELECT value FROM settings WHERE `name` = 'appliesVote_maintenanceChannel';")

                result = cursor.fetchone()
                maintenanceChannelID = result and result[0] or False
                maintenanceChannel = bot.get_channel(int(maintenanceChannelID))
                channel = bot.get_channel(int(channel_id))
                msg = await channel.fetch_message(int(message))
                upvotesString = ''
                for upvote in upvotes:
                    upvotesString = upvotesString + '<@' + str(upvotes[upvote]) + '> \n'
                downvotesString = ''
                for downvote in downvotes:
                    downvotesString = downvotesString + '<@' + str(downvotes[downvote]) + '> \n'

                cursor.execute("SELECT value FROM settings WHERE `name` = 'applies_isInterview';")

                result = cursor.fetchone()
                isInterview = result and result[0] or False
                memberMsg = 'Allowlist hakemuksesi on hyväksytty!'
                newStatus = 'inprogress'
                success = False
                if len(upvotes) > len(downvotes):
                    newStatus = 'done'
                    memberMsg = 'Allowlist hakemuksesi on hyväksytty!'
                    success = True
                    if isInterview == 'true':
                        msg.embeds[0].title = 'Haastateltava hakemus'
                        memberMsg = 'Sinut on kutsuttu haastatteluun, kysele saatavilla olevia haastattelu aikoja discord kanavalla.'
                elif len(downvotes) > len(upvotes):
                    newStatus = 'done'
                    memberMsg = 'Allowlist hakemuksesi on hylätty! Voit lähettää uuden hakemuksen 24 tunnin päästä.'
                else:
                    newStatus = 'done'
                    memberMsg = 'Allowlist hakemuksesi on hylätty! Voit lähettää uuden hakemuksen 24 tunnin päästä.'

                memberMsg = memberMsg + '\n\n 👍: ' + str(len(upvotes)) + '\n 👎: ' + str(len(downvotes))

                successStr = 'Hylätty'
                if success:
                    successStr = 'Hyväksytty'
                embedDescription = 'Käyttäjän <@' + str(discordid.split(":", 1)[1]) + '> lähettämä hakemus' + msg.embeds[0].description.split(" äänestettävä hakemus \n", 1)[1].split("Äänestys päättyy:", 1)[0] + '\n Äänestys päättynyt: <t:' + str(int(time.mktime(enddate.timetuple()))) + ':R> \n\n Äänestyksen tulos: ' + successStr + ' \n\n 👍 (' + str(len(upvotes)) + '): \n' + upvotesString + '\n 👎 (' + str(len(downvotes)) + '): \n' + downvotesString
                msg.embeds[0].description = embedDescription
                msg.embeds[0].title = 'Hakemuksen käsittely päättynyt'
                
                guild = await bot.fetch_guild(config['discord']['guild'])
                member = await guild.fetch_member(discordid.split(":", 1)[1])
                if member:
                    cursor.execute("SELECT value FROM settings WHERE `name` = 'allowlist_role';")

                    result = cursor.fetchone()
                    roleId = result and result[0] or False
                    role = guild.get_role(int(roleId))
                    if newStatus == 'done':
                        userStatus = 'none'
                        if success:
                            userStatus = 'allowlisted'
                            await member.add_roles(role)
                        date_time = datetime.datetime.now()  + datetime.timedelta(days=1)
                        cursor.execute("UPDATE applies SET status = %s, waitdate = %s WHERE message = %s;", (newStatus, date_time, message))
                        databaseConnection.commit()
                        
                    cursor.execute("UPDATE registered_users SET status = %s WHERE discord = %s;", (userStatus, discordid))
                    databaseConnection.commit()
                    if await canSendDMtoMember(member):
                        embed = discord.Embed(title="Hakemus", description=memberMsg, color=0x60d1d8)
                        await member.send(embed=embed)
                newMsg = await maintenanceChannel.send(embeds=msg.embeds, view=isInterview == 'true' and InterviewButtons() or discord.ui.View())
                cursor.execute("UPDATE applies SET message = %s WHERE message = %s;", (newMsg.id, message))
                databaseConnection.commit()
                await msg.delete()
    databaseConnection.close()

@bot.event
async def on_ready():
    CheckApplys.start()
    await bot.tree.sync()

@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.tree.command(name="checkself",description="Tarkista oma tilanteesi")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
async def command(interaction:discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

    cursor = databaseConnection.cursor()
    cursor.execute("SELECT status FROM registered_users WHERE `discord` = 'discord:" + str(interaction.user.id) + "';")

    result = cursor.fetchone()
    status = result and result[0] or False
    databaseConnection.close()
    msg = status == 'admins' and 'Olet ylläpitäjä' or status == 'allowlisted' and 'Sinut on allowlistattu.' or status == 'processing' and 'Hakemuksesi on käsittelyssä!' or not status and 'Sinua ei ole rekisteröity tietokantaan.' or 'Sinua ei ole allowlistattu.'
    hasAllowlist = False
    if not interaction.user.roles:
        msg = msg + ' Sinulla ei näyttäisi olevan roolia, voit ottaa roolin painikkeesta "Ota rooli"!'
        hasAllowlist = True
    else:
        if not "allowlisted" in [y.name.lower() for y in interaction.user.roles] and status == 'allowlisted':
            msg = msg + ' Sinulla ei näyttäisi olevan roolia, voit ottaa roolin painikkeesta "Ota rooli"!'
            hasAllowlist = True
    embed = discord.Embed(title="STATUKSESI", description=msg, color=0x60d1d8)
    # embed.set_footer(text=footer)
    await interaction.followup.send(embed=embed, view=hasAllowlist and GetRole() or discord.ui.View())


async def getFivemCredentials(embed: discord.Embed):
    resp = ''
    inServer = False
    try: 
        resp = rq.get('http://' + str(config['fivem']['host']) + ':' + str(config['fivem']['port']) + '/players.json', timeout=1).json()
    except:
        resp = "Timed out"
    if resp != "Timed out":
        for player in resp:
            embed.add_field(name='name', value=player["name"], inline=False)
            for identifier in player["identifiers"]:
                if identifier == 'discord:' + str(member.id):
                    inServer = True
                    embed.add_field(name='Tila', value="Palvelimella", inline=False)
                    for identifier in player["identifiers"]:
                        embed.add_field(name=identifier.split(':', 1)[0], value=identifier.split(':', 1)[1], inline=False)
                if identifier.split(':', 1)[0] == "fivem":
                    resp = rq.get('https://policy-live.fivem.net/api/getUserInfo/' + identifier.split(':', 1)[1]).json()
                    embed.add_field(name='Cfx.re Forum Name', value=resp["name"], inline=False)
                    embed.add_field(name='Cfx.re Forum Link', value="https://forum.cfx.re/u/" + resp["name"], inline=False)
        if (not inServer):
            embed.add_field(name='Tila', value="Ei ole palvelimella", inline=False)
    else:
        embed.add_field(name='Tila', value="Palvelimeen ei saatu yhteyttä!", inline=False)

    return True

class Apply(discord.ui.Modal, title='Allowlist hakemus'):
    def __init__(self):
        super().__init__(timeout=None)
    age = discord.ui.TextInput(label='IRL Ikä?', custom_id="age", max_length=2, min_length=2)
    ooc = discord.ui.TextInput(label='OOC', style=discord.TextStyle.paragraph, custom_id="ooc", max_length=1800, min_length=2)
    ic = discord.ui.TextInput(label='IC', style=discord.TextStyle.paragraph, custom_id="ic", max_length=1800, min_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

        cursor = databaseConnection.cursor()
        cursor.execute("SELECT value FROM settings WHERE `name` = 'appliesVote_channelId';")

        result = cursor.fetchone()
        value = result and result[0] or False
        if value:
            date_time = datetime.datetime.now()  + datetime.timedelta(days=2)
            embed = discord.Embed(title="Lähetetty allowlist hakemus", description="Uusi anonyyminä äänestettävä hakemus \n\n\n **IRL Ikä?:** " + str(self.age) + "\n\n**OOC:** " + str(self.ooc) + "\n\n**IC:** " + str(self.ic) + "\n\n Äänestys päättyy: <t:" + str(int(time.mktime(date_time.timetuple()))) + ":R>", color=0x60d1d8)
            ownembed = discord.Embed(title="Hakemuksesi", description="Lähettämäsi hakemus \n\n**IRL Ikä?:** " + str(self.age) + "\n\n**OOC:** " + str(self.ooc) + "\n\n**IC:** " + str(self.ic), color=0x60d1d8)
            # embed.set_footer(text=footer)
            embed.timestamp = datetime.datetime.now()
            channel = bot.get_channel(int(value))
            msg = await channel.send(embed=embed, view=VoteButtons())
            
            databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

            cursor = databaseConnection.cursor()
            cursor.execute("INSERT INTO applies (discord, message, enddate) VALUES (%s, %s, %s)", ("discord:" + str(interaction.user.id), str(msg.id), date_time))

            databaseConnection.commit()

            cursor.execute("SELECT status FROM registered_users WHERE `discord` = 'discord:" + str(interaction.user.id) + "';")
            result = cursor.fetchone()
            status = result and result[0] or False

            if not status:
                cursor.execute("INSERT INTO registered_users (discord, status) VALUES (%s, %s)", ("discord:" + str(interaction.user.id), 'processing'))
                databaseConnection.commit()
            
            if status:
                cursor.execute("UPDATE registered_users SET status = %s WHERE discord = %s;", ('processing', "discord:" + str(interaction.user.id)))
                databaseConnection.commit()

            databaseConnection.close()
            memberMsg = 'Allowlist hakemuksesi on vastaanotettu! Käsittely voi kestää pisimmillään kaksi vuorokautta. Voit tarkastaa oman hakemuksesi tilanteen komennolla **/checkself** discord palvelimellamme!'
            
            await interaction.followup.send(memberMsg, ephemeral=True)
            
            ownembed2 = discord.Embed(title="Hakemus", description=memberMsg, color=0x60d1d8)
            await interaction.user.send(embeds=[ownembed, ownembed2])
        else:
            await interaction.followup.send('Epäonnistui! Äänestys kanavaa ei ole määritetty oikein.', ephemeral=True)

class Buttons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="sendapply", label="Lähetä hakemus", style=discord.ButtonStyle.primary, emoji="📨")
    async def button_callback(self, interaction, button):
        if not await canSendDMtoUser(interaction.user):
            return await interaction.response.send_message('Sinulla ei ole yksityisviestit auki. Hakemusta ei voi tehdä yksityisviestien ollessa kiinni.', ephemeral=True)

        databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
        
        cursor = databaseConnection.cursor()

        cursor.execute("SELECT status FROM registered_users WHERE `discord` = 'discord:" + str(interaction.user.id) + "';")
        result = cursor.fetchone()
        status = result and result[0] or False
        if not status:
            return await interaction.response.send_modal(Apply())
        if status:
            if status == 'processing':
                return await interaction.response.send_message('Hakemustasi käsitellään! Käsittelyssä kestää yleensä 2-3 päivää', ephemeral=True)
            if status == 'allowlisted':
                return await interaction.response.send_message('Olet jo allowlistattu!', ephemeral=True)
            if status == 'admins':
                return await interaction.response.send_message('Olet ylläpitäjä', ephemeral=True)
            
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('SELECT discord, message, votes, enddate, status, waitdate FROM applies WHERE discord = "discord:' + str(interaction.user.id) + '" AND waitdate >  "' + str(now) + '";')
            applys = cursor.fetchall()
            canApply = True
            for apply in applys:
                discordid, message, votes, enddate, status2, waitdate = apply
                canApply = False

            if not canApply:
                return await interaction.response.send_message('Viimesimmästä hylätystä hakemuksesta on alle 24 tuntia aikaa, odotathan hetken ennen uuden lähettämistä!', ephemeral=True)
            await interaction.response.send_modal(Apply())

class ConnectButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        button = discord.ui.Button(label='Yhdistä', style=discord.ButtonStyle.url, url='https://servers.unknownrp.fi')
        self.add_item(button)

class VoteButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="voteyes", style=discord.ButtonStyle.success, emoji="👍")
    async def voteyes(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.roles:
            return await interaction.followup.send('Et ole allowlist käsittelijä', ephemeral=True)
        else:
            if not "📋" in [y.name.lower() for y in interaction.user.roles]:
                return await interaction.followup.send('Et ole allowlist käsittelijä', ephemeral=True)
        databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

        cursor = databaseConnection.cursor()
        
        cursor.execute("SELECT votes FROM applies WHERE message = " + str(interaction.message.id) + ";")

        result = cursor.fetchone()
        value = result and result[0] or json.dumps({})
        votes = json.loads(value)
        userid = str(interaction.user.id)
        msg = 'Äänestys epäonnistui!'
        if votes.get(userid):
            votes[userid] = votes[userid]
        else:
            votes[userid] = None

        if votes[userid] != None:
            if votes[userid] == 'false':
                votes[userid] = 'true'
                cursor.execute("UPDATE applies SET votes = %s WHERE message = %s;", (json.dumps(votes), interaction.message.id))
                databaseConnection.commit()
                msg = 'Äänen vaihto onnistui!'
            elif votes[userid] == 'true':
                msg = 'Olet jo äänestänyt!'
        else:
            votes[userid] = 'true'
            cursor.execute("UPDATE applies SET votes = %s WHERE message = %s;", (json.dumps(votes), interaction.message.id))
            databaseConnection.commit()
            msg = 'Äänestys onnistui!'

        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(custom_id="voteno", style=discord.ButtonStyle.danger, emoji="👎")
    async def voteno(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.roles:
            return await interaction.followup.send('Et ole allowlist käsittelijä', ephemeral=True)
        else:
            if not "📋" in [y.name.lower() for y in interaction.user.roles]:
                return await interaction.followup.send('Et ole allowlist käsittelijä', ephemeral=True)
        databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

        cursor = databaseConnection.cursor()

        cursor.execute("SELECT votes FROM applies WHERE message = " + str(interaction.message.id) + ";")

        result = cursor.fetchone()
        value = result and result[0] or json.dumps({})
        votes = json.loads(value)
        userid = str(interaction.user.id)
        msg = 'Äänestys onnistui!'
        if votes.get(userid):
            votes[userid] = votes[userid]
        else:
            votes[userid] = None


        if votes[userid] != None:
            if votes[userid] == 'true':
                votes[userid] = 'false'
                cursor.execute("UPDATE applies SET votes = %s WHERE message = %s;", (json.dumps(votes), interaction.message.id))
                databaseConnection.commit()
                msg = 'Äänen vaihto onnistui!'
            elif votes[userid] == 'false':
                msg = 'Olet jo äänestänyt!'
        else:
            votes[userid] = 'false'
            cursor.execute("UPDATE applies SET votes = %s WHERE message = %s;", (json.dumps(votes), interaction.message.id))
            databaseConnection.commit()
            msg = 'Äänestys onnistui!'

        await interaction.followup.send(msg, ephemeral=True)

# class InterviewButtons(discord.ui.View): - Suunniteltu haastatteluja varten, mutta poistettu käytöstä kesken kehityksen ja jätetty kesken
#     def __init__(self):
#         super().__init__(timeout=None)

#     @discord.ui.button(custom_id="confirm", style=discord.ButtonStyle.success, emoji="✔️")
#     async def confirm(self, interaction, button):
#         print('test')

#     @discord.ui.button(custom_id="cancel", style=discord.ButtonStyle.danger, emoji="✖️")
#     async def cancel(self, interaction, button):
#         print('test')
        

class GetRole(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="get_role", label="Ota rooli", style=discord.ButtonStyle.secondary, emoji="🪪")
    async def get_role(self, interaction, button):
        guild = await bot.fetch_guild(config['discord']['guild'])
        member = await guild.fetch_member(interaction.user.id)

        databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

        cursor = databaseConnection.cursor()

        cursor.execute("SELECT value FROM settings WHERE `name` = 'allowlist_role';")

        result = cursor.fetchone()
        roleId = result and result[0] or False
        role = guild.get_role(int(roleId))
        await member.add_roles(role)
        await interaction.response.edit_message(embeds={}, content='Rooli annettu onnistuneesti!', view=discord.ui.View())


class OpenTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="open-ticket",
        placeholder = "Tiketin aihe",
        min_values = 1,
        max_values = 1,
        options = [
            discord.SelectOption(
                label="Pelaajan ilmiantaminen",
                description="Avaa tiketin sinun ja ylläpitäjien välille"
            ),
            discord.SelectOption(
                label="Palvelimen porttikielto",
                description="Avaa tiketin sinun ja ylläpitäjien kanssa, jotka käsittelevät porttikieltoja"
            ),
            discord.SelectOption(
                label="Hakemukset",
                description="Avaa tiketin sinun ja hakemuksista vastaavien kanssa"
            ),
            discord.SelectOption(
                label="Muu",
                description="Avaa yleisen tiketin sinun ja ylläpitäjien kanssa"
            )
        ]
    )
    async def select_callback(self, interaction, select): # the function called when the user is done selecting options
        await interaction.response.defer(ephemeral=True)
        msg = await interaction.followup.send(f"Haluatko avata tiketin?", view=ConfirmButtons(), ephemeral=True)
        tempCache[str(msg.id)] = select.values[0]

class ReopenButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="reopen-ticket", label="Uudelleen avaa", style=discord.ButtonStyle.success, emoji="🔓")
    async def reopen(self, interaction, button):
        await interaction.response.defer()
        databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

        cursor = databaseConnection.cursor()
        cursor.execute("SELECT value FROM settings WHERE `name` = 'tickets_openCategory';")
        result = cursor.fetchone()
        categoryId = result and result[0] or False

        channel = interaction.message.channel
        category = await bot.fetch_channel(categoryId)
        cursor.execute("SELECT user FROM tickets WHERE `channel` = '" + str(channel.id) + "';")
        result = cursor.fetchone()
        userId = result and result[0] or False
        user = await bot.fetch_user(userId)
        overwrite = discord.PermissionOverwrite()
        overwrite.read_messages = True
        await channel.set_permissions(user, overwrite=overwrite)
        await channel.edit(category=category)
        await interaction.message.edit(view=CloseButton())
        
class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="close-ticket", label="Sulje", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction, button):
        await interaction.response.defer()
        databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

        cursor = databaseConnection.cursor()
        cursor.execute("SELECT value FROM settings WHERE `name` = 'tickets_archivedCategory';")
        result = cursor.fetchone()
        categoryId = result and result[0] or False

        channel = interaction.message.channel
        category = await bot.fetch_channel(categoryId)
        
        guild = await bot.fetch_guild(config['discord']['guild'])
        for role in guild.roles:
            if role.name.lower() == 'moderaattori':
                ModerateRole = role
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ModerateRole: discord.PermissionOverwrite(read_messages=True),
        }
        await channel.edit(category=category, overwrites=overwrites)
        await interaction.message.edit(view=ReopenButton())

class ConfirmButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="yes", style=discord.ButtonStyle.success, emoji="👍")
    async def yes(self, interaction, button):
        await interaction.response.defer()
        databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
        if (tempCache and tempCache[str(interaction.message.id)]):
            threadPrefix = 'muu-'
            typeString = "muuhun"
            if (tempCache[str(interaction.message.id)] == "Pelaajan ilmiantaminen"):
                threadPrefix = 'ilmianto-'
                typeString = "pelaajaan"
            if (tempCache[str(interaction.message.id)] == "Palvelimen porttikielto"):
                threadPrefix = 'porttikielto-'
                typeString = "porttikieltoon"
            if (tempCache[str(interaction.message.id)] == "Hakemukset"):
                threadPrefix = 'hakemus-'
                typeString = "hakemukseen"
                
            cursor = databaseConnection.cursor()
            cursor.execute("SELECT value FROM settings WHERE `name` = 'tickets_openCategory';")
            result = cursor.fetchone()
            categoryId = result and result[0] or False
            guild = await bot.fetch_guild(config['discord']['guild'])
            categories = {}
            for category in await guild.fetch_channels():
                categories[str(category.id)] = category
            for role in guild.roles:
                if role.name.lower() == 'moderaattori':
                    ModerateRole = role
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, add_reactions=True, attach_files=True, read_message_history=True, send_messages=True, embed_links=True),
                ModerateRole: discord.PermissionOverwrite(read_messages=True),
            }
            channel = await categories[categoryId].create_text_channel(name = threadPrefix + interaction.user.name, overwrites=overwrites)
            
            embed = discord.Embed(title="Tiketti", description='<@' + str(interaction.user.id) + '>:n tiketti', color=0x60d1d8)
            
            await getFivemCredentials(embed)

            await channel.send(embed=embed, view=CloseButton())
            embed = discord.Embed(title="Tiketti", description='Avasit uuden tiketin: ' + channel.mention, color=0x60d1d8)
            databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

            cursor = databaseConnection.cursor()
            cursor.execute("INSERT INTO tickets (channel, user) VALUES (%s, %s)", (str(channel.id), interaction.user.id))

            databaseConnection.commit()
            
            databaseConnection.close()
            await interaction.edit_original_response(content="", embed=embed, view=discord.ui.View())
        else:
            await interaction.edit_original_response(content="Ei löytynyt interactiota.", view=discord.ui.View())

    @discord.ui.button(custom_id="no", style=discord.ButtonStyle.danger, emoji="👎")
    async def no(self, interaction, button):
        await interaction.response.defer()
        if (tempCache and tempCache[str(interaction.message.id)]):
            await interaction.edit_original_response(content="Peruutettu!", view=discord.ui.View())
        else:
            await interaction.edit_original_response(content="Ei löytynyt interactiota.", view=discord.ui.View())





@bot.tree.command(name="allowlistmsg",description="Lähetä allowlist viesti")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
async def command(interaction:discord.Interaction):
    await interaction.response.defer()
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
    cursor = databaseConnection.cursor()
    cursor.execute("SELECT value FROM settings WHERE `name` = 'applies_msgId';")
    msgquery = cursor.fetchone()
    cursor.execute("SELECT value FROM settings WHERE `name` = 'applies_channelId';")
    channelquery = cursor.fetchone()
    msg_id = msgquery and msgquery[0] or False
    channel_id = channelquery and channelquery[0] or False
    if msg_id and channel_id:
        channel = bot.get_channel(int(channel_id))
        msg = await channel.fetch_message(int(msg_id))
        await msg.delete()
    editedEmbedList = embedList[:]

    cursor.execute("SELECT value FROM settings WHERE `name` = 'applies_isOpen';")
    result = cursor.fetchone()
    value = result[0] == 'true' and True or False
    if value:
        embed = discord.Embed(title="<:customcheckmark:1282428829402660874> ALLOWLIST HAKEMUKSET AVOINNA! <:customcheckmark:1282428829402660874>", color=0x60d1d8)
        # embed.set_footer(text=footer)
    else:
        embed = discord.Embed(title="<:customxmark:1267443141275943004> ALLOWLIST HAKEMUKSET TOISTAISEKSI KIINNI! <:customxmark:1267443141275943004>", color=0xC41E3A)
        # embed.set_footer(text=footer)
    editedEmbedList.append(embed)
    msg = await interaction.followup.send(embeds=editedEmbedList, view=value and Buttons() or discord.ui.View(), ephemeral=False)
    
    cursor.execute("UPDATE settings SET value = " + str(msg.id) + " WHERE `name` = 'applies_msgId';")
    databaseConnection.commit()
    cursor.execute("UPDATE settings SET value = " + str(msg.channel.id) + " WHERE `name` = 'applies_channelId';")
    databaseConnection.commit()
    databaseConnection.close()


@bot.tree.command(name="open-applies",description="Sulje hakemukset")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
async def command(interaction:discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
    cursor = databaseConnection.cursor()
    cursor.execute("UPDATE settings SET value = 'true' WHERE `name` = 'applies_isOpen';")
    databaseConnection.commit()

    cursor.execute("SELECT value FROM settings WHERE `name` = 'applies_msgId';")
    msgquery = cursor.fetchone()
    cursor.execute("SELECT value FROM settings WHERE `name` = 'applies_channelId';")
    channelquery = cursor.fetchone()
    msg_id = msgquery and msgquery[0] or False
    channel_id = channelquery and channelquery[0] or False
    if msg_id and channel_id:
        channel = bot.get_channel(int(channel_id))
        msg = await channel.fetch_message(int(msg_id))
        editedEmbedList = embedList[:]

        embed = discord.Embed(title="<:customcheckmark:1282428829402660874> ALLOWLIST HAKEMUKSET AVOINNA! <:customcheckmark:1282428829402660874>", color=0x60d1d8)
        # embed.set_footer(text=footer)
        editedEmbedList.append(embed)
        await msg.edit(embeds=editedEmbedList, view=Buttons())
        await interaction.followup.send('Hakemukset avattu!', ephemeral=True)

    databaseConnection.close()

@bot.tree.command(name="close-applies",description="Sulje hakemukset")
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
async def command(interaction:discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
    cursor = databaseConnection.cursor()
    cursor.execute("UPDATE settings SET value = 'false' WHERE `name` = 'applies_isOpen';")
    databaseConnection.commit()

    cursor.execute("SELECT value FROM settings WHERE `name` = 'applies_msgId';")
    msgquery = cursor.fetchone()
    cursor.execute("SELECT value FROM settings WHERE `name` = 'applies_channelId';")
    channelquery = cursor.fetchone()
    msg_id = msgquery and msgquery[0] or False
    channel_id = channelquery and channelquery[0] or False
    if msg_id and channel_id:
        channel = bot.get_channel(int(channel_id))
        msg = await channel.fetch_message(int(msg_id))
        editedEmbedList = embedList[:]
        embed = discord.Embed(title="<:customxmark:1267443141275943004> ALLOWLIST HAKEMUKSET TOISTAISEKSI KIINNI! <:customxmark:1267443141275943004>", color=0xC41E3A)
        # embed.set_footer(text=footer)
        editedEmbedList.append(embed)
        await msg.edit(embeds=editedEmbedList, view=discord.ui.View())
        await interaction.followup.send('Hakemukset suljettu!', ephemeral=True)

    databaseConnection.close()

@bot.tree.command(name='check-apply', description='Tarkista hakemus')
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
@app_commands.describe(message='Message id')
async def checkApply(interaction: discord.Interaction, message: str):
    await interaction.response.defer(ephemeral=True)
    if "📋" in [y.name.lower() for y in interaction.user.roles]:
        return await interaction.followup.send('Sinulla ei ole oikeuksia tähän!', ephemeral=True)
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
    cursor = databaseConnection.cursor()
    cursor.execute("SELECT discord, votes FROM applies WHERE `message` = '" + message + "';")
    result = cursor.fetchone()
    discordid = result and result[0] or False
    votes = result and result[1] or False
    apply_votes = json.loads(votes) or {}
    upvotes = {}
    downvotes = {}
    for user in apply_votes:
        vote = apply_votes[user]            
        if vote == 'true':
            upvotes[len(upvotes)+1] = user
        elif vote == 'false':
            downvotes[len(downvotes)+1] = user

    upvotesString = ''
    for upvote in upvotes:
        upvotesString = upvotesString + '<@' + str(upvotes[upvote]) + '> \n'
    downvotesString = ''
    for downvote in downvotes:
        downvotesString = downvotesString + '<@' + str(downvotes[downvote]) + '> \n'

    voteString = '👍 (' + str(len(upvotes)) + '): \n' + upvotesString + '\n 👎 (' + str(len(downvotes)) + '): \n' + downvotesString

    await interaction.followup.send(f'Hakemuksen lähetti: <@{discordid.split(":", 1)[1]}> \n\n' + voteString, ephemeral=True)

@bot.tree.command(name='deny-apply', description='Suoraan hylkää hakemus')
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
@app_commands.describe(message='Message id')
@app_commands.describe(message='Reason')
async def denyApply(interaction: discord.Interaction, message: str, reason: str):
    await interaction.response.defer(ephemeral=True)
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)

    cursor = databaseConnection.cursor()
    cursor.execute('SELECT discord, votes, enddate, status FROM applies WHERE message = "' + str(message) + '";')
    status = 'inprogress'
    applyFetch = cursor.fetchone()
    apply = applyFetch and applyFetch[0] or False
    discordid = applyFetch[0]
    votes = applyFetch[1]
    enddate = applyFetch[2]
    status = applyFetch[3]
    apply_votes = json.loads(votes) or {}
    upvotes = {}
    downvotes = {}
    for user in apply_votes:
        vote = apply_votes[user]            
        if vote == 'true':
            upvotes[len(upvotes)+1] = user
        elif vote == 'false':
            downvotes[len(downvotes)+1] = user
    if status != 'done':
        cursor.execute("SELECT value FROM settings WHERE `name` = 'appliesVote_channelId';")

        result = cursor.fetchone()
        channel_id = result and result[0] or False
        if channel_id:
            cursor.execute("SELECT value FROM settings WHERE `name` = 'appliesVote_maintenanceChannel';")

            result = cursor.fetchone()
            maintenanceChannelID = result and result[0] or False
            maintenanceChannel = bot.get_channel(int(maintenanceChannelID))
            channel = bot.get_channel(int(channel_id))
            msg = await channel.fetch_message(int(message))
            embedDescription = 'Käyttäjän <@' + str(discordid.split(":", 1)[1]) + '> lähettämä hakemus' + msg.embeds[0].description.split(" äänestettävä hakemus \n", 1)[1].split("Äänestys päättyy:", 1)[0] + '\n Äänestys päättynyt: <t:' + str(int(time.mktime(enddate.timetuple()))) + ':R> \n\n Tämä hakemus on suoraan hylätty ylläpitäjän <@' + str(interaction.user.id) + '> toimesta syyllä: ' + str(reason)
            msg.embeds[0].description = embedDescription
            msg.embeds[0].title = 'Hakemuksen käsittely päättynyt'
            memberMsg = 'Allowlist hakemuksesi on hylätty ylläpidon toimesta! Hylkäämisen syy: ' + str(reason) + ', Voit lähettää uuden hakemuksen 24 tunnin kuluttua.'
            newStatus = 'done'
            success = False
            guild = await bot.fetch_guild(config['discord']['guild'])
            member = await guild.fetch_member(discordid.split(":", 1)[1])
            if member:
                userStatus = 'none'
                date_time = datetime.datetime.now()  + datetime.timedelta(days=1)
                cursor.execute("UPDATE applies SET status = %s, waitdate = %s WHERE message = %s;", (newStatus, date_time, message))
                databaseConnection.commit()
                        
                cursor.execute("UPDATE registered_users SET status = %s WHERE discord = %s;", (userStatus, discordid))
                databaseConnection.commit()
                if await canSendDMtoMember(member):
                    embed = discord.Embed(title="Hakemus", description=memberMsg, color=0x60d1d8)
                    await member.send(embed=embed)
            newMsg = await maintenanceChannel.send(embeds=msg.embeds)
            cursor.execute("UPDATE applies SET message = %s WHERE message = %s;", (newMsg.id, message))
            databaseConnection.commit()
            await msg.delete()
    
    await interaction.followup.send('Hakemus suoraan hylätty!', ephemeral=True)
    databaseConnection.close()

@bot.tree.command(name='scan-role', description='Aseta roolilla oleville tila')
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
@app_commands.describe(role='Role id')
@app_commands.describe(status='Status')
async def scanRole(interaction: discord.Interaction, role: discord.Role, status: str):
    await interaction.response.defer(ephemeral=True)
    empty = True
    for member in interaction.guild.members:
        if role in member.roles:
            databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
            cursor = databaseConnection.cursor()

            if status == 'beta':
                cursor.execute("SELECT beta FROM registered_users WHERE `discord` = 'discord:" + str(member.id) + "';")
                result = cursor.fetchone()
                beta = result and result[0] or False
                dataChanged = False
                if beta:
                    if beta == 'false':
                        cursor.execute("UPDATE registered_users SET beta = %s WHERE discord = %s;", ('true', "discord:" + str(member.id)))
                        databaseConnection.commit()
                        dataChanged = True
                else:
                    cursor.execute("INSERT INTO registered_users (discord, beta) VALUES (%s, %s)", ("discord:" + str(member.id), 'true'))
                    databaseConnection.commit()
                    dataChanged = True
                if dataChanged:
                    messageString = 'Sinun beta roolisi on synkronoitu tietokannan kanssa.'
                    if await canSendDMtoMember(member):
                        embed = discord.Embed(title="Roolisynkronointi", description=messageString, color=0x60d1d8)
                        await member.send(embed=embed)
                empty = False
            else:
                cursor.execute("SELECT status FROM registered_users WHERE `discord` = 'discord:" + str(member.id) + "';")

                result = cursor.fetchone()
                statusonSQL = result and result[0] or False
                dataChanged = False
                if statusonSQL:
                    if not statusonSQL == status:
                        cursor.execute("UPDATE registered_users SET status = %s WHERE discord = %s;", (status, "discord:" + str(member.id)))
                        databaseConnection.commit()
                        dataChanged = True
                else:
                    cursor.execute("INSERT INTO registered_users (discord, status) VALUES (%s, %s)", ("discord:" + str(member.id), status))
                    databaseConnection.commit()
                    dataChanged = True
                if dataChanged:
                    messageString = 'Sinun roolisi (' + str(role.name) + ') on synkronoitu tietokannan kanssa rooliin (' + str(status) + ').'

                    if status == 'allowlisted':
                        messageString = 'Sinulle on annettu allowlist automaattisesti'
                        guild = await bot.fetch_guild(config['discord']['guild'])
                        cursor.execute("SELECT value FROM settings WHERE `name` = 'allowlist_role';")

                        result = cursor.fetchone()
                        roleId = result and result[0] or False
                        Role = guild.get_role(int(roleId))
                        await member.add_roles(Role)
                        if role.name == '📋':
                            messageString = 'Sinulle on annettu allowlist automaattisesti, koska olet allowlist käsittelijä!'

                    if await canSendDMtoMember(member):
                        embed = discord.Embed(title="Roolisynkronointi", description=messageString, color=0x60d1d8)
                        await member.send(embed=embed)
                empty = False
    if empty:
        return await interaction.followup.send("Ketään ei ole roolilla {}".format(role.mention), ephemeral=True)

    await interaction.followup.send('Scan tehty!', ephemeral=True)
    databaseConnection.close()


@bot.tree.command(name='connectionmsg', description='Yhdistä viesti')
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
async def getLink(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="Palvelimelle yhdistäminen", description="Yhdistä tästä palvelimelle painamalla painiketta ja sitten tekstistä", color=0x60d1d8)
            
    await interaction.followup.send(embed=embed, view=ConnectButtons())

@bot.tree.command(name='ticketmsg', description='Tiketti viesti')
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
async def ticketmsg(interaction: discord.Interaction):
    await interaction.response.defer()
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
    cursor = databaseConnection.cursor()
    cursor.execute("SELECT value FROM settings WHERE `name` = 'tickets_ticketPanelMessage';")
    msgquery = cursor.fetchone()
    cursor.execute("SELECT value FROM settings WHERE `name` = 'tickets_ticketPanelChannel';")
    channelquery = cursor.fetchone()
    msg_id = msgquery and msgquery[0] or False
    channel_id = channelquery and channelquery[0] or False
    if msg_id and channel_id:
        channel = bot.get_channel(int(channel_id))
        msg = await channel.fetch_message(int(msg_id))
        await msg.delete()
    embed = discord.Embed(title="Tiketit", description="**Valitsemalla aiheen sinulle avautuu yksityinen kanava asian käsiteltäviksi, ainoastaan sinä, ylläpitäjät, valvojat näkee tickettisi**", color=0x60d1d8)
            
    msg = await interaction.followup.send(embed=embed, view=OpenTicketButton())
    
    cursor.execute("UPDATE settings SET value = " + str(msg.id) + " WHERE `name` = 'tickets_ticketPanelMessage';")
    databaseConnection.commit()
    cursor.execute("UPDATE settings SET value = " + str(msg.channel.id) + " WHERE `name` = 'tickets_ticketPanelChannel';")
    databaseConnection.commit()
    databaseConnection.close()


@bot.tree.command(name='open-ticket', description='Avaa tiketti ylläpitäjänä toiselle')
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
@app_commands.describe(member='Käyttäjä maininta')
async def openticket(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
    cursor = databaseConnection.cursor()
    cursor.execute("SELECT value FROM settings WHERE `name` = 'tickets_openCategory';")
    result = cursor.fetchone()
    categoryId = result and result[0] or False
    guild = await bot.fetch_guild(config['discord']['guild'])
    categories = {}
    for category in await guild.fetch_channels():
        categories[str(category.id)] = category
    for role in guild.roles:
        if role.name.lower() == 'moderaattori':
            ModerateRole = role
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True),
        ModerateRole: discord.PermissionOverwrite(read_messages=True),
    }
    channel = await categories[categoryId].create_text_channel(name = 'ylläpito-' + member.name, overwrites=overwrites)
            
    embed = discord.Embed(title="Tiketti", description='<@' + str(member.id) + '>:n tiketti', color=0x60d1d8)
    
    await getFivemCredentials(embed)

    await channel.send(embed=embed, view=CloseButton())
    embed = discord.Embed(title="Tiketti", description='Avasit uuden tiketin: ' + channel.mention, color=0x60d1d8)

    cursor = databaseConnection.cursor()
    cursor.execute("INSERT INTO tickets (channel, user) VALUES (%s, %s)", (str(channel.id), member.id))

    databaseConnection.commit()
            
    databaseConnection.close()
    await interaction.followup.send(embed=embed)

@bot.tree.command(name='add-user', description='Lisää käyttäjä tickettiin')
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
@app_commands.describe(member='Käyttäjä maininta')
async def openticket(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
    cursor = databaseConnection.cursor()
    cursor.execute("SELECT * FROM tickets WHERE `channel` = '" + str(interaction.channel.id) + "';")
    result = cursor.fetchone()
    channel = result and result[0] or False
    if not channel:
        return await interaction.followup.send('Tuntematon vuorovaikutus!')
    guild = await bot.fetch_guild(config['discord']['guild'])
    categories = {}
    for category in await guild.fetch_channels():
        categories[str(category.id)] = category
    for role in guild.roles:
        if role.name.lower() == 'moderaattori':
            ModerateRole = role
    
    overwrite = discord.PermissionOverwrite()
    overwrite.read_messages = True
    await interaction.channel.set_permissions(member, overwrite=overwrite)
    embed = discord.Embed(title="Tiketti", description='<@' + str(member.id) + '> lisätty tikettiin', color=0x60d1d8)
    resp = False
    await getFivemCredentials(embed)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name='remove-user', description='Poista käyttäjä ticketistä')
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
@app_commands.describe(member='Käyttäjä maininta')
async def openticket(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()
    databaseConnection = mysql.connector.connect(**databaseConnectionDetails)
    cursor = databaseConnection.cursor()
    cursor.execute("SELECT * FROM tickets WHERE `channel` = '" + str(interaction.channel.id) + "';")
    result = cursor.fetchone()
    channel = result and result[0] or False
    if not channel:
        return await interaction.followup.send('Tuntematon vuorovaikutus!')
    guild = await bot.fetch_guild(config['discord']['guild'])
    categories = {}
    for category in await guild.fetch_channels():
        categories[str(category.id)] = category
    for role in guild.roles:
        if role.name.lower() == 'moderaattori':
            ModerateRole = role
    
    await interaction.channel.set_permissions(member, overwrite=None)
    embed = discord.Embed(title="Tiketti", description='<@' + str(member.id) + '> poistettiin tiketistä', color=0x60d1d8)
    
    await interaction.followup.send(embed=embed)


bot.run(config['discord']['token'])