
import re
import functools
import random
import requests
import Murmur
from src.factories import create_card

command_subscribers = []

class TextMessage(Murmur.TextMessage):
    """Wrapper for Murmur TextMessages to add additional message context

    Args:
        server:     Server this message is sent to.
        user:       User that sent this message. None implies a system message
        sessions:   Sessions (connected users) who were sent this message.
        channels:   Channels who were sent this message.
        trees:      Trees of channels who were sent this message.
        text:       The contents of the message.
        match:      Re match groups if the message was mapped to a command
    """
    def __init__(
        self,
        user=None,
        server=None,
        sessions=None,
        channels=None,
        trees=None,
        text='',
        match=None
    ):
        super().__init__(sessions, channels, trees, text)
        self.user = user
        self.server = server
        self.match = match

class TextResponse:
    """Prepared message to an individual, channel, or server

    Args:
        message:    the message to send (text or HTML)
        server:     the target Murmur server. Defaults to all servers
        channel:    the target channel for the message. If unspecified,
                    all channels on `server` will receive the message.
        user:       the target user for a direct message. Will be ignored
                    if `channel` is specified.
    """
    def __init__(
        self,
        message: str,
        server: Murmur.Server = None,
        channel: Murmur.Channel = None,
        user: Murmur.User = None
    ):
        self.message = message
        self.server = server
        self.channel = channel
        self.user = user

def publish(
    server: Murmur.Server,
    user: Murmur.User,
    msg: Murmur.TextMessage
):
    """Publish a text message to all commands matching the message pattern

    Args:
        server (Murmur.Server):     Originating server instance
        user (Murmur.User):         User that sent the message
        msg (Murmur.TextMessage):   The message that was sent
    """
    # Wrap original message in a more context aware TextMessage
    wrapped = TextMessage(
        user,
        server,
        msg.sessions,
        msg.channels,
        msg.trees,
        msg.text
    )

    for command in command_subscribers:
        match = command['prog'].search(msg.text)
        if match:
            command['func'](wrapped, **match.groupdict())
            return

def subscribe(
    pattern: str,
    usage: str,
    func: callable
):
    # Make sure it's not already registered before registering
    # (can happen during werkzeug lazy reloads)
    for command in command_subscribers:
        if command['func'] == func:
            return

    command_subscribers.append({
        'prog': re.compile(pattern, re.IGNORECASE),
        'usage': usage,
        'func': func
    })

def command(pattern: str, usage: str = None):
    """Decorator for command subscriber methods"""
    def decorator(func):
        subscribe(pattern, usage, func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

@command(r'(?P<url>https?://[^\s]+)\"')
def any_url(msg: TextMessage, url: str):
    """Generate a card for any URL

    Note the regex has a trailing quote match because URLs in murmur will
    come in as `<a href="...">...</a>`.

    Args:
        msg (TextMessage):  TextMessage that triggered this command response
        url (str):          URL to cardify
    """
    # try:
    html = create_card(url)
    for channel in msg.channels:
        msg.server.sendMessageChannel(channel, False, html)
    # except:
    #     # Ignore anything we can't cardify
    #     logger.error()
