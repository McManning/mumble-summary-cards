
from io import BytesIO
from sys import platform
import datetime
import ipaddress
import re
import base64
from PIL import Image, ImageDraw
import requests
import humanize

def crop_to_circle(img):
    """Circular crop, preserving alpha.
    Author: https://stackoverflow.com/a/59804079
    """
    bigsize = (img.size[0] * 3, img.size[1] * 3)
    mask = Image.new('L', bigsize, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(img.size, Image.ANTIALIAS)
    # mask = ImageChops.darker(mask, img.split()[-1])
    img.putalpha(mask)

def url_to_data_uri(url: str, size: int = 128, round: bool = False):
    """Returns a base 64 data URI version of the source URL image

    :param url: Source URL
    :param size: Thumbnail size

    :return str|None: Data URI
    """
    if not url:
        return None

    r = requests.get(url)
    img = Image.open(BytesIO(r.content))

    if round:
        crop_to_circle(img)

    # Resize thumbnail
    # TODO: Skip resize if it's already small enough?
    # TODO: Customize resize based on website? (E.g. youtube should be bigger)
    img.thumbnail((size, size), Image.ANTIALIAS)

    # Return b64 encoded version
    buffered = BytesIO()
    img.save(buffered, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffered.getvalue()).decode('utf-8')

def first_or_default(value, default = None):
    return value[0] if type(value) is list and len(value) > 0 else default

def pretty_datetime(dt, relative: bool = True, include_time: bool = True):
    """Returns a Twitter-style format, e.g. `6:30 AM · May 2, 2022`
    """
    if relative:
        return humanize.naturaldate(dt)

    if include_time:
        fmt = '%-I:%M %p · %B %-d, %Y'
    else:
        fmt = '%B %-d, %Y'

    # There's platform differences for leading zeros between Windows/Linux
    if platform == 'win32':
        fmt = fmt.replace('-', '#')

    return dt.strftime(fmt)

def parse_isoduration(isostring, as_dict=False):
    """
    Parse the ISO8601 duration string as hours, minutes, seconds
    Author: https://stackoverflow.com/a/66569868
    """
    separators = {
        "PT": None,
        "W": "weeks",
        "D": "days",
        "H": "hours",
        "M": "minutes",
        "S": "seconds",
    }
    duration_vals = {}
    for sep, unit in separators.items():
        partitioned = isostring.partition(sep)
        if partitioned[1] == sep:
            # Matched this unit
            isostring = partitioned[2]
            if sep == "PT":
                continue # Successful prefix match
            dur_str = partitioned[0]
            dur_val = float(dur_str) if "." in dur_str else int(dur_str)
            duration_vals.update({unit: dur_val})
        else:
            if sep == "PT":
                raise ValueError("Missing PT prefix")
            else:
                # No match for this unit: it's absent
                duration_vals.update({unit: 0})
    if as_dict:
        return duration_vals
    else:
        return tuple(duration_vals.values())

def address_tuple_to_ipv6(address):
    """Convert an address tuple to an IPv6Address object"""
    groups = ['{:02X}{:02X}'.format(address[i], address[i+1]) for i in range(0, 16, 2)]
    long_form = ':'.join(groups)

    return ipaddress.IPv6Address(long_form)

def texture_to_data_uri(texture) -> str:
    """Convert a Murmur Texture to a data uri encoded PNG"""

    if len(texture) < 1:
        return None

    # Murmur gives us the *original* image data, so we want
    # to try to decode that, crush it to an avatar size, and encode
    image = Image.open(BytesIO(texture))
    image.thumbnail((128, 128), Image.ANTIALIAS)

    # Convert image to PNG string
    buffered = BytesIO()
    image.save(buffered, format='PNG')

    encoded = base64.b64encode(buffered.getvalue())
    return 'data:image/png;base64,' + encoded.decode('utf-8')

def strip_html(html: str) -> str:
    """Strip out tags from an HTML string

    :param html: content to strip
    """
    return re.sub('<[^<]+?>', '', html)

def now() -> str:
    """Return ISO8601 timestamp of UTC now"""
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

def get_addr(info):
    """Return IPv6Address from the request context.

    Safely handles internal forwards from Nginx and conversion to IPv6
    (as it may be passed as IPv4 via Nginx)
    """
    headers_list = info.context.headers.getlist("X-Forwarded-For")
    ip4or6 = ipaddress.ip_address(
        headers_list[0] if headers_list else info.context.remote_addr
    )

    if type(ip4or6) == ipaddress.IPv6Address:
        return ip4or6

    # Convert to an IPv4 mapped IPv6
    return ipaddress.ip_address('::ffff:' + str(ip4or6))

