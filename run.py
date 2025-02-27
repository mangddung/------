'''
전체곡 반복, 한 곡 반복, 플레이리스트
기능 제작 예정
대기열 곡 삭제 기능
'''

import asyncio
import discord
from discord.ext import commands
import yt_dlp
from utils.functions import *

# ffmpeg_path = "C:\\ffmpeg\\bin\\ffmpeg.exe"  # FFmpeg 경로
ffmpeg_path = 'ffmpeg'

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
    await bot.change_presence(activity=discord.Game(name="작동"))
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
        print(f"패널 메세지 재생성 실패 : {e}")
    print("봇 준비완료")

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

@bot.event
async def on_voice_state_update(member, before, after):
    if bot.voice_clients:  # 봇이 음성 채널에 연결되어 있는지 확인
        voice_channel = bot.voice_clients[0].channel  # 봇이 연결된 음성 채널 객체 가져오기
        if voice_channel: # voice_channel이 None이 아닌지 확인 (봇이 연결이 끊어졌을 경우를 대비)
            members_in_channel = voice_channel.members  # 채널에 있는 멤버 목록 가져오기
            member_count = 0
            for member in members_in_channel:
                if not member.bot:
                    member_count += 1
            if member_count == 0:
                await bot.voice_clients[0].disconnect()

async def play(message):
    async def play_next_music(err, voice_client, panel_message):
        if err:
            print(err)
        else:
            del play_queue[0]
            if not play_queue:
                embed = discord.Embed (title="현재 재생중인 곡이 없어요.")
                await panel_message.edit(embed=embed)
                async def leave_channel_after_delay():
                    await asyncio.sleep(600)  # 5분 (300초) 대기
                    if not play_queue:  # 5분 후에도 대기열이 비어 있으면 실행
                        voice_client = message.guild.voice_client
                        if voice_client:
                            await voice_client.disconnect()
                            notice_message = await panel_message.channel.send("재생 대기열이 비어 있어 음성 채널에서 나갔어요.")
                            await notice_message.delete(delay=5)
                asyncio.create_task(leave_channel_after_delay())
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
        result_message = await message.channel.send(f"{video_info['title']}을 재생합니다.")
        await result_message.delete(delay=3)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
        voice_client.play(
            discord.FFmpegPCMAudio(executable=ffmpeg_path, source=url2, **ffmpeg_options),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next_music(e, voice_client, panel_message), voice_client.loop)
        )
    else:
        result_message = await message.channel.send(f"{video_info['title']}을 대기열에 등록합니다.")
        await result_message.delete(delay=3)

#명령어
#========================================================================================
@bot.command(name='패널생성')
@commands.has_permissions(administrator=True)
async def control_pannel(ctx):
    try:
        global panel_message_id
        global own_channel_id
        embed, view = await create_panel_form(ctx.channel)
        panel_message = await ctx.send(embed=embed, view=view)
        panel_message_id = panel_message.id
        own_channel_id = ctx.channel.id
        config['CHANNEL_ID'] = own_channel_id
        config['MESSAGE_ID'] = panel_message_id
        write_config(config)
    except:
        await ctx.send("패널 생성 실패")
    await ctx.message.delete()

bot.run(bot_token)