import os
import logging
import json
import math
import re
import random
import ast

from aiotg import Bot, chat
from database import db, text_search, text_delete

greeting = """
This is a Music bot!
"""

help = """
Simply type in keywords to search from the database.
Simply send music files to add to the database.
Command `/help` for help.
type:TYPE after keywords to restrict the type of result.
```Xiaoan type:flac```
```Xiaoan type:mp3``` ( mp3 was converted to mpeg in bot since mp3 is not a mime-type.)
```Xiaoan type:mpeg```
Seperate the artist and song by > .
```Xiaoan>The song of early-spring```
It also works great with type.
```Xiaoan>The song of early-spring type:flac```
Command /stats for the status of bot.
Command /music to return music files from this bot in a group chat.
```/music Xiaoan```
Reply `/add` to a music file in a group chat to add music file to the database.
Songs which was uploaded to the music channel will be sync to the database.
This bot supports inline mode, too.
"""

not_found = """
Data not found ._.
"""
bot = Bot(
    api_token=os.environ.get('API_TOKEN'),
    name=os.environ.get('BOT_NAME'),
    botan_token=os.environ.get("BOTAN_TOKEN")
)

logger = logging.getLogger("musicbot")
channel = bot.channel(os.environ.get('CHANNEL'))
logChannelID = os.environ.get("LOGCHN_ID")

async def getAdmin(ID=logChannelID):
    raw = ast.literal_eval(str(await bot.api_call("getChatAdministrators",chat_id=ID)))
    i=0
    adminDict = []
    while i < len(raw['result']):
        if 'last_name' in raw['result'][i]['user']:
            adminDict.append({
            'id':raw['result'][i]['user']['id'],
            'username':raw['result'][i]['user']['username'],
            'first_name':raw['result'][i]['user']['first_name'],
            'last_name':raw['result'][i]['user']['last_name']})
        else:
            adminDict.append({
            'id':raw['result'][i]['user']['id'],
            'username':raw['result'][i]['user']['username'],
            'first_name':raw['result'][i]['user']['first_name'],
            'last_name':''})
        i += 1
    return adminDict

async def isAdmin(ID):
    i=0
    adminList = await getAdmin()
    while i<len(adminList):
        if adminList[i]['id'] == ID:
            return 1
        i += 1
    return 0

@bot.handle("audio")
async def add_track(chat, audio):
    if "title" not in audio:
        await chat.send_text("Failed...No Id3 tag found :(")
        return

    if (str(chat.sender) == 'N/A'):
        sendervar = os.environ.get('CHANNEL_NAME')
    else:
        sendervar = str(chat.sender)
        matchedMusic = await db.tracks.find_one({"$and":[{'title': str(audio.get("title"))},{'performer': str(audio.get("performer"))}]})
    if (matchedMusic):
        if not int(audio.get("file_size")) > int(matchedMusic["file_size"]):
            await chat.send_text("Music already exists owo")
            logger.info("%s sent an existed music %s %s", sendervar, str(audio.get("performer")), str(audio.get("title")))
            await bot.send_message(logChannelID,sendervar + " sent an existed music " + str(audio.get("performer")) + " - " + str(audio.get("title")))
            return
        else:
            await text_delete(str(audio.get("performer"))+ '>' + str(audio.get("title")))
            doc = audio.copy()
            try:
                if (chat.sender["id"]):
                    doc["sender"] = chat.sender["id"]
            except:
                doc["sender"] = os.environ.get("CHANNEL")
            await db.tracks.insert(doc)
            await chat.send_text("New file is larger then the previous one, replaced!")
            logger.info("%s added a larger version %s %s", sendervar, str(audio.get("performer")), str(audio.get("title")))
            await bot.send_message(logChannelID,sendervar + " added a larger version " + str(audio.get("performer")) + " - " + str(audio.get("title")))
            return
    doc = audio.copy()
    try:
        if (chat.sender["id"]):
            doc["sender"] = chat.sender["id"]
    except:
        doc["sender"] = os.environ.get("CHANNEL")
        
    await db.tracks.insert(doc)
    logger.info("%s added %s %s", sendervar, doc.get("performer"), doc.get("title"))
    await bot.send_message(logChannelID,sendervar + " added " + str(doc.get("performer")) + " - " + str(doc.get("title")))
    if (sendervar != os.environ.get('CHANNEL_NAME')):
        await chat.send_text(sendervar + " added " + str(doc.get("performer")) + " - " + str(doc.get("title")) + " !")
    
@bot.command(r'/add')
async def add(chat, match):
    audio = chat.message['reply_to_message']['audio']
    if "title" not in audio:
        await chat.send_text("Failed...No Id3 tag found :(")
        return
    if (str(chat.sender) == 'N/A'):
        sendervar = os.environ.get('CHANNEL_NAME')
    else:
        sendervar = str(chat.sender)
    if (await db.tracks.find_one({ "file_id": audio["file_id"] })):
        await chat.send_text("The song has already been added to the database owo")
        logger.info("%s sent a existed music %s %s", sendervar, str(audio.get("performer")), str(audio.get("title")))
        await bot.send_message(logChannelID,sendervar + " sent a existed music " + str(audio.get("performer")) + " - " + str(audio.get("title")))
        return
    doc = audio.copy()
    try:
        if (chat.sender["id"]):
            doc["sender"] = chat.sender["id"]
    except:
        doc["sender"] = os.environ.get("CHANNEL")
        
    await db.tracks.insert(doc)
    logger.info("%s added %s %s", sendervar, doc.get("performer"), doc.get("title"))
    await bot.send_message(logChannelID,sendervar + " added " + str(doc.get("performer")) + " - " + str(doc.get("title")))
    if (sendervar != os.environ.get('CHANNEL_NAME')):
        await chat.send_text(sendervar + " added " + str(doc.get("performer")) + " - " + str(doc.get("title")) + " !")
    
@bot.command(r'/admin')
async def admin(chat, match):
    if not await isAdmin(chat.sender['id']):
        logger.info("%s requested admin list, rejected.", str(chat.sender))
        await bot.send_message(logChannelID, str(chat.sender) + ' requested admin list , rejected.')
        await chat.send_text("Access denied.")
        return
    else:
        logger.info("%s requested admin list", str(chat.sender))
        await bot.send_message(logChannelID, str(chat.sender) + ' requested admin list')
        raw = await getAdmin()
        adminStr=''
        i=0
        while i<len(raw):
            adminStr += raw[i]['first_name']+' '+raw[i]['last_name']+'\n'
            i += 1
        await chat.send_text(adminStr)

@bot.command(r'/delete (.+)')
async def delete(chat, match):
    text = match.group(1)
    if not await isAdmin(chat.sender['id']):
        logger.info("%s tried to delete '%s',rejected.", str(chat.sender), text)
        await bot.send_message(logChannelID, str(chat.sender) + ' tried to delete ' + text + ',rejected.')
        await chat.send_text("Access denied.")
        return
    else:
        msg = text.split(" type:")
        art = msg[0].split('>')
        i=0
        cursor = await text_delete(text)
        
        if (len(art) == 2):
            if (len(msg) == 2):
                logger.info("%s deleted %i %s music: %s - %s", chat.sender, cursor, msg[1].upper(), art[0], art[1])
                await bot.send_message(logChannelID,str(chat.sender) + " 刪除了 " + str(cursor) + ' 個 ' + msg[1].upper() + " 格式的 " + art[0] + "的" + art[1])
            elif (len(msg) == 1):
                logger.info("%s deleted %i %s - %s", chat.sender, cursor, art[0], art[1])
                await bot.send_message(logChannelID,str(chat.sender) + " 刪除了 " + str(cursor) + ' 個 '  + art[0] + "的" + art[1])
        elif (len(msg) == 2):
            logger.info("%s deleted %i %s music: %s", chat.sender, cursor, msg[1].upper(), msg[0])
            await bot.send_message(logChannelID,str(chat.sender) + " 刪除了 " + str(cursor) + ' 個 '  + msg[1].upper() + " 格式的 " + msg[0])
        elif (len(msg) == 1):
            logger.info("%s deleted %i %s", chat.sender, cursor, iq.query)
            await bot.send_message(logChannelID,str(chat.sender) + " 刪除了 " + str(cursor) + ' 個 '  + str(text))
        else:
            logger.info("element ERROR!")
            await bot.send_message(logChannelID,"element ERROR!")
            await bot.send_message(logChannelID,"(text , msg , len(msg)) = " + str(text) + " , " + str(msg) + " , " + str(len(msg)))
            logger.info("(text , msg , len(msg)) = (%s , %s , %d)", str(text), str(msg), len(msg))
@bot.command(r'@%s (.+)' % bot.name)
@bot.command(r'/music@%s (.+)' % bot.name)
@bot.command(r'/music (.+)')
def music(chat, match):
    return search_tracks(chat, match.group(1))

@bot.command(r'/me')
def whoami(chat, match):
    return chat.reply(chat.sender["id"])

@bot.command(r'\((\d+)/\d+\) Next page "(.+)"')
def more(chat, match):
    page = int(match.group(1))
    return search_tracks(chat, match.group(2), page)


@bot.default
def default(chat, message):
    return search_tracks(chat, message["text"])

@bot.inline
async def inline(iq):
    msg = iq.query.split(" type:")
    art = msg[0].split('>')
    cursor = await text_search(iq.query)
    if (len(art) == 2):
        if (len(msg) == 2):
            logger.info("%s searched %s music %s - %s", iq.sender, msg[1].upper(), art[0], art[1])
            await bot.send_message(logChannelID,str(iq.sender) + " searched " + msg[1].upper() + " music " + art[0] + " - " + art[1])
            results = [inline_result(iq.query, t) for t in await cursor.to_list(10)]
            await iq.answer(results)
        elif (len(msg) == 1):
            logger.info("%s searched %s - %s", iq.sender,  art[0], art[1])
            await bot.send_message(logChannelID,str(iq.sender) + " searched " + art[0] + " - " + art[1])
            results = [inline_result(iq.query, t) for t in await cursor.to_list(10)]
            await iq.answer(results)
    elif (len(msg) == 2):
        logger.info("%s searched %s music %s", iq.sender, msg[1].upper(), msg[0])
        await bot.send_message(logChannelID,str(iq.sender) + " searched " + msg[1].upper() + " music " + msg[0])
        results = [inline_result(iq.query, t) for t in await cursor.to_list(10)]
        await iq.answer(results)
    elif (len(msg) == 1):
        logger.info("%s searched %s", iq.sender, iq.query)
        await bot.send_message(logChannelID,str(iq.sender) + " searched " + str(iq.query))
        results = [inline_result(iq.query, t) for t in await cursor.to_list(10)]
        await iq.answer(results)
    else:
        logger.info("ERROR")
        await bot.send_message(logChannelID,"ERROR")
        await bot.send_message(logChannelID,"(iq.query , msg , len(msg)) = " + str(iq.query) + " , " + str(msg) + " , " + str(len(msg)))
        logger.info("(iq.query , msg , len(msg)) = (%s , %s , %d)", str(iq.query), str(msg), len(msg))


@bot.command(r'/music(@%s)?$' % bot.name)
def usage(chat, match):
    return chat.send_text(greeting, parse_mode='Markdown')


@bot.command(r'/start')
async def start(chat, match):
    tuid = chat.sender["id"]
    if not (await db.users.find_one({ "id": tuid })):
        logger.info("New user %s", chat.sender)
        await bot.send_message(logChannelID,"New user " + str(chat.sender))
        await db.users.insert(chat.sender.copy())

    await chat.send_text(greeting, parse_mode='Markdown')


@bot.command(r'/stop')
async def stop(chat, match):
    tuid = chat.sender["id"]
    await db.users.remove({ "id": tuid })

    logger.info("%s exited", chat.sender)
    await bot.send_message(logChannelID,str(chat.sender) + " exited")
    await chat.send_text("Goodbye! 😢")


@bot.command(r'/help')
def usage(chat, match):
    return chat.send_text(help, parse_mode='Markdown')


@bot.command(r'/stats')
async def stats(chat, match):
    count = await db.tracks.count()
    group = {
        "$group": {
            "_id": None,
            "size": {"$sum": "$file_size"}
        }
    }
    cursor = db.tracks.aggregate([group])
    aggr = await cursor.to_list(1)

    if len(aggr) == 0:
        return (await chat.send_text("Info not prepared yet!"))

    size = human_size(aggr[0]["size"])
    text = '%d songs, %s' % (count, size)

    return (await chat.send_text(text))


def human_size(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    rank = int((math.log10(nbytes)) / 3)
    rank = min(rank, len(suffixes) - 1)
    human = nbytes / (1024.0 ** rank)
    f = ('%.2f' % human).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[rank])


def send_track(chat, keyboard, track):
    return chat.send_audio(
        audio=track["file_id"],
        title=track.get("title"),
        performer=track.get("performer"),
        duration=track.get("duration"),
        reply_markup=json.dumps(keyboard)
    )


async def search_tracks(chat, query, page=1):
    if(str(chat.sender) != "N/A"):
        typel = query.split(" type:")
        if (query.find(">") != -1):
            art = typel[0].split('>')
            author = art[0]
            song = art[1]
            if (len(typel) == 1):
                logger.info("%s searched %s - %s", chat.sender, author, song)
                await bot.send_message(logChannelID,str(chat.sender) + " searched " + author + " - " + song)
            else:
                logger.info("%s searched %s music %s - %s", chat.sender, typel[1].upper(), author, song)
                await bot.send_message(logChannelID,str(chat.sender) + " searched " + typel[1].upper() + " music " + author + " - " + song)
        elif (len(typel) == 1):
            logger.info("%s searched %s", chat.sender, query)
            await bot.send_message(logChannelID,str(chat.sender) + " searched " + str(query))
        else:
            logger.info("%s searched %s music %s", chat.sender, typel[1].upper(), typel[0])
            await bot.send_message(logChannelID,str(chat.sender) + " searched " + typel[1].upper() + " music " + str(typel[0]))

        limit = 3
        offset = (page - 1) * limit

        tempCursor = await text_search(query)
        cursor = tempCursor.skip(offset).limit(limit)
        count = await cursor.count()
        results = await cursor.to_list(limit)

        if count == 0:
            await chat.send_text(not_found)
            return

        # Return single result if we have exact match for title and performer
        if results[0]['score'] > 2:
            limit = 1
            results = results[:1]

        newoff = offset + limit
        show_more = count > newoff

        if show_more:
            pages = math.ceil(count / limit)
            kb = [['(%d/%d) Next page "%s"' % (page+1, pages, query)]]
            keyboard = {
                "keyboard": kb,
                "resize_keyboard": True
            }
        else:
            keyboard = { "hide_keyboard": True }

        for track in results:
            await send_track(chat, keyboard, track)


def inline_result(query, track):
    global seed
    seed = query + str(random.randint(0,9999999))
    random.seed(query + str(random.randint(0,9999999)))
    noinline ={
        "message_text": track.get("performer", "") + ">" + track.get("title", "")
    }
    results = {
            "type": "document",
            "id": track["file_id"] + str(random.randint(0,99)),
            "document_file_id": track["file_id"],
            "title" : "{} - {}".format(track.get("performer", "Unknown Artist"),track.get("title", "Untitled")),
            "input_message_content" : noinline
            }
    return results