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
    'skip' : "▶| 스킵"
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
    return video

async def create_panel_form(channel,play_queue = []):
    view = discord.ui.View()
    # 버튼 생성
    play_btn = discord.ui.Button(label=panel_message_list['pause'], style=discord.ButtonStyle.secondary)
    skip_btn = discord.ui.Button(label=panel_message_list['skip'], style=discord.ButtonStyle.secondary)
    if play_queue:
        if len(play_queue) > 1:
            options = []
            for idx, music in enumerate(play_queue[1:], start=1):
                member = channel.guild.get_member(int(music['requester'].strip("<@!>")))
                requester_nick = member.nick if member.nick else "Unknown"
                options.append(discord.SelectOption(label=music['title'], description=f"요청자: {requester_nick}, 영상 길이: {music['duration']}", value=idx))
            placeholder = f"다음 노래가 {len(play_queue)-1}개 있어요"
        else: 
            options = [discord.SelectOption(label="없어요."),]
            placeholder = "다음 노래가 없어요."
        embed = playing_embed_form(play_queue[0])
    else:
        embed = discord.Embed (title="재생중인 곡이 없어요.")
        options = [discord.SelectOption(label="없어요."),]
        placeholder = "다음 노래가 없어요."
    queue_dropdown = discord.ui.Select(placeholder=placeholder, options=options, min_values=1, max_values=1) #다음곡 선택 재생 기능 만들때  max_value바꾸기

    # 중지, 재생 버튼
    async def play_btn_callback(interaction):
        voice_client = channel.guild.voice_client
        if not voice_client:
            await interaction.response.send_message("음성 채널에 접속해 주세요.", ephemeral=True)
            return
        if play_btn.label == panel_message_list['resume']:
            voice_client.resume()
            play_btn.label = panel_message_list['pause']
            await interaction.response.edit_message(content="곡을 재생합니다.", view=view)
        else:
            voice_client.pause()
            play_btn.label = panel_message_list['resume']
            await interaction.response.edit_message(content="곡을 중지합니다.", view=view)

    # 스킵 버튼
    async def skip_btn_callback(interaction):
        voice_client = channel.guild.voice_client
        if voice_client:
            voice_client.stop()
            #스킵 한 후 다음 곡 여부 확인해서 패널 업데이트
            await interaction.response.edit_message(content="곡이 스킵되었습니다.", view=view)

    #대기열 목록
    async def queue_dropdown_callback(interaction: discord.Interaction):
        voice_client = channel.guild.voice_client
        if len(play_queue) > 1 and voice_client:
            selected_option = int(queue_dropdown.values[0])
            selected_music = play_queue.pop(selected_option)
            play_queue.insert(1,selected_music)
            voice_client.stop()
            await interaction.response.send_message(f"{play_queue[1]['title']}을 재생합니다.",ephemeral=True)
        else:
            await interaction.response.send_message("아니 없어요",ephemeral=True)
    
    play_btn.callback = play_btn_callback  # 중지, 재생 버튼
    skip_btn.callback = skip_btn_callback  # 스킵 버튼
    queue_dropdown.callback = queue_dropdown_callback

    # 버튼을 포함한 뷰 생성
    view.add_item(queue_dropdown)
    view.add_item(play_btn)
    view.add_item(skip_btn)

    return embed,view

def playing_embed_form(video_info):
    embed = discord.Embed(
        title = video_info['title'],
        url = video_info['url'],
        description="",
        color=discord.Color.default()
    )
    embed.set_image(url=video_info['thumbnail'])
    embed.add_field(name="요청자", value=video_info['requester'], inline=True)
    embed.add_field(name="영상 길이", value=video_info['duration'], inline=True)

    return embed

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