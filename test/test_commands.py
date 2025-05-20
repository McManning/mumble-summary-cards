
import MumbleServer
from src.commands import publish
import os
import sys
import unittest
from unittest.mock import Mock

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, os.pardir))
sys.path.insert(0, PROJECT_DIR)


class MockServer(MumbleServer.Server):
    def sendMessageChannel(self, channel, tree, text):
        self.text = text

    def sendMessage(self, session, text):
        self.text = text

    def getUsers():
        return [create_mock_user()]


def create_mock_text(text):
    return MumbleServer.TextMessage([0], [0], [], text)


def create_mock_user():
    user = MumbleServer.User()
    user.name = 'Mock'

    return user


class CommandsTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_link(self):
        server = MockServer()
        user = create_mock_user()

        text = create_mock_text('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        publish(server, user, text)

        self.assertTrue(len(server.text) > 0)
