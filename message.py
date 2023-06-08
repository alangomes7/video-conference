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
    return message.split(" | ")


def send_client_message(protocol_message, client):
    """
    Sends the message on client side
    :param protocol_message: encoded message as bytes
    :param client: client sender
    """
    client.send(protocol_message)


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
        for client_connected, client_connected_name in clients_connected.items():
            if client_connected_name == destination_client:
                client_connected.send(protocol_message)
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
    for client_connected, client_connected_name in clients_connected.items():
        if client_connected_name == client_name and mode == "broadcast_not_me":
            continue
        client_connected.send(protocol_message)
