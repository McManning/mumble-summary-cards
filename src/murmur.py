
import os

import Ice
Ice.loadSlice('', ['-I' + Ice.getSliceDir(), 'ice/Murmur.ice'])

# Import from Ice slice
import Murmur

from src.commands import publish
from src.util import address_tuple_to_ipv6, texture_to_data_uri

meta = None

class MetaCallback(Murmur.MetaCallback):
    def __init__(self, logger, adapter):
        self.logger = logger
        self.adapter = adapter

    def started(self, server, current=None):
        """ Called when a server is started.

        The server is up and running when this event is sent,
        so all methods that need a running server will work.
        """
        self.logger.info('metaCallback started')

        serverR = Murmur.ServerCallbackPrx.uncheckedCast(
            self.adapter.addWithUUID(ServerCallback(server, current.adapter))
        )

        server.addCallback(serverR)

    def stopped(self, server, current=None):
        """ Called when a server is stopped.

        The server is already stopped when this event is sent,
        so no methods that need a running server will work.
        """
        self.logger.info('metaCallback stopped')


class ServerContextCallback(Murmur.ServerContextCallback):
    """Callback for injecting additional content into the Murmur context menu"""
    def __init__(self, server):
        self.server = server

    def contextAction(self, action, p, session, channel_id):
        print(action, p)


class ServerCallback(Murmur.ServerCallback):
    """Callback for Murmur server events for a distinct server"""
    def __init__(self, logger, server, adapter):
        self.logger = logger
        self.server = server
        self.logger.info('ServerCallback bound')

    def userTextMessage(self, user, msg, current=None):
        self.logger.debug('userTextMessage %s', user)
        publish(self.server, user, msg)

def get_murmur_meta():
    return meta

def murmur_connect(logger):
    """
    Returns:
        Mumble Ice runtime
    """
    global meta

    logger.info('Configuring Ice')

    props = Ice.createProperties()
    props.setProperty('Ice.ImplicitContext', 'Shared')
    props.setProperty('Ice.MessageSizeMax', '65535')
    props.setProperty('Ice.Default.EncodingVersion', '1.0')

    idd = Ice.InitializationData()
    idd.properties = props

    comm = Ice.initialize(idd)
    comm.getImplicitContext().put('secret', os.environ['ICE_SECRET'])

    proxy = 'Meta:tcp -h {host} -p {port}'.format(
        host=os.environ['ICE_HOST'],
        port=os.environ['ICE_PORT']
    )

    logger.info('Connecting to Murmur: ' + proxy)
    base = comm.stringToProxy(proxy)

    meta = Murmur.MetaPrx.checkedCast(base)

    # Attach event handlers for "meta" events (server start/stop)
    adapter = comm.createObjectAdapterWithEndpoints('Callback.Client', 'tcp')
    metaR = Murmur.MetaCallbackPrx.uncheckedCast(
        adapter.addWithUUID(MetaCallback(logger, adapter))
    )

    adapter.activate()
    meta.addCallback(metaR)

    # Attach event handlers to all already running server instances
    for server in meta.getBootedServers():
        serverR = Murmur.ServerCallbackPrx.uncheckedCast(
            adapter.addWithUUID(ServerCallback(logger, server, adapter))
        )

        server.addCallback(serverR)

    return comm
