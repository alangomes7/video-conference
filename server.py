import threading
import socket
import random

import message as message_manager


def receive():
    """
    receive client's connection: the server.
    """
    global stop_server
    while not stop_server:
        try:
            # First: get client and client_name
            socket_client, address = socket_server.accept()
            # message to request client name
            protocol_message = message_manager.protocol_message_encoding("server", "client", "name")
            # using this method because the client is not added on clients_connect list yet
            socket_client.send(protocol_message)
            # receive client's name
            received_message = message_manager.protocol_message_decoding(socket_client.recv(BUFFER_SIZE))
            print(received_message)
            if username_available(received_message[3]):
                print("connection is established: (%s) -> %s" % (received_message[3], address))
                clients_connected[socket_client] = received_message[3]
                # check in clients_moderators is empty
                if not clients_moderators:
                    clients_moderators[socket_client] = received_message[3]
                message_data = "You are now connected to the server in " + str(address)
                message_protocol = message_manager.protocol_message_encoding(
                    "server", received_message[3], message_manager.OPCODE_CONNECTION_CONFIRMATION, message_data)
                message_manager.send_server_message(message_protocol, clients_connected)
                print("Sent: " + message_protocol.decode('utf-8'))
                # now using threads to allow multiple connections and actions simultaneously
                thread = threading.Thread(target=handle_client, args=(socket_client,), daemon=True)
                thread.start()
            else:
                message_data = "This username is already taken. "
                message_data += "You need to connect again and use another one"
                new_client_name = "new_client: " + received_message[3]
                protocol_message = message_manager.protocol_message_encoding(
                    "server", new_client_name, message_manager.OPCODE_CONNECTION_ERROR, message_data)
                socket_client.send(protocol_message)
                print(protocol_message)
                break
        except socket.error as socket_error:
            if stop_server:
                print("Server closed")
            else:
                print(socket_error)
                print("Server closed")


def handle_client(client):
    """
    Manage client's messages
    :param client: client sender
    """
    message_received = ["", "", "", ""]
    global stop_server
    while not stop_server:
        try:
            message_received = message_manager.protocol_message_decoding(client.recv(BUFFER_SIZE))
            print("Server receive: %s" % message_received)
            # server actions
            if message_received[2] == message_manager.OPCODE_UNKNOWN_OPERATION:
                message_data = "Operation not supported!"
                protocol_message = message_manager.protocol_message_encoding("server", message_received[0],
                                                                             message_manager.OPCODE_UNKNOWN_OPERATION,
                                                                             message_data)
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == message_manager.OPCODE_ECHO:
                protocol_message = message_manager.protocol_message_encoding(message_received[0], message_received[0],
                                                                             message_manager.OPCODE_ECHO,
                                                                             message_received[3])
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == message_manager.OPCODE_PRIVATE_MESSAGE:
                protocol_message = message_manager.protocol_message_encoding(message_received[0], message_received[1],
                                                                             message_manager.OPCODE_PRIVATE_MESSAGE,
                                                                             message_received[3])
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == message_manager.OPCODE_BROADCAST or message_received[
                2] == message_manager.OPCODE_BROADCAST_NOT_ME:
                protocol_message = message_manager.protocol_message_encoding(
                    message_received[0], SENDS_TO_ALL, message_received[2], message_received[3])
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == message_manager.OPCODE_LIST_CLIENTS and message_received[1] == "server":
                protocol_message = message_manager.protocol_message_encoding(SERVER_ITSELF, message_received[0],
                                                                             message_manager.OPCODE_LIST_CLIENTS,
                                                                             list_clients())
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == message_manager.OPCODE_EXIT_CLIENT:
                protocol_message = \
                    message_manager.protocol_message_encoding(
                        message_received[1], message_received[0], message_manager.OPCODE_EXIT_CLIENT,
                        "client disconnected")
                message_manager.send_server_message(protocol_message, clients_connected)
                socket_client = get_client_by_name(message_received[0])
                clients_connected.pop(socket_client)
                print("Server sends: %s" % protocol_message)
                break
            if message_received[2] == message_manager.OPCODE_CLOSE_SERVER:
                # checking if user has enough permissions to close server
                if is_moderator(message_received[0]):
                    protocol_message = \
                        message_manager.protocol_message_encoding(
                            SERVER_ITSELF, SENDS_TO_ALL, message_manager.OPCODE_BROADCAST, "server closed")
                    message_manager.send_server_message(protocol_message, clients_connected)
                    clients_connected.clear()
                    stop_server = True
                else:
                    message_data = "You do not have enough permissions to execute that action!"
                    protocol_message = \
                        message_manager.protocol_message_encoding(
                            SERVER_ITSELF, message_received[0], message_manager.OPCODE_PRIVATE_MESSAGE, message_data)
                    message_manager.send_server_message(protocol_message, clients_connected)
        except socket.error as socket_error:
            message_data = str(socket_error) + " | "
            message_data += "client (" + message_received[0] + ") disconnected"
            protocol_message = \
                message_manager.protocol_message_encoding(
                    SERVER_ITSELF, SENDS_TO_ALL, message_manager.OPCODE_ERROR_MESSAGE, message_data)
            clients_connected.pop(client)
            print("Server sends: %s" % protocol_message)
            break
    if message_received[2] == message_manager.OPCODE_CLOSE_SERVER:
        print("Closing server...")
        socket_server.close()
    else:
        receive()


def is_moderator(client_username):
    """
    Check if the client is a moderator
    :param client_username: the new_client username
    """
    for moderator, moderator_name in clients_moderators.items():
        if moderator_name == client_username:
            return True
    return False


def username_available(new_client_name):
    """
    Check if the client is already connected
    :param new_client_name: the new_client's username
    """
    for client_connected, client_connected_name in clients_connected.items():
        if client_connected_name == new_client_name:
            return False
    return True


def get_client_by_name(client_name):
    """
    Search client_connected by name
    :param client_name: client_name
    :return: the client obj or "Not found"
    """
    for client_connected, client_connected_name in clients_connected.items():
        if client_connected_name == client_name:
            return client_connected
    return "Not found"


def list_clients():
    """
    Shows the list of clients_connected
    :return: list of connected clients
    """
    clients_list_names = "clients connected: "
    for client_connected, client_connected_name in clients_connected.items():
        clients_list_names += client_connected_name + " ,"
    clients_list_names = clients_list_names[:-2]
    return clients_list_names


def get_local_ip():
    """
    Get my local ip address
    """
    try:
        # Get the hostname
        hostname = socket.gethostname()
        # Get the local IP address
        local_ip = socket.gethostbyname(hostname)
        return local_ip

    except socket.error as e:
        print(f"Error: {e}")
        return None


def socket_connect():
    """
    Creates a socket and connect it.
    """
    global stop_server
    # new socket, family: Ipv4, type: TCP
    socket_connecting = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    connecting = True
    while connecting:
        try:
            host = get_local_ip()
            port = random.randint(49152, 65535)
            print("Connection attempt...")
            socket_connecting.connect((host, port))
            connecting = False
            print("Server is running and listening on (%s,%s)\n" % (host, port))
        except socket.error as e:
            print(f"Error: {e}")
            print("Server connection error on (%s,%s)" % (host, port))
            user_server = str(input("n = to finish or any key to try again...\n"))
            if user_server == "n":
                stop_server = True
                connecting = False
            else:
                port = random.randint(49152, 65535)
    return socket_connecting


# Main function
if __name__ == "__main__":
    stop_server = False
    socket_server = socket_connect()

    if not stop_server:
        socket_server.listen(10)
        BUFFER_SIZE = 1024
        SERVER_ITSELF = "Server"
        SENDS_TO_ALL = "All clients"

        clients_connected = {}
        """dictionary with all clients connected"""
        clients_moderators = {}
        """dictionary with all moderators clients"""
        # Starting server
        receive()
    else:
        print("Execution finished.")
