"""Module for async server"""
import asyncio
import configparser
import logging
import sqlite3
from passlib.hash import pbkdf2_sha256

from user import User


class Server:
    """class for async messenger server"""
    users = []

    def __init__(self):
        """
        Defining parameters for starting server and then start
        """
        # comment below string to remove log messages output
        logging.basicConfig(level=logging.INFO)
        config = configparser.ConfigParser()
        config.read("server.ini")
        self.help_msg = config["INFO"]["help message"]
        self.host = config["DEFAULT"]["host"]
        self.port = config["DEFAULT"]["port"]
        logging.info("Starting server...")
        asyncio.run(self.start_server())

    async def start_server(self):
        """
        Function starting server
        """
        self.server = await asyncio.start_server(self.connection_callback, host=self.host, port=self.port)
        async with self.server:
            logging.info("Server started")
            await self.server.serve_forever()

    async def connection_callback(self, reader_stream, writer_stream):
        """
        Function called when connection is created and terminating when the user disconnects

        :param reader_stream: stream from which messages from the user are read
        :param writer_stream: stream to which messages are written for the user
        """
        user = User(writer_stream, writer_stream.get_extra_info("peername"))
        self.users.append(user)
        logging.info("New client connected: %s", user.peername)
        try:
            while True:
                data = await reader_stream.read(1024)
                message = data.decode()
                await self.parse_message(user, message)
        except ConnectionError as exception:
            logging.info("%s: %s", (user.login or user.peername), str(exception))
        except Exception as exception:
            logging.error(exception)
            writer_stream.close()
            await writer_stream.wait_closed()
        finally:
            self.users.remove(user)

    async def parse_message(self, user, msg):
        """
        Depending on user status and his message call necessary function

        :param user
        :param msg
        """
        if msg == "help":
            await self.send_help(user)
        elif user.status == "unknown" and str(msg).startswith("register"):
            await self.register_new_user(user, msg[len("register"):])
        elif user.status == "unknown" and msg.startswith("login"):
            await self.authenticate(user, msg[len("login"):])
        elif user.status == "authenticated" and msg.startswith("all:"):
            await self.send_msg_all(user, msg[len("all:"):])
        elif user.status == "authenticated" and ":" in msg:
            recipient, message = msg.split(":", 1)
            await self.send_msg_usr(user, recipient, message)
        else:
            await self.send_err_msg(user)

    async def send_help(self, user):
        """
        Send help message to the user

        :param user
        """
        await self.send_msg(user, self.help_msg)

    async def register_new_user(self, user, register_data):
        """
        Add credentials of user into database

        :param user
        :param register_data: string from user message containing register data
        """
        try:
            login, pswd, pswd_confirm = register_data.strip().split(" ", 2)
        except Exception:
            await self.send_err_msg(user)
            return
        if pswd != pswd_confirm:
            msg = "Passwords don't match"
            logging.info("%s: %s", user.peername, msg)
            await self.send_msg(user, msg)
        else:
            try:
                credentials_db = sqlite3.connect("credentials.db")
                credentials_cursor = credentials_db.cursor()
                credentials_cursor.execute(
                    "create table if not exists credentials (login TEXT, password TEXT)")
                record = credentials_cursor.execute("SELECT * FROM credentials WHERE login=?", (login,))
                if record.fetchone():
                    msg = "Error: login already in use"
                    logging.info(user.peername + msg + " : " + login)
                    await self.send_msg(user, msg)
                else:
                    pswd_hash = pbkdf2_sha256.hash(pswd)
                    credentials_cursor.execute("INSERT INTO credentials VALUES (?,?)", (login, pswd_hash))
                    credentials_db.commit()
                    msg = "Successful registration. Now you can log in"
                    logging.info(user.peername + msg + " : " + login)
                    await self.send_msg(user, msg)
            except Exception as exception:
                logging.error(exception)
                await self.send_msg(user, "Error occurred: " + str(exception))
            finally:
                credentials_db.close()

    async def authenticate(self, user, login_data):
        """
        Check credentials of user in database

        :param user
        :param login_data: string from user message containing credentials
        """
        try:
            login, pswd = login_data.strip().split(" ", 1)
        except Exception:
            await self.send_err_msg(user)
            return
        credentials_db = sqlite3.connect("credentials.db")
        credentials_cursor = credentials_db.cursor()
        credentials_cursor.execute(
            "create table if not exists credentials (login TEXT, password TEXT)")
        record = credentials_cursor.execute("SELECT password FROM credentials WHERE login=?", (login,))
        pswd_hash = record.fetchone()
        if not pswd_hash:
            msg = "Error: unknown login"
            logging.info(user.peername + msg + " : " + login)
            await self.send_msg(user, "Error: unknown login")
        else:
            pswd_db = pswd_hash[0]
            if pbkdf2_sha256.verify(pswd, pswd_db):
                user.login = login
                user.status = "authenticated"
                msg = "Successful authentication"
                logging.info(user.peername + " " + msg + ": " + login)
                await self.send_msg(user, msg)
            else:
                msg = "Incorrect password"
                logging.info("%s: %s", user.peername, msg)
                await self.send_msg(user, msg)
        credentials_db.close()

    async def send_msg_all(self, user, msg):
        """
        Send message to all authenticated users

        :param user
        :param msg
        """
        msg = user.login + "->all:" + msg
        for usr in self.users:
            if usr.status == "authenticated" and usr.login != user.login:
                await self.send_msg(usr, msg)

    async def send_msg_usr(self, user, recipient, msg):
        """
        Send message from one user to another

        :param user
        :param recipient: user who is recipient of the message
        :param msg
        """
        msg = user.login + "->" + recipient + ":" + msg
        for usr in self.users:
            if usr.status == "authenticated" and usr.login == recipient:
                await self.send_msg(usr, msg)
                break
        else:
            msg = "User with this login doesn't exist or is offline"
            logging.info("%s: %s", msg, recipient)
            await self.send_msg(user, msg)

    async def send_msg(self, user, msg):
        """
        Send message to the user

        :param user
        :param msg
        """
        user.writer_stream.write(msg.encode())
        await user.writer_stream.drain()

    async def send_err_msg(self, user):
        """
        Send error message to the user

        :param user
        """
        msg = "Incorrect format of message or you don't have enough rights. Send 'help' message for information"
        logging.info("%s: %s", (user.login or user.peername), msg)
        await self.send_msg(user, msg)
