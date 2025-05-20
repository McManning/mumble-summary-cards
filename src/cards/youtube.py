import os
import requests
import random
from datetime import datetime, timedelta

from src.util import parse_isoduration, pretty_datetime


def get_api_key() -> str:
    if "YOUTUBE_API_KEY" in os.environ:
        return os.environ['YOUTUBE_API_KEY']

    return None


def create_youtube_card(meta: dict) -> str:
    if get_api_key() is None:
        raise ValueError(
            'This feature requires an API key for YouTube Data API v3')

    return '''
        <table>
            <tr>
                <td>
                    <a href="{url}"><img src="{thumbnail}" /></a>
                </td>
                <td>
                    <a href="{url}"><b>{title}</b></a>
                    <br/>
                    {description}
                </td>
            </tr>
        </table>
    '''.format(
        url=meta['url'],
        thumbnail=meta['thumbnail'],
        title=meta['title'],
        description=create_youtube_video_description(meta)
    )


def create_youtube_video_description(meta: dict) -> str:
    """
    Use YouTube's Data API to create a more useful video description
    instead of the complete garbage most people put in there.

    SuBscRiBe tO mY PaTReOn
    """
    # Ref: https://developers.google.com/youtube/v3/getting-started

    # Don't have a video embed link - don't use the API
    url = meta['video_url']
    if not url or url.find('embed') < 0:
        return meta['description']

    # Should look like 'https://www.youtube.com/embed/pHKVSfcAO2g'
    video_id = url[url.find('embed')+6:]

    # If the embed code had a playlist attached, delete it
    if video_id.find('?') > 0:
        video_id = video_id[:video_id.find('?')]

    url = 'https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={key}&part=snippet,contentDetails,statistics,status'.format(
        video_id=video_id,
        key=YOUTUBE_DATA_API_KEY
    )

    r = requests.get(url)
    json = r.json()

    if len(json['items']) < 1:
        return ''

    info = json['items'][0]
    published_at = datetime.strptime(
        info['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%S%z")
    duration = info['contentDetails']['duration']

    try:
        t = parse_isoduration(duration, as_dict=True)
        td = timedelta(**t)
        duration = td
    except:  # Live videos don't have a valid duration
        duration = '<b>Live</b>'

    views = int(info['statistics']['viewCount'])
    likes = int(info['statistics']['likeCount'])

    random.seed(views)
    dislikes = int(likes * random.random() * 3)  # lol

    # We're going to kinda mimic google results here
    return '''
        YouTube · {channel} · {duration}

        <p style="font-size: small; color: #666666">
            <b>{views:,}</b> Views · {date}
        </p>
    '''.format(
        duration=duration,
        channel=info['snippet']['channelTitle'],
        views=views,
        likes=likes,
        dislikes=dislikes,
        date=pretty_datetime(published_at, relative=False, include_time=False)
    )
