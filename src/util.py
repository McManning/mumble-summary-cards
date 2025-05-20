
from io import BytesIO
from sys import platform
import datetime
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


def first_or_default(value, default=None):
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
                continue  # Successful prefix match
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


def strip_html(html: str) -> str:
    """Strip out tags from an HTML string

    :param html: content to strip
    """
    return re.sub('<[^<]+?>', '', html)


def now() -> str:
    """Return ISO8601 timestamp of UTC now"""
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
