
import requests
import re
import metadata_parser

from .util import first_or_default, url_to_data_uri
from .cards.steam import create_steam_card
from .cards.twitter import create_twitter_card
from .cards.youtube import create_youtube_card


def meta_from_url(url: str) -> dict:
    """Extract metadata and thumbnails from a URL
    """
    headers = {
        # 'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

        # So far, spoofing twitter's crawler generates the best results.
        # Many sites, like Spotify, block Google's or the default UA.
        # UA list available at: https://github.com/monperrus/crawler-user-agents/blob/master/crawler-user-agents.json
        'User-Agent': 'Twitterbot/1.0'
    }

    page = metadata_parser.MetadataParser(
        url=url,
        url_headers=headers,
        # Try to work with whatever terrible content we get
        search_head_only=False,
        force_parse_invalid_content_type=True,
        support_malformed=True,
        # strategy=['og', 'dc', 'meta', 'page', 'twitter']
    )

    res = {
        'url': url,
        'discrete_url': page.get_discrete_url(),
        'title': first_or_default(page.get_metadatas('title'), 'No title'),

        # Canonical site name such as @youtube, @steam, etc.
        'site': first_or_default(page.get_metadatas('site'), 'Unknown'),

        # Generate a thumbnail for the link. Could be a video thumbnail or site.
        'thumbnail': url_to_data_uri(page.get_metadata_link('image')),

        # YouTube and related will provide an og:video:url
        # e.g. 'https://www.youtube.com/embed/pHKVSfcAO2g'
        'video_url': first_or_default(page.get_metadatas('video:url')),

        # Dump of all metadata as a dict for anything site-specific we want later
        'meta': page.metadata['meta'],
    }

    # Some sites will use Description instead of description.
    # We need to check both since the metadata_parser library can't handle it
    res['description'] = first_or_default(page.get_metadatas('description'))
    if not res['description']:
        res['description'] = first_or_default(
            page.get_metadatas('Description'), '')

    return res


def create_card_for_image_url(url: str) -> str:
    """Direct links to images get thumbnailed automatically"""
    return '<a href="{url}"><img src="{thumbnail}" /></a>'.format(
        url=url,
        thumbnail=url_to_data_uri(url, 300)
    )


def create_card_for_video_url(url: str) -> str:
    """Handle direct video links.

    Typically, these are .webm files from 4chan.
    """
    # If it's a 4chan .webm, we can hack together a thumbnail instead
    if url.find('4cdn.org') > 0 and url.endswith('.webm'):
        # https://i.4cdn.org/wsg/1651135239075.webm
        # -> https://i.4cdn.org/wsg/1651135239075s.jpg
        return '<a href="{url}"><img src="{thumbnail}" /></a>'.format(
            url=url,
            thumbnail=url_to_data_uri(url[:-5] + 's.jpg', 300)
        )

    # Otherwise, nah.
    return ''


def create_card_for_unhandled_mime_type(mime: str, url: str) -> str:
    return mime


def create_card_for_html(url: str) -> str:
    info = meta_from_url(url)

    try:
        # Twitter is annoying and doesn't expose meta tags
        if re.search('https?://twitter.com', url):
            return create_twitter_card(info)

        # Meta tags can be used to map specific sites to custom renderers
        if info['site'] == '@youtube':
            return create_youtube_card(info)
        elif info['site'].lower().endswith('steam'):
            return create_steam_card(info)
    except Exception as e:
        print(e)
        # Log exception but fallback to a generic card from
        # meta tags so at least we have something.

    # Otherwise, use a generic card
    return '''
        <table>
            <tr>
                <td>
                    <a href="{url}"><img src="{thumbnail}" /></a>
                </td>
                <td>
                    <a href="{url}"><b>{title}</b></a>
                    <p>{description}</p>
                </td>
            </tr>
        </table>
    '''.format(
        url=info['url'],
        thumbnail=info['thumbnail'],
        title=info['title'],
        description=info['description']
    )


def create_card(url: str) -> str:
    # Do a pre-flight request for content info
    head = requests.head(url, allow_redirects=True)
    ct = head.headers['content-type']

    if ct.startswith('image/'):
        return create_card_for_image_url(url)
    elif ct.startswith('video/'):
        return create_card_for_video_url(url)
    elif ct.startswith('text/html'):
        return create_card_for_html(url)

    return create_card_for_unhandled_mime_type(ct, url)
