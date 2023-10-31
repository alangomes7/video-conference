import threading
import socket
import message as message_manager

# server setup
host = "localhost"
port = 1234
socket_server = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
socket_server.bind((host, port))
socket_server.listen(10)
BUFFER_SIZE = 1024
close_server = False
clients_connected = {}
"""dictionary with all clients connected"""


def receive():
    """
    receive client's connection: the server.
    """
    print("Server is running and listening...")
    global close_server
    while not close_server:
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
                message_data = "You are now connected to the server in " + str(address)
                message_protocol = message_manager.protocol_message_encoding(
                    "server", received_message[3], "connection_confirmation", message_data)
                message_manager.send_server_message(message_protocol, clients_connected)
                print("Sent: " + message_protocol.decode('utf-8'))
                # now using threads to allow multiple connections and actions simultaneously
                thread = threading.Thread(target=handle_client, args=(socket_client,), daemon=True)
                thread.start()
            else:
                message_data = "This username is already taken. "
                message_data += "You need to connect again and use another one"
                new_client_name = "new_client: " + received_message[3]
                protocol_message = message_manager.protocol_message_encoding("server", new_client_name,
                                                                             "connection_error", message_data)
                socket_client.send(protocol_message)
                print(protocol_message)
                break
        except socket.error as socket_error:
            if close_server:
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
    global close_server
    while not close_server:
        try:
            message_received = message_manager.protocol_message_decoding(client.recv(BUFFER_SIZE))
            print("Server receive: %s" % message_received)
            # server actions
            if message_received[2] == "Unknown operation":
                message_data = "Operation (" + message_received[3] + ") is not supported"
                protocol_message = message_manager.protocol_message_encoding("server", message_received[0],
                                                                             "Unknown_operation",
                                                                             message_data)
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == "echo":
                protocol_message = message_manager.protocol_message_encoding(message_received[0], message_received[0],
                                                                             "echo",
                                                                             message_received[3])
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == "private_message":
                protocol_message = message_manager.protocol_message_encoding(message_received[0], message_received[1],
                                                                             "private_message",
                                                                             message_received[3])
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == "broadcast" or message_received[2] == "broadcast_not_me":
                protocol_message = message_manager.protocol_message_encoding(
                    message_received[0], "all clients", message_received[2], message_received[3])
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == "list_clients" and message_received[1] == "server":
                protocol_message = message_manager.protocol_message_encoding("server", message_received[0],
                                                                             "list_clients",
                                                                             list_clients())
                print("Server sends: %s" % protocol_message)
                message_manager.send_server_message(protocol_message, clients_connected)
                continue
            if message_received[2] == "exit":
                protocol_message = \
                    message_manager.protocol_message_encoding(
                        message_received[1], message_received[0], "exit", "client disconnected")
                message_manager.send_server_message(protocol_message, clients_connected)
                socket_client = get_client_by_name(message_received[0])
                clients_connected.pop(socket_client)
                print("Server sends: %s" % protocol_message)
                break
            if message_received[2] == "close_server":
                protocol_message = \
                    message_manager.protocol_message_encoding(
                        "server", "all clients", "broadcast", "server closed")
                message_manager.send_server_message(protocol_message, clients_connected)
                clients_connected.clear()
                close_server = True
        except socket.error as socket_error:
            message_data = str(socket_error) + " | "
            message_data += "client (" + message_received[0] + ") disconnected"
            protocol_message = \
                message_manager.protocol_message_encoding(
                    "server", "server", "error_message", message_data)
            clients_connected.pop(client)
            print("Server sends: %s" % protocol_message)
            break
    if message_received[2] == "close_server":
        print("Closing server...")
        socket_server.close()
    else:
        receive()


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


# Main function
if __name__ == "__main__":
    receive()
