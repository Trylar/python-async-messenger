"""Module for async client"""
import configparser
import logging
import asyncio
import os


class Client:
    """class representing async messenger client"""

    def __init__(self):
        # uncomment below string to see log messages
        logging.basicConfig(level=logging.INFO)
        asyncio.run(self.first_connect_to_server())

    async def first_connect_to_server(self):
        """
        Define connection parameters then connect
        """
        host = input("Input host or leave blank to use default:")
        port = input("Input port or leave blank to use default:")
        config = configparser.ConfigParser()
        config.read("client.ini")
        self.host = host or config["DEFAULT"]["host"]
        self.port = port or config["DEFAULT"]["port"]
        logging.info("Trying to connect to server...")
        await self.connect_to_server()

    async def reconnect_to_server(self):
        """
        Try reconnect if connection is lost
        """
        logging.info("Trying to reconnect to server...")
        await self.connect_to_server()

    async def connect_to_server(self):
        """
        Try to connect to server and then run client
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            logging.info("Connected")
            await asyncio.gather(self.listen_to_server(), self.read_input())
        except Exception as exception:
            logging.error(str(exception))
            os._exit(1)

    async def listen_to_server(self):
        """
        Listen to server and try to reconnect of connection is lost
        """
        try:
            while 1:
                data = await self.reader.read(1024)
                msg = data.decode()
                if msg:
                    print(msg)
        except ConnectionError:
            await self.reconnect_to_server()
        except Exception as exception:
            logging.error(str(exception))
            os._exit(1)

    async def read_input(self):
        """
        Red input from console and send it to server
        """
        loop = asyncio.get_running_loop()
        while True:
            msg = await loop.run_in_executor(None, self.get_input)
            if msg == "exit":
                if self.writer and not self.writer.is_closing():
                    self.writer.close()
                os._exit(0)
            else:
                self.writer.write(msg.encode())
                await self.writer.drain()

    @staticmethod
    def get_input():
        """
       This is a reST style.

       :returns: input from the user console
       """
        return input()
