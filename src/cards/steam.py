#
# Steam API integrations (and web scraping) for retrieving
# information about a Steam app or workshop item.
#
import requests
import re
from bs4 import BeautifulSoup

from src.util import url_to_data_uri

STEAM_WORKSHOP__ITEM_PATTERN = r'https?://steamcommunity.com/(sharedfiles|workshop)/filedetails/.*\?id=(?P<itemid>[\d]+).*'
STEAM_APP_PATTERN = r'https?://store.steampowered.com/app/(?P<appid>[\d]+)'

class SteamApiException(Exception):
    pass

class SteamApp:
    """Information about a specific Steam app on the store

    Attributes are pulled directly from the `data` of the appdetails API,
    as well as some custom calculated attributes.

    Useful attributes include:
        - name
        - short_description
        - logo_url
        - movies
        - release_date [.coming_soon, .date]
        - publishers
        - developers
        - controller_support

    :param appid: Steam App ID
    """
    appid: str
    data: dict
    scraped: dict
    _logo_b64: str
    loaded: bool

    def __init__(self, appid: str):
        self.appid = appid
        self.loaded = False
        self.scraped = {
            'reviews': []
        }

    def load_from_api(self):
        """Populate attributes from available Steam APIs"""

        details_api = 'https://store.steampowered.com/api/appdetails/?appids={}&cc=us&l=en&json=1'
        # reviews_api = 'https://store.steampowered.com/appreviews/{}?json=1'
        store_url = 'https://store.steampowered.com/app/{}'

        # TODO: Async this up
        r = requests.get(details_api.format(self.appid))
        details_json = r.json()

        # Make sure the API is bringing back real app data
        if not details_json or not details_json[self.appid]['success']:
            raise SteamApiException('Invalid App ID')

        self.data = details_json[self.appid]['data']

        # Reviews - scraped from the store page since the official API only
        # provides overall review aggregation and not a split for recent vs all
        r = requests.get(store_url.format(self.appid))
        soup = BeautifulSoup(r.content, features='html.parser')

        for subtitle in soup.select('div.subtitle'):
            for caption in subtitle.stripped_strings:
                if caption == 'Recent Reviews:' or caption == 'All Reviews:':
                    summary = subtitle.parent.select('span.game_review_summary')

                    # These next two are horrible selectors, but it's all we got :(
                    count = subtitle.parent.select('span.responsive_hidden')
                    # desc = subtitle.parent.select('span.responsive_reviewdesc')

                    if summary and count:
                        self.scraped['reviews'].append({
                            'type': caption[:-1],
                            'summary': summary[0].get_text(strip=True),
                            'count': count[0].get_text(strip=True)[1:-1]
                        })

        self.loaded = True

    @property
    def title(self) -> str:
        return self.data['name']

    @property
    def price(self) -> str:
        """Calculate a human readable price string.

        Examples: `$19.99`, `Free`, `Coming Soon`
        """
        if self.is_free:
            return 'Free'

        # No price (unreleased game, or pulled)
        if 'price_overview' not in self.data:
            return 'Not Available'

        return '${}'.format(self.price_overview['final'] / 100)

    @property
    def discount(self) -> str:
        """Calculate a human readable discount string.

        Example: `-50%`
        Will return an empty string if there is no discount.
        """
        if not self.loaded:
            self.load_from_api()

        if 'price_overview' in self.data:
            discount = self.price_overview['discount_percent']
            if discount:
                return '-{}%'.format(discount)

        return ''

    @property
    def categories(self) -> list:
        """Return a list of categories

        Example: ['Single-player', 'Steam Achievements', 'Full controller support']
        """
        if not self.loaded:
            self.load_from_api()

        return [c['description'] for c in self.data['categories']]

    @property
    def genres(self) -> list:
        """Return a list of genres

        Example: ['Survival', 'Sandbox', 'Crafting', 'Open World', 'Indie', 'Multiplayer']
        """
        if not self.loaded:
            self.load_from_api()

        return [g['description'] for g in self.data['genres']]

    @property
    def reviews(self) -> list:
        """Return review summary information

        Example: ['All Reviews: Mixed (10)', 'Recent Reviews: Mixed (5)']

        May exclude 'Recent Reviews' if it's not old enough
        """
        if not self.loaded:
            self.load_from_api()

        return self.scraped['reviews']

    @property
    def is_early_access(self) -> bool:
        """Returns true if this app is still in early access"""
        return 'Early Access' in self.genres

    @property
    def is_unreleased(self) -> bool:
        """Returns true if this app isn't out yet"""
        return self.release_date['coming_soon'] == True

    @property
    def released(self) -> str:
        """Returns the actual release date of the app.

        Examples: `Aug 7, 2018`, `No release date`
        """
        if not self.release_date['date']:
            return 'No release date'

        return self.release_date['date']

    @property
    def logo_base64(self) -> '(str | None)':
        """Return a base64 encoded version of this app's logo"""
        if not self._logo_b64:
            self._logo_b64 = url_to_data_uri(self.header_image)

        return self._logo_b64

    def __getattr__(self, attr):
        """Delegate attribute lookup to keys in our steam API JSON

        :param attr: Attribute to retrieve
        """
        if not self.loaded:
            self.load_from_api()

        if attr in self.data:
            return self.data[attr]

        raise AttributeError('Attribute {} not available from Steam API'.format(attr))

class SteamWorkshopItem:
    """Information about a specific item on the Steam Workshop

    Attributes are primarily pulled from web scraping since there's no API (afaik?)

    Properties:
        itemid (str): Workshop file ID
    """
    itemid: str
    scraped: dict
    loaded: bool

    def __init__(self, itemid: str):
        self.itemid = itemid
        self.loaded = False
        self.scraped = {
            'tags': []
        }

    def load_from_api(self):
        workshop_url = 'https://steamcommunity.com/sharedfiles/filedetails/?id={}'

        r = requests.get(workshop_url.format(self.itemid))
        soup = BeautifulSoup(r.content, features='html.parser')

        # Extract basic info (item name, app name)
        self.scraped['appname'] = soup.select_one('.apphub_AppName').text
        self.scraped['title'] = soup.select_one('.workshopItemTitle').text
        self.scraped['description'] = soup.select_one('.workshopItemDescription').text
        self.scraped['logo'] = soup.select_one('link[rel="image_src"]')['href']

        # Extract tags (variable number of tags and items per workshop item)
        for tag in soup.select('div.workshopTags'):
            self.scraped['tags'].append(tag.text.split(':\xa0'))

        """
        Scraping ratings would be nice, but not very doable right now.
        The star rating is based on an <img> that's embedded that has a certain
        filename (e.g. 4-star_large.png) but no other data on the page.
        """

        self.loaded = True

    @property
    def tags(self) -> list:
        return self.scraped['tags']

    @property
    def appname(self) -> str:
        return self.scraped['appname']

    @property
    def title(self) -> str:
        return self.scraped['title']

    @property
    def description(self) -> str:
        return self.scraped['description']

    @property
    def logo_url(self) -> str:
        """Image URL to either a logo image or a screenshot"""
        return self.scraped['logo']


def format_description(text: str) -> str:
    """Htmlize and trim description content"""
    if len(text) > 200:
        text = text[:200] + '...'

    return text

def open_with_steam(url: str) -> str:
    return 'steam://openurl/' + url

def create_steam_price_box(app: SteamApp) -> str:
    # Note that some qt table CSS rules don't apply to Mumble's renderer.
    if app.discount:
        return '''
            <table border="2" style="border-color: #000000; border-style: solid" cellpadding="2" cellspacing="0">
                <tr>
                    <td style="font-size: large; background-color: #4c6b22; color: #a4d007">{discount}</td>
                    <td style="background-color: #000000; color: #acdbf5">{price}</td>
                </tr>
            </table>
        '''.format(price=app.price, discount=app.discount)

    return '''
            <table border="2" style="border-color: #000000; border-style: solid" cellpadding="2" cellspacing="0">
                <tr>
                    <td style="background-color: #000000; color: #acdbf5">{price}</td>
                </tr>
            </table>
    '''.format(price=app.price)

def create_content_for_workshop_item(meta: dict, item: SteamWorkshopItem) -> str:
    # Tag list (different per item and workshop app)
    # Each tag may have a long comma-delimited list of values as well.
    # Example: Tabletop Simulator games have 8 tags (Category, complexity,
    # number of players, play time, etc) and contain lists for tags, like
    # "Assets: Scripting, Sounds, Dice, Cards, Figurines, Rules".
    tags_left = ''
    tags_right = ''
    left = True
    for tag in item.tags:
        if left:
            tags_left += '<br/><b>{}:</b> {}'.format(tag[0], tag[1])
        else:
            tags_right += '<br/><b>{}:</b> {}'.format(tag[0], tag[1])
        left = not left

    return '''
        <table>
            <tr>
                <td>
                    <a href="{url}"><img src="{thumbnail}" /></a>
                </td>
                <td>
                    <a href="{url}">{title}</a> for {app}
                    <p>{description}</p>
                </td>
            </tr>
        </table>
        <table>
            <tr>
                <td>
                    <p style="font-size: small; color:#666666">{tags_left}</p>
                </td>
                <td>
                    <p style="font-size: small; color:#666666">{tags_right}</p>
                </td>
            </tr>
        </table>
    '''.format(
        url=open_with_steam(meta['url']),
        thumbnail=meta['thumbnail'],
        title=item.title,
        description=format_description(item.description),
        app=item.appname,
        tags_left=tags_left,
        tags_right=tags_right,
    )

def create_content_for_app(meta: dict, app: SteamApp) -> str:
    # Additional context-aware information about the app.
    release_date = ''
    if app.is_early_access:
        if app.is_unreleased:
            release_date = '<br/><b>Unreleased Early Access Meme</b>'
        else:
            release_date = '<br/><b>Early Access Meme</b>'
    else:
        if app.is_unreleased:
            release_date = '<b>Releases:</b> {}'.format(app.release_date['date'])
        else:
            release_date = '<b>Released:</b> {}'.format(app.release_date['date'])

    # Review aggregation if we have any
    small_text = ''
    if not app.is_unreleased and app.reviews:
        small_text = ' · '.join([
            '<b>{type}:</b> {summary} ({count})'.format(**x) for x in app.reviews
        ])
    else:
        # No reviews, is it early access / to be released?
        if app.is_unreleased:
            small_text = '<b>Releases:</b> {}'.format(app.release_date['date'])
        elif app.release_date['date']:
            small_text = '<b>Released:</b> {}'.format(app.release_date['date'])
        else:
            small_text = '<b>No release date</b>'

    early_access_warning = ''
    if app.is_early_access:
        early_access_warning = '''
            <table border="3" style="margin-top: 10px; border-style: solid; border-color: #000000" cellspacing="1">
                <tr>
                    <td style="background: #000000; color: #fc9403">
                    ⚠️Early Access Meme⚠️
                    </td>
                </tr>
            </table>
        '''

    return '''
        <table>
            <tr>
                <td>
                    <a href="{url}"><img src="{thumbnail}" /></a>
                    {price_box}
                </td>
                <td>
                    <a href="{url}">{title}</a>

                    {early_access_warning}

                    <p>{description}</p>

                    <p style="font-size: small; color: #666666">
                        {small_text}
                    </p>
                </td>
            </tr>
        </table>
    '''.format(
        url=open_with_steam(meta['url']),
        thumbnail=meta['thumbnail'],
        early_access_warning=early_access_warning,
        title=app.title,
        description=format_description(app.short_description),
        price_box=create_steam_price_box(app),
        small_text=small_text,
        release_date=release_date,
    )

def create_steam_card(meta: dict) -> str:
    # Try the app/workshop specific parsers. If they fail because our web scraping
    # didn't get what it needed or it's some other steam page (like a profile)
    # then fallback to the default thumbnail + description handler.
    # try:
    match = re.match(STEAM_WORKSHOP__ITEM_PATTERN, meta['url'])
    if match:
        item = SteamWorkshopItem(match.group('itemid'))
        item.load_from_api()
        return create_content_for_workshop_item(meta, item)

    match = re.match(STEAM_APP_PATTERN, meta['url'])
    if match:
        app = SteamApp(match.group('appid'))
        return create_content_for_app(meta, app)
    # except:
    #     pass

    # Everything else - fallback to meta tags
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
        url=open_with_steam(meta['url']),
        thumbnail=meta['thumbnail'],
        title=meta['title'],
        description=meta['description']
    )
