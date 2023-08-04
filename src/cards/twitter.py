#
# Everything Twitter.
#
import os
import re
import tweepy

from src.util import pretty_datetime, url_to_data_uri

# A bearer token is sufficient - we only need read-only access to public info
TWITTER_API_BEARER_TOKEN = os.environ['TWITTER_BEARER_TOKEN']

def create_card_for_misc(meta: dict) -> str:
    """Handle non-tweets (by not presenting anything)"""
    return ''

def create_cards_for_embedded_urls(entities: dict) -> str:
    """Render out inline embedded content such as YouTube links

    This only supports a small subset of link embed handling,
    things like tweets to youtube videos and such.
    """

    # Hashtags/annotations/etc we absolutely don't care about. Just external urls
    if 'urls' not in entities:
        return ''

    html = ''
    for url in entities['urls']:
        # We skip anything that's just an embedded url
        # that wasn't thumbnail-ized by Twitter. These
        # don't need to be captured in a separate container.
        if 'images' not in url:
            continue

        html += '''
            <a href="{url}">
                <table>
                    <tr>
                        <td>
                            <img src="{thumbnail}" />
                        </td>
                        <td>
                            {title}

                            <p style="font-size: small; color:#666666">
                                {description}
                            </p>
                        </td>
                    </tr>
                </table>
            </a>
        '''.format(
            url=url['unwound_url'], # t.co -> zpr.io -> youtube
            description=url['description'],
            title=url['title'],
            thumbnail=url_to_data_uri(url['images'][0]['url'], 128)
        )

    return html

def link_to_tweet(tweet_id: str) -> str:
    """Generate a usable link to a tweet ID.

    Twitter doesn't care who the user is in the URL, as long
    as it's a `status/{tweet_id}` style link.
    """
    return 'https://twitter.com/twitter/status/' + tweet_id

def create_card_for_tweet(tweet_id: str, meta: dict) -> str:
    client = tweepy.Client(bearer_token=TWITTER_API_BEARER_TOKEN)

    # Pull down the tweet
    r = client.get_tweets(
        tweet_id,
        tweet_fields=['created_at', 'public_metrics', 'entities'],
        user_fields=['verified', 'profile_image_url'],
        media_fields=['preview_image_url', 'url'],
        expansions=['attachments.media_keys', 'author_id']
    )

    tweet = r.data[0]

    text = tweet.text

    # Tweets with entities will have a trailing t.co link.
    # we display (most of) these entities inline so erase it.
    if 'entities' in tweet:
        text = tweet.text[:-23]

    text = re.sub(r'\n', '<br/>', text) # nl2br

    metrics = tweet.public_metrics

    # Parse out the author
    user = r.includes['users'][0]
    profile_thumbnail = url_to_data_uri(user.profile_image_url, 64, True)

    # Parse out embedded content (urls) and convert into inline blocks
    embeds = ''
    if 'entities' in tweet and 'urls' in tweet.entities:
        embeds = create_cards_for_embedded_urls(tweet.entities)

    # Parse out attached media, if any, and convert into inline thumbnails
    thumbnails = []
    if 'media' in r.includes:
        media_count = len(r.includes['media'])
        for media in r.includes['media']:
            # If we have multiple media, we generate a thumbnail grid instead
            size = 128 if media_count > 1 else 256

            data_uri = None
            if media.preview_image_url: # Video media
                data_uri = url_to_data_uri(media.preview_image_url, size)
            elif media.url: # Image media
                data_uri = url_to_data_uri(media.url, size)

            url = media.url
            if not url:
                url = link_to_tweet(tweet_id)

            thumbnails.append('<a href="{}"><img src="{}" /></a>'.format(url, data_uri))

    # TODO: Embed posts that someone was replying to?

    # Create Mumble-compliant DOM
    # https://doc.qt.io/qt-5/richtext-html-subset.html
    return '''
        <table>
            <tr>
                <td>
                    <a href="https://twitter.com/{username}">
                        <img src="{profile_thumbnail}" />
                    </a>
                </td>
                <td>
                    <a href="https://twitter.com/{username}">
                        {name}
                        <br/>
                        <span style="color: #666666">@{username}</span>
                    </a>
                </td>
            </tr>
        </table>

        <p>{text}</p>
        {embeds}
        <p>{thumbnails}</p>

        <a href="https://twitter.com/twitter/status/{tweet_id}">
            <span style="font-size: small; color: #666666">
                {date} · <b>{retweets:,}</b> Retweets · <b>{likes:,}</b> Likes
            </span>
        </a>

    '''.format(
        tweet_id=tweet_id,
        profile_thumbnail=profile_thumbnail,
        name=user.name,
        username=user.username,
        date=pretty_datetime(tweet.created_at, relative=False),
        text=text,
        thumbnails=''.join(thumbnails),
        embeds=embeds,
        replies=metrics['reply_count'],
        retweets=metrics['retweet_count'],
        likes=metrics['like_count'],
        quotes=metrics['quote_count']
    )

def create_twitter_card(meta: dict) -> str:
    match = re.search(r'status/(?P<id>\d+)', meta['url'])
    if match:
        return create_card_for_tweet(match.group('id'), meta)

    return create_card_for_misc(meta)
