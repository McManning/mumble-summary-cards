import os
import Ice
Ice.loadSlice('', ['-I' + Ice.getSliceDir(), 'ice/MumbleServer.ice'])

# Import from Ice slice
import MumbleServer  # nopep8
from src.commands import publish  # nopep8

meta = None


class MetaCallback(MumbleServer.MetaCallback):
    def __init__(self, logger, adapter):
        self.logger = logger
        self.adapter = adapter

    def started(self, server, current=None):
        """ Called when a server is started.

        The server is up and running when this event is sent,
        so all methods that need a running server will work.
        """
        self.logger.info('metaCallback started')

        serverR = MumbleServer.ServerCallbackPrx.uncheckedCast(
            self.adapter.addWithUUID(ServerCallback(server, current.adapter))
        )

        server.addCallback(serverR)

    def stopped(self, server, current=None):
        """ Called when a server is stopped.

        The server is already stopped when this event is sent,
        so no methods that need a running server will work.
        """
        self.logger.info('metaCallback stopped')


class ServerContextCallback(MumbleServer.ServerContextCallback):
    """Callback for injecting additional content into the MumbleServer context menu"""

    def __init__(self, server):
        self.server = server

    def contextAction(self, action, p, session, channel_id):
        print(action, p)


class ServerCallback(MumbleServer.ServerCallback):
    """Callback for Mumble server events for a distinct server"""

    def __init__(self, logger, server, adapter):
        self.logger = logger
        self.server = server
        self.logger.info('ServerCallback bound')

    def userTextMessage(self, user, msg, current=None):
        self.logger.debug('userTextMessage %s', user)
        publish(self.server, user, msg)


def get_mumble_meta():
    return meta


def mumble_connect(logger):
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

    logger.info('Connecting to mumble: ' + proxy)
    base = comm.stringToProxy(proxy)

    meta = MumbleServer.MetaPrx.checkedCast(base)

    # Attach event handlers for "meta" events (server start/stop)
    adapter = comm.createObjectAdapterWithEndpoints('Callback.Client', 'tcp')
    metaR = MumbleServer.MetaCallbackPrx.uncheckedCast(
        adapter.addWithUUID(MetaCallback(logger, adapter))
    )

    adapter.activate()
    meta.addCallback(metaR)

    # Attach event handlers to all already running server instances
    for server in meta.getBootedServers():
        serverR = MumbleServer.ServerCallbackPrx.uncheckedCast(
            adapter.addWithUUID(ServerCallback(logger, server, adapter))
        )

        server.addCallback(serverR)

    return comm
