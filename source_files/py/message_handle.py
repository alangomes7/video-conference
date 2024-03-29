import socket

# Code message operations
OPCODE_NAME = "name"
OPCODE_CONNECTION_CONFIRMATION = "connection confirmation"
OPCODE_CONNECTION_ERROR = "connection error"
OPCODE_UNKNOWN_OPERATION = "unknown operation"
OPCODE_ECHO = "echo"
OPCODE_PRIVATE_MESSAGE = "private message"
OPCODE_BROADCAST = "broadcast"
OPCODE_BROADCAST_NOT_ME = "broadcast not me"
OPCODE_LIST_CLIENTS = "list clients"
OPCODE_EXIT_CLIENT = "exit client"
OPCODE_ERROR_MESSAGE = "error message"
OPCODE_MESSAGE_CONFIRMATION = "message received"
OPCODE_VIDEO_CONFERENCE = "video conference"
OPCODE_CLIENT_ADDRESS_REQUEST = "request address"
OPCODE_CLIENT_ADDRESS_SEND = "send address"
OPCODE_CLIENT_AVAILABLE = "client available"

# Message data
MESSAGE_REQUESTING = "request connection"
MESSAGE_DECLINED = "connection declined"
MESSAGE_ACCEPTED = "connection accepted"
MESSAGE_SERVER_CLOSED = "server closed"
MESSAGE_YOU_LEAVING = "You are exiting the server"
MESSAGE_SERVER_OPEN = "server open"
MESSAGE_CLIENT_CONNECTED = "client connected"


def protocol_message_encoding(x, y, fx, data="no data"):
    """
    Encode message str to bytes
    :param x: client sender
    :param y: client destination
    :param fx: message function
    :param data: message data
    :return: encoded message
    """
    message = str(x) + " | " + str(y) + " | " + str(fx) + " | " + str(data)
    return message.encode('utf-8')


def protocol_message_decoding(protocol_message):
    """
    Decode message bytes to str
    :param protocol_message: encoded message as bytes
    :return: decoded message
    """
    message = str(protocol_message.decode('utf-8'))
    decoded_message = message.split(" | ")
    if len(decoded_message) < 4:
        decoded_formatted_message = ["", "", "", ""]
        decoded_formatted_message[1] = "server"
        decoded_formatted_message[2] = OPCODE_UNKNOWN_OPERATION
        decoded_formatted_message[3] = decoded_message
        decoded_message = decoded_formatted_message
    return decoded_message


def send_client_message(protocol_message, client):
    """
    Sends the message on client side
    :param protocol_message: encoded message as bytes
    :param client: client sender
    """
    send_message(protocol_message, client)


def send_server_message(protocol_message, clients_connected):
    """
    Sends the message on server side. This functions routes the message from clients in clients_connected_list
    :param protocol_message: encoded message as bytes
    :param clients_connected: The list of clients connected on server
    """
    protocol_message_decoded = protocol_message_decoding(protocol_message)
    if protocol_message_decoded[2] == "broadcast_not_me" or protocol_message_decoded[2] == "broadcast":
        send_server_message_broadcast(protocol_message, clients_connected)
        return protocol_message
    else:
        forwarded_message = False
        destination_client = protocol_message_decoded[1]
        found = clients_connected.get(destination_client, "not found")
        if found != "not found":
            for client_connected_name, client_connected in clients_connected.items():
                if client_connected_name == destination_client:
                    send_message(protocol_message, client_connected)
                    forwarded_message = True
                    break
            # reply message to sender when not found the client destination (echo)
            if not forwarded_message:
                message_data = "Destination client (" + destination_client + ") not found!"
                protocol_message_reply = protocol_message_encoding("server", protocol_message_decoded[0],
                                                                   protocol_message_decoded[2], message_data)
                send_server_message(protocol_message_reply, clients_connected)
                protocol_message = protocol_message_reply
    return protocol_message


def send_server_message_broadcast(protocol_message, clients_connected):
    """
    Send Broadcast messages
    mode: default-all users: any, all users except the sender : "broadcast_not_me"
    :param protocol_message: message formatted as protocol
    :param clients_connected: dictionary with clients connected
    """
    message = protocol_message_decoding(protocol_message)
    mode = message[2]
    client_name = message[0]
    for client_connected_name, client_connected in clients_connected.items():
        if client_connected_name == client_name and mode == OPCODE_BROADCAST_NOT_ME:
            continue
        send_message(protocol_message, client_connected)


def send_message(protocol_message, sock):
    """
    Sends the message and handle if message was not sent.
    """
    try:
        # This will retrieve the socket error, if any
        message_code = sock.send(protocol_message)
        return message_code
    except socket.error:
        print("Socket closed.")
