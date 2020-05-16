"""Module for User class"""


class User:
    """class representing client connections"""

    def __init__(self, writer_stream, peername):
        self.writer_stream = writer_stream
        self.peername = str(peername)
        self.status = "unknown"
        self.login = ""
