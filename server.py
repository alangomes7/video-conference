import threading
import socket
import random
import time

import message as message_manager


def receive():
    """
    Function to receive client connections on the server.
    """
    global stop_server, clients_connected, clients_moderators
    while not stop_server:
        try:
            log_file("Waiting for connection...")

            # Accept incoming connection and get client information
            socket_client, address = socket_server.accept()
            log_file("Connection established")

            # Request client name
            protocol_message = message_manager.protocol_message_encoding("server", "client", "name")
            server_sends(protocol_message, socket_client)

            # Receive client's name
            received_message = message_manager.protocol_message_decoding(socket_client.recv(BUFFER_SIZE))
            log_file(received_message)

            # Check if the username is available
            client_username = received_message[3]
            if get_client_socket_by_name(client_username, clients_connected) == "not found":
                log_file("Connection established: (%s) -> %s" % (received_message[3], address))

                # Add the client to the connected clients
                add_client(client_username, socket_client)

                message_data = "You are now connected to the server.\n"
                message_data += "Your address: " + str(address)
                message_protocol = message_manager.protocol_message_encoding(
                    "server", received_message[3], message_manager.OPCODE_CONNECTION_CONFIRMATION, message_data)

                # Send connection confirmation message
                server_sends(message_protocol)

                # Use threads to allow multiple connections and actions simultaneously
                thread_handle_client = threading.Thread(target=handle_client, args=(socket_client,), daemon=True)
                thread_handle_client.start()
            else:
                # Inform the client that the username is taken
                message_data = "This username (" + received_message[3] + ") is already taken.\n"
                message_data += "You need to connect again and use another one"
                protocol_message = message_manager.protocol_message_encoding(
                    "server", received_message[3], message_manager.OPCODE_CONNECTION_ERROR, message_data)
                log_file("Sent: %s" % protocol_message)
                server_sends(protocol_message, socket_client)
        except socket.error as socket_error:
            server_checks(socket_error)
    server_checks()


def handle_client(client):
    """
    Function to manage client's messages.
    :param client: client sender
    """
    global stop_server, close_server, clients_connected, clients_moderators
    message_received = ["", "", "", ""]
    message_data = ""
    while not stop_server:
        try:
            message_received = message_manager.protocol_message_decoding(client.recv(BUFFER_SIZE))
            log_file("Server receive: %s" % message_received)
            user_sender = message_received[0]
            message_confirmation(user_sender, message_received[2])
            # Server actions based on the received message opcode
            if message_received[2] == message_manager.OPCODE_UNKNOWN_OPERATION:
                message_data = "Operation not supported!"
                protocol_message = \
                    message_manager.protocol_message_encoding(
                        "server", user_sender, message_manager.OPCODE_UNKNOWN_OPERATION, message_data)
                server_sends(protocol_message)
                continue
            if message_received[2] == message_manager.OPCODE_ECHO:
                protocol_message = message_manager.protocol_message_encoding(
                    user_sender, user_sender, message_manager.OPCODE_ECHO, message_received[3])
                server_sends(protocol_message)
                continue
            if message_received[2] == message_manager.OPCODE_PRIVATE_MESSAGE:
                protocol_message = message_manager.protocol_message_encoding(
                    user_sender, message_received[1], message_manager.OPCODE_PRIVATE_MESSAGE,
                    message_received[3])
                server_sends(protocol_message)
                continue
            if message_received[2] == message_manager.OPCODE_BROADCAST \
                    or message_received[2] == message_manager.OPCODE_BROADCAST_NOT_ME:
                protocol_message = message_manager.protocol_message_encoding(
                    user_sender, message_manager.OPCODE_BROADCAST, message_received[2], message_received[3])
                server_sends(protocol_message)
                continue
            if message_received[2] == message_manager.OPCODE_LIST_CLIENTS and message_received[1] == "server":
                protocol_message = message_manager.protocol_message_encoding(
                    SERVER_ITSELF, user_sender, message_manager.OPCODE_LIST_CLIENTS, get_all_list())
                server_sends(protocol_message)
                continue
            if message_received[2] == message_manager.OPCODE_EXIT_CLIENT:
                # sends to everyone: client left
                message_data = "client (" + user_sender + ") left"
                protocol_message = \
                    message_manager.protocol_message_encoding(
                        SERVER_ITSELF, message_manager.OPCODE_BROADCAST, message_manager.OPCODE_EXIT_CLIENT,
                        message_data)
                server_sends(protocol_message)
                # sends the answer to client
                message_data = "You are existing the server"
                protocol_message = message_manager.protocol_message_encoding(
                    SERVER_ITSELF, user_sender, message_manager.OPCODE_EXIT_CLIENT, message_data)
                server_sends(protocol_message)
                # removes the client from clients_connected
                remove_client(message_received[0])
                continue
            if message_received[2] == message_manager.OPCODE_CLOSE_SERVER:
                # Check if the user has enough permissions to close the server
                if get_client_socket_by_name(user_sender, clients_moderators) != "not found":
                    message_data = "server closed"
                    stop_server = True
                    close_server = True
                else:
                    message_data = "You do not have enough permissions to execute that action!"
                    protocol_message = \
                        message_manager.protocol_message_encoding(
                            SERVER_ITSELF, user_sender, message_manager.OPCODE_PRIVATE_MESSAGE, message_data)
                    server_sends(protocol_message)
            if message_received[2] == message_manager.OPCODE_VIDEO_CONFERENCE \
                    and message_received[3] == message_manager.MESSAGE_REQUESTING:
                message_data = "Client " + message_received[0] + "is requesting a video conference"
                protocol_message = message_manager.protocol_message_encoding(
                    message_received[0], message_received[1], message_received[2], message_data)
                server_sends(protocol_message)
        except socket.error as socket_error:
            # removes the clients from list
            message_data = str(socket_error) + " | "
            message_data += "client (" + user_sender + ") disconnected"
            protocol_message = message_manager.protocol_message_encoding(
                SERVER_ITSELF, message_manager.OPCODE_BROADCAST, message_manager.OPCODE_BROADCAST,
                message_data)
            socket_client = get_client_socket_by_name(message_received[0], clients_connected)
            remove_client(socket_client)
            receive()
            server_sends(protocol_message)
    if close_server:
        log_file("Closing server...")
        message_data += "\nUser (" + message_received[0] + ") closes the server."
        protocol_message = message_manager.protocol_message_encoding(
            SERVER_ITSELF, message_manager.OPCODE_BROADCAST, message_manager.OPCODE_BROADCAST, message_data)
        server_sends(protocol_message)
        time.sleep(2)
        socket_server.close()
    else:
        receive()


def message_confirmation(user_sender, message_code):
    if message_code in (message_manager.OPCODE_PRIVATE_MESSAGE, message_manager.OPCODE_BROADCAST_NOT_ME):
        server_sends(message_manager.protocol_message_encoding(
            SERVER_ITSELF, user_sender, message_manager.OPCODE_MESSAGE_CONFIRMATION, "message sent"))


def server_sends(protocol_message, socket_client=None):
    """
    Prints the server message and sends it
    :param protocol_message: message to forward
    :param socket_client: socket used to send a message to a refused client connection
    """
    global clients_connected
    log_file("Server sends: %s" % protocol_message)
    if not socket_client:
        if clients_connected:
            message_manager.send_server_message(protocol_message, clients_connected)
        else:
            log_file("Server clients is empty!")
    else:
        socket_client.send(protocol_message)
    time.sleep(2)


def server_checks(socket_error=""):
    """
    Verify if the server was closed due a client message or error
    """
    global stop_server, close_server
    if stop_server:
        log_file("Server closed")
        close_server = True
    else:
        log_file(socket_error)
        log_file("Restarting the server...\n")
        receive()


def get_client_socket_by_name(client_name, client_list):
    """
    Function to search for a client by name.
    :param client_name: client_name
    :param client_list: list of clients
    :return: the client obj or "Not found"
    """
    client_socket = client_list.get(client_name, "not found")
    return client_socket


def get_all_list():
    """
    Function to show the list of connected clients in all pairs (clients,address).
    :return: list of clients
    """
    global clients_connected
    # Get a view object of all key-value pairs in the dictionary
    all_items = ""  # clients_connected.items()
    for key, value in clients_connected.items():
        address = str(value).split("raddr=")[1][:-1]
        all_items += key + " -> " + address + "\n"
    # Convert the view object to a list if needed
    # items_list = list(all_items)
    return all_items


def add_client(username, client_socket):
    """
    Add client on dictionary
    :param: username: client's username to add
    :param: client_socket: client's socket to add
    """
    global clients_connected
    clients_connected[username] = client_socket
    add_moderator(username, client_socket)


def add_moderator(client_username, client_socket):
    """
    Verify is the server has moderators. If it has not then adds else do not add it.
    :param: client_username: client's username to add.
    :param: client_socket: client's socket to add.
    """
    global clients_moderators
    if dict_empty(clients_moderators):
        clients_moderators[client_username] = client_socket


def remove_client(client_username):
    """
    Removes element from dictionary
    :param: client_username: client's username to be removed from dict
    :dict_clients: dictionary to be updated without client
    """
    global clients_connected, clients_moderators
    clients_moderators.pop(client_username, -1)
    clients_connected.pop(client_username, -1)
    server_has_at_least_one_moderator()


def server_has_at_least_one_moderator():
    """
    Verify if the server can continues open.
    The server can only continue open if exists at least one moderator.
    """
    global stop_server, close_server
    # verify if the server can continue open
    if not clients_moderators:
        stop_server = True
        close_server = True
        time.sleep(3)


def dict_empty(dict_clients):
    """Verify is dict is empty
    :param: dict_clients: dict to verify
    :return: True if empty else False
    """
    if not dict_clients:
        return True
    else:
        return False


def get_local_ip():
    """
    Function to get the local IP address.
    """
    try:
        # Get the hostname
        hostname = socket.gethostname()
        # Get the local IP address
        local_ip = socket.gethostbyname(hostname)
        return local_ip

    except socket.error as e:
        log_file(f"Error: {e}")
        return None


def socket_connect():
    """
    Function to create a socket and connect it.
    """
    global stop_server
    # Create a new socket, family: Ipv4, type: TCP
    socket_connecting = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    host = get_local_ip()
    port = 1234
    connecting = True
    while connecting:
        try:
            log_file("Connection attempt...")
            socket_connecting.bind((host, port))
            socket_connecting.listen(10)
            connecting = False
            log_file("Server is running and listening on (%s,%s)\n" % (host, port))
        except socket.error as e:
            log_file(f"Error: {e}")
            log_file("Server connection error on (%s,%s)" % (host, port))
            user_server = str(input("n = to finish or any key to try again...\n"))
            if user_server == "n":
                stop_server = True
                connecting = False
            else:
                port = random.randint(49152, 65535)
    return socket_connecting


def log_file(log_message):
    print(log_message)
    log_file_path = 'log.txt'
    with open(log_file_path, 'a') as file:
        file.write(str(log_message) + '\n')


# Main function
if __name__ == "__main__":
    stop_server = False
    socket_server = socket_connect()

    if not stop_server:
        close_server = False
        BUFFER_SIZE = 1024
        SERVER_ITSELF = "Server"
        SENDS_TO_ALL = "All clients"

        clients_connected = {}
        """dictionary with all clients connected"""
        clients_moderators = {}
        """dictionary with all moderators clients"""
        # Starting the server
        receive()
    else:
        log_file("Execution finished.")
