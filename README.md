# Async messenger

Simple project representing async client and server.

Usage
-----

Client can be run from ```msg_client``` folder as ```python run_client.py```

Server can be run from ```msg_server``` folder as ```python run_server.py```

No parameters needed for running.

Usage of client:

    Format of messages can be as follows (all values in brackets are mandatory, brackets are NOT needed):
    help -> prints this help message
    register [login] [password] [password_confirmation] -> to register new user
    login [login] [password] -> to login as registered user
    all:[message] -> send message* to all authenticated users.
    [user_login]:[message] -> send message* to user with login [user_login]
    *You need to be authenticated to send messages