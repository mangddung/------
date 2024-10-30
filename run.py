'''
드롭다운 메뉴 선택시 해당곡 재생으로 바꾸기
'''

import asyncio
import discord
from discord.ext import commands
import yt_dlp
from utils.functions import *

ffmpeg_path = "C:\\ffmpeg\\bin\\ffmpeg.exe"  # FFmpeg 경로

config = read_config()
bot_prefix = config['BOT_PREFIX']
bot_token = config['BOT_TOKEN']
own_channel_id = int(config['CHANNEL_ID'])
panel_message_id = int(config['MESSAGE_ID'])

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.presences = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=bot_prefix, intents=intents)
    
play_queue = []
ffmpeg_source = []
ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
# yt-dlp로 유튜브 오디오 스트림을 가져옵니다.
ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extractaudio': True
}
#이벤트
#========================================================================================
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="테스트"))
    try:
        channel = bot.get_channel(own_channel_id)
        message = await channel.fetch_message(int(config['MESSAGE_ID']))
        await message.delete()
        embed, view = await create_panel_form(channel)
        panel_message = await channel.send(embed=embed, view=view)
        panel_message_id = panel_message.id
        config['MESSAGE_ID'] = panel_message_id
        write_config(config)
    except Exception as e:
        print(f"전용 채널 미스 또는 에러 : {e}")
    print("봇 준비완료")

@bot.event
async def on_guild_join(guild):
    print("서버 입장")
    #DB에 정보 등록

@bot.event
async def on_guild_remove(guild):
    print("서버 제거")

@bot.event
async def on_message(message):
    if message.author.bot:
        return 
    if message.content.startswith(bot_prefix):
        await bot.process_commands(message)
        return
    if message.channel.id == own_channel_id:
        await play(message)
        await message.delete()
        return

async def play(message):
    async def play_next_music(err, voice_client, panel_message):
        if err:
            print(err)
        else:
            del play_queue[0]
            if not play_queue:
                embed = discord.Embed (title="현재 재생중인 곡이 없어요.")
                await panel_message.edit(embed=embed)
                return
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(play_queue[0]['url'], download=False)
                url2 = info['url']
            embed, view = await create_panel_form(message.channel,play_queue)
            await panel_message.edit(embed=embed, view=view)
            voice_client.play(
                discord.FFmpegPCMAudio(executable=ffmpeg_path, source=url2, **ffmpeg_options),
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next_music(e, voice_client, panel_message), voice_client.loop)
            )    
    
    if message.author.voice is None:
        await message.channel.send("음성 채널에 먼저 접속해 주세요.")
        return
    
    voice_channel = message.author.voice.channel
    bot_voice_channel = message.guild.voice_client
    query = message.content.strip()

    #노래 이름 검색
    if not query.startswith("http"):
        video_info = get_video_url(query)
        url = video_info['url']
    elif query.startswith("https://www.youtube.com/watch?v="):
        video_info = get_video_info_from_url(query)
        url = video_info['url']
    else:
        message.channel.send("유튜브 링크가 아니네요.")
        return

    if not video_info:
        message.channel.send('영상 정보가 없어요.')
        return
    
    #보이스 채널 참가중 확인
    if not bot_voice_channel:
        voice_client = await voice_channel.connect()
    else:
        voice_client = bot_voice_channel

    video_info['requester'] = message.author.mention
    play_queue.append(video_info)
    panel_message = await message.channel.fetch_message(int(config['MESSAGE_ID']))
    embed, view = await create_panel_form(message.channel,play_queue)
    await panel_message.edit(embed=embed, view=view)
    if not voice_client.is_playing():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
        voice_client.play(
            discord.FFmpegPCMAudio(executable=ffmpeg_path, source=url2, **ffmpeg_options),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next_music(e, voice_client, panel_message), voice_client.loop)
        )

#명령어
#========================================================================================
@bot.command(name="t")
async def test(ctx):
    await create_panel_form(ctx)

@bot.command(name='전용채널')
@commands.has_permissions(administrator=True)
async def own_channel(ctx, name='우흥이-전용'):
    await ctx.guild.create_text_channel(name)
    own_channel_id = ctx.channel.id
    config['CHANNEL_ID'] = own_channel_id
    write_config(config)

@bot.command(name='패널생성')
@commands.has_permissions(administrator=True)
async def control_pannel(ctx):
    embed, view = await create_panel_form(ctx.channel)
    panel_message = await ctx.send(embed=embed, view=view)
    panel_message_id = panel_message.id
    config['MESSAGE_ID'] = panel_message_id
    write_config(config)
    await ctx.message.delete()

@bot.command(name="skip")
async def st(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        voice_client.stop()

@bot.command(name="pause")
async def pause(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        voice_client.pause()
    
@bot.command(name="resume")
async def unpause(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        voice_client.resume()

@bot.command(name="queue")
async def queue(ctx):
    template = "현재 대기열\n\n"
    for video_info in play_queue:
        template += f"제목: [{video_info['title']}]({video_info['url']})  재생 시간: {video_info['duration']}\n"
    embed = discord.Embed(description=template)
    await ctx.send(embed=embed)
bot.run(bot_token)