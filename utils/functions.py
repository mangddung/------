from youtubesearchpython import VideosSearch, Video
import discord
from discord.ext import commands
from datetime import timedelta

search_priority = [
    # "가사",
    # "lyrics"
]

search_filter = [
    # "1시간",
    # "1 hour",
    # "10시간",
    # "10 hour"
]

panel_message_list = {
    'resume' : "▶ 재생",
    'pause' : "∥ 중지",
    'skip' : "■ 스킵"
}

def get_video_url(query,search_count=1):
    # 비디오 검색
    search = VideosSearch(query, limit=search_count, region = 'KR')  # limit 검색 수
    results = search.result()
    video_data = []
    for index in range(search_count):
        if results['result']:
            video_info = results['result'][index]
            video_title = video_info['title']
            thumbnails_count = (len(video_info['thumbnails']))
            video_thumbnail = video_info['thumbnails'][thumbnails_count-1]['url']
            title_lower = video_title.lower()
            video_url = video_info['link']
            video_duration = video_info['duration']
            video = {
                'title': video_title,
                'url': video_url,
                'duration': video_duration,
                'thumbnail' : video_thumbnail
            }
            if any (word.lower() in title_lower for word in search_priority):
                video_data.insert(0,video)
            else:
                video_data.append(video)
    return video_data[0]

def get_video_info_from_url(url):
    video_info = Video.getInfo(url)
    video_title = video_info['title']
    video_url = video_info['link']
    thumbnails_count = (len(video_info['thumbnails']))
    video_thumbnail = video_info['thumbnails'][thumbnails_count-1]['url']

    #초로 나오는 데이터 가공
    video_duration_seconds = int(video_info['duration']['secondsText'])
    time_delta = timedelta(seconds=video_duration_seconds)
    hours, remainder = divmod(time_delta.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_data = [int(hours),int(minutes),int(seconds)]
    video_duration = ":".join([str(time) for time in duration_data if time > 0])

    video = {
        'title': video_title,
        'url': video_url,
        'duration': video_duration,
        'thumbnail' : video_thumbnail
        }
    print(video)
    return video

async def create_panel_form(channel):
    view = discord.ui.View()
    # 버튼 생성
    play_btn = discord.ui.Button(label=panel_message_list['pause'], style=discord.ButtonStyle.secondary)
    skip_btn = discord.ui.Button(label=panel_message_list['skip'], style=discord.ButtonStyle.secondary)

    # 중지, 재생 버튼
    async def play_btn_callback(interaction):
        #재생
        if play_btn.label == panel_message_list['resume']:
            voice_client = channel.guild.voice_client
            if voice_client:
                voice_client.resume()
                play_btn.label = panel_message_list['pause']
                await interaction.response.edit_message(content="곡을 재생합니다.", view=view)
        #중지
        else:
            voice_client = channel.guild.voice_client
            if voice_client:
                voice_client.pause()
                play_btn.label = panel_message_list['resume']
                await interaction.response.edit_message(content="곡을 중지합니다.", view=view)

    # 스킵 버튼
    async def skip_btn_callback(interaction):
        voice_client = channel.guild.voice_client
        if voice_client:
            voice_client.stop()
            await interaction.response.edit_message(content="곡이 스킵되었습니다.", view=view)

    play_btn.callback = play_btn_callback  # 중지, 재생 버튼
    skip_btn.callback = skip_btn_callback  # 스킵 버튼

    # 버튼을 포함한 뷰 생성
    view.add_item(play_btn)
    view.add_item(skip_btn)
    
    embed = discord.Embed (
        title="현재 재생중인 곡이 없어요."
    )
    interact = await channel.send(embed=embed, view=view)

    return interact.id

def read_config(filename='config.txt'):
    config = {}
    with open(filename, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            config[key.strip()] = value.strip()
    return config

def write_config(config, filename='config.txt'):
    with open(filename, 'w') as file:
        for key, value in config.items():
            file.write(f"{key}={value}\n")

def playing_panel_form(video_info, requester):
    embed = discord.Embed(
        title = video_info['title'],
        url = video_info['url'],
        description="",
        color=discord.Color.default()
    )
    embed.set_image(url=video_info['thumbnail'])
    embed.add_field(name="요청자", value=requester, inline=True)
    embed.add_field(name="영상 길이", value=video_info['duration'], inline=True)

    return embed