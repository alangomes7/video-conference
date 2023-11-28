import socket
import threading
import time
import message as message_manager

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, GLib, Gst, GLib

Gst.init(None)


def client_send():
    global stop_client, wait_server
    while not stop_client:
        message_protocol_options = client_menu_message()
        message_manager.send_client_message(message_protocol_options, socket_client)
        # wait_server = True


def client_menu_message():
    operation = menu()
    message_data = ""
    message_destination = "server"
    message_code_operation = message_manager.OPCODE_UNKNOWN_OPERATION
    if operation == 1:  # echo message
        print("--- Sent an echo message ---\n")
        message_data = str(input("Echo message: \n"))
        message_destination = name
        message_code_operation = message_manager.OPCODE_ECHO
    elif operation == 2:  # list clients
        print("--- Listing all clients connected ---\n")
        message_code_operation = message_manager.OPCODE_LIST_CLIENTS
    elif operation == 3:  # private message
        print("--- Sent a message to a specific user ---\n")
        message_destination = str(input("Input the client to send the private message:\n"))
        message_data = str(input("Input the private message to %s:\n" % message_destination))
        message_code_operation = message_manager.OPCODE_PRIVATE_MESSAGE
    elif operation == 4:  # broadcast
        print("--- Sent a message to everyone on the Server ---\n")
        broadcast_mode = str(input("Broadcast message except you? y/n\n"))
        if broadcast_mode == "y":
            message_code_operation = message_manager.OPCODE_BROADCAST_NOT_ME
        else:
            message_code_operation = message_manager.OPCODE_BROADCAST
        message_data = str(input("Broadcast message: \n"))
    elif operation == 5:  # exit: client is leaving
        print("--- You are leaving the server and are also closing yourself ---\n")
        message_code_operation = message_manager.OPCODE_EXIT_CLIENT
    elif operation == 6:  # video conference
        print("--- Video conference ---\n")
        message_destination = str(input("Input the name of user to connect:\n"))
        message_code_operation = message_manager.OPCODE_VIDEO_CONFERENCE
        message_data = message_manager.MESSAGE_REQUESTING
    return message_manager.protocol_message_encoding(name, message_destination, message_code_operation, message_data)


def client_receive():
    global stop_client
    message_received = ""
    while not stop_client:
        try:
            message_received = message_manager.protocol_message_decoding(socket_client.recv(BUFFER_SIZE))
            handle_received_message(message_received)
        except socket.error as socket_error:
            handle_client_error(socket_error)
    print("Closing client (receive)...")


def handle_received_message(protocol_message_decoded):
    global stop_client, socket_client
    if stop_client:
        return

    if protocol_message_decoded[2] == message_manager.OPCODE_NAME:
        protocol_message = message_manager.protocol_message_encoding(name, "server", message_manager.OPCODE_NAME, name)
        message_manager.send_client_message(protocol_message, socket_client)

    elif protocol_message_decoded[2] == message_manager.OPCODE_CONNECTION_CONFIRMATION:
        my_address(protocol_message_decoded)
        print_reply(protocol_message_decoded)

    elif protocol_message_decoded[2] in (
            message_manager.OPCODE_UNKNOWN_OPERATION, message_manager.OPCODE_ECHO,
            message_manager.OPCODE_PRIVATE_MESSAGE, message_manager.OPCODE_LIST_CLIENTS,
            message_manager.OPCODE_BROADCAST_NOT_ME, message_manager.OPCODE_MESSAGE_CONFIRMATION,
            message_manager.OPCODE_CONNECTION_CONFIRMATION):
        print_reply(protocol_message_decoded)

    elif protocol_message_decoded[2] in (message_manager.OPCODE_CONNECTION_ERROR, message_manager.OPCODE_EXIT_CLIENT):
        close_client(protocol_message_decoded)

    # Broadcast Messages
    if protocol_message_decoded[2] == message_manager.OPCODE_BROADCAST:
        if protocol_message_decoded[3] == message_manager.MESSAGE_SERVER_CLOSED:
            close_client(protocol_message_decoded)

        else:
            if message_manager.MESSAGE_YOU_LEAVING in protocol_message_decoded[3]:
                close_client(protocol_message_decoded)

            if not (message_manager.MESSAGE_YOU_LEAVING in protocol_message_decoded[3]):
                print_reply(protocol_message_decoded)

    # Video conference Messages
    if protocol_message_decoded[2] == message_manager.OPCODE_VIDEO_CONFERENCE:
        if protocol_message_decoded[3] == message_manager.MESSAGE_REQUESTING:
            print("Message requesting")
            answer = str(input("Accept call from " + protocol_message_decoded[1] + "? y/n"))
            if answer == "y":
                protocol_message = message_manager.protocol_message_encoding(
                    name, protocol_message_decoded[0], message_manager.OPCODE_VIDEO_CONFERENCE,
                    message_manager.MESSAGE_ACCEPTED)
                message_manager.send_client_message(protocol_message, socket_client)
            if answer == "n":
                protocol_message = message_manager.protocol_message_encoding(
                    name, protocol_message_decoded[0], message_manager.OPCODE_VIDEO_CONFERENCE,
                    message_manager.MESSAGE_DECLINED)
                message_manager.send_client_message(protocol_message, socket_client)
            else:
                pass
        if protocol_message_decoded[3] == message_manager.MESSAGE_DECLINED:
            print("Connection declined by " + protocol_message_decoded[0])
        if protocol_message_decoded[3] == message_manager.MESSAGE_ACCEPTED:
            protocol_message = message_manager.protocol_message_encoding(
                name, protocol_message_decoded[0], message_manager.OPCODE_CLIENT_ADDRESS_REQUEST)
            message_manager.send_client_message(protocol_message, socket_client)

    # address messages
    if protocol_message_decoded[2] == message_manager.OPCODE_CLIENT_ADDRESS_REQUEST:
        message_data = my_ip + ";" + my_port
        protocol_message = message_manager.protocol_message_encoding(
            name, protocol_message_decoded[0], message_manager.OPCODE_CLIENT_ADDRESS_SEND, message_data)
        message_manager.send_client_message(protocol_message, socket_client)
    if protocol_message_decoded[2] == message_manager.OPCODE_CLIENT_ADDRESS_SEND:
        print(protocol_message_decoded[3])
        print("Video call started!")


def close_client(protocol_message_decoded):
    global stop_client
    print_reply(protocol_message_decoded)
    stop_client = True
    time.sleep(3)
    socket_client.close()
    print("Closing client (message received: exit)...")


def handle_client_error(socket_error):
    global stop_client
    if stop_client:
        return

    print(socket_error)
    message_data = "Error with client connection (" + str(socket_error.args[0]) + ")"
    message_protocol = message_manager.protocol_message_encoding(
        name, name, message_manager.OPCODE_ERROR_MESSAGE, message_data)
    print_reply(message_manager.protocol_message_decoding(message_protocol))
    stop_client = True
    time.sleep(2)  # it needs waiting a little bit more
    socket_client.close()


def menu():
    options = "Options: \n"
    options += "1 - echo\n"
    options += "2 - list clients\n"
    options += "3 - private message\n"
    options += "4 - broadcast message\n"
    options += "5 - exit\n"
    options += "6 - Video Conference\n"
    print(options)
    user_answer = ""
    try:
        user_answer = int(input("Input option's number:\n"))
    except ValueError:
        user_answer = 0
    finally:
        return user_answer


def print_reply(protocol_message_decoded):
    print("Server reply:\n")
    print(protocol_message_decoded[3])


def my_address(message_data):
    global my_ip, my_port
    data = message_data[3]
    adrress = data.split("('")[1].split("',")
    my_ip = adrress[0]
    my_port = adrress[1][:-1]
    print(my_ip)


def socket_connect():
    global stop_client
    # new socket, family: Ipv4, type: TCP
    socket_connecting = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    connecting = True
    while connecting:
        host = str(input("Please input the server's ip:\n"))
        port = 1234  # int(input("Please input the server's port:\n"))
        try:
            # Time out necessary to connect to a specific ip
            socket_connecting.connect((host, port))
            # Removes time out. It needs to wait the user's input
            socket_connecting.settimeout(None)
            connecting = False
        except socket.error as e:
            print(f"Error: {e}")
            print("Client connection error on (%s,%s)" % (host, port))
            user_client = str(input("n = to finish or any key to try again...\n"))
            if user_client == "n":
                stop_client = True
                connecting = False
    return socket_connecting


# Main function
if __name__ == "__main__":
    stop_client = False
    socket_client = socket_connect()
    if not stop_client:
        wait_server = True
        BUFFER_SIZE = 1024
        name = str(input("Please, input your username:\n"))
        message_protocol = message_manager.protocol_message_encoding(name, "server", message_manager.OPCODE_NAME, name)
        # Send the first message to the server
        message_manager.send_client_message(message_protocol, socket_client)

        # Thread
        thread_receive = threading.Thread(target=client_receive)
        thread_receive.start()

        thread_send = threading.Thread(target=client_send, daemon=True)
        thread_send.start()

        my_ip = ""
        my_port = 0

        while not stop_client:
            pass
        print("Finished.")
