import queue
import socket
import threading
import time
import message as message_manager
import asyncio
from vidstream import CameraClient, StreamingServer


class MessageBuffer:
    """
    Class that buffer received messages.
    """
    def __init__(self):
        self.message_queue = queue.Queue()

    def add_message(self, message):
        """
        Adds messages on buffer.
        :param message: message to be buffered.
        """
        self.message_queue.put(message)

    def process_messages(self):
        """
        Process buffered messages.
        """
        while not self.message_queue.empty():
            message = self.message_queue.get()
            handle_received_message(message)


async def client_send():
    """
    Runs the menu and then send the answer to server.
    """
    print("waiting...")
    count = 0
    while count < 10:
        time.sleep(1)
        if count % 3 == 0:
            print(".")
        count += 1
    print("")
    if run_menu:
        message_protocol_options = client_menu_message()
        message_manager.send_client_message(message_protocol_options, socket_client)


def client_menu_message():
    """
    Prints the menu.
    """
    global run_menu
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
        run_menu = False
        message_destination = str(input("Input the name of user to connect:\n"))
        message_code_operation = message_manager.OPCODE_VIDEO_CONFERENCE
        message_data = message_manager.MESSAGE_REQUESTING
    return message_manager.protocol_message_encoding(name, message_destination, message_code_operation, message_data)


def client_receive():
    """
    Await to messages from server or from another client.
    """
    global stop_client
    message_buffer = MessageBuffer()
    while not stop_client:
        try:
            message_received = message_manager.protocol_message_decoding(socket_client.recv(BUFFER_SIZE))
            print(message_received)
            message_buffer.add_message(message_received)
            thread = threading.Thread(target=message_buffer.process_messages, daemon=True)
            thread.start()
        except socket.error as socket_error:
            handle_client_receive_messages_error(socket_error)
    print("Closing client (receive)...")


def receive_call(ip_to_receive, port_to_receive):
    """
    Opens the server to receive the call.
    :param ip_to_receive: ip to open the server.
    :param port_to_receive: port to open the server.
    """
    global stop_call
    receiving_video_stream = StreamingServer(ip_to_receive, port_to_receive)
    thread_receiving_video_stream = threading.Thread(target=receiving_video_stream.start_server())
    thread_receiving_video_stream.start()
    print("server opened and wait a call...")
    while not stop_call:
        continue
    receiving_video_stream.stop_server()


def send_call(ip_to_send, port_to_send):
    """
    Connect to server through (ip, port) and sends the call data.
    :param ip_to_send: ip to connect.
    :param port_to_send: port to connect.
    """
    global stop_call
    sending_video_streaming = CameraClient(ip_to_send, port_to_send)
    thread_sending_video_streaming = threading.Thread(target=sending_video_streaming.start_stream())
    thread_sending_video_streaming.start()
    print("sending_video_stream")
    while not stop_call:
        continue
    sending_video_streaming.stop_stream()


def control_call():
    """
    Blocks the program execution and wait to client message to send a signal to close the call.
    """
    global stop_call
    stop_call = False
    print("Type any key to stop the call...\n")
    while not stop_call:
        close_call = str(input(""))
        if close_call != "":
            stop_call = True
        continue


def make_video_call(ip, port, create_server=1):
    """
    Creates threads to receive or send call data. Default: create call server.
    :param ip: ip to connect.
    :param port: port to connect.
    :param create_server: indicates if the operation is for create a server or send to server.
    """
    if create_server == 1:
        # wait stream
        thread_receive_call = threading.Thread(target=receive_call, args=(ip, port))
        thread_receive_call.start()
    else:
        # send stream
        thread_send_call = threading.Thread(target=send_call, args=(ip, port,))
        thread_send_call.start()
        # block here in send stream
        control_call()


def save_client_call_address(ip, port):
    """
    Save the another client address.
    """
    global client_call_address
    address = ip + ";" + str(port)
    client_call_address = address


def get_my_address():
    """
    Gets my address.
    """
    global my_ip, my_port
    return my_ip + ":" + str(my_port)


def get_client_call_address():
    """
    Get another client address.
    """
    global client_call_address
    return client_call_address


def handle_received_message(protocol_message_decoded):
    """
    Process the incoming message.
    :param protocol_message_decoded: incoming message to process.
    """
    global stop_client, socket_client, run_menu, my_ip, my_port
    if stop_client:
        return

    if protocol_message_decoded[2] == message_manager.OPCODE_NAME:
        protocol_message = message_manager.protocol_message_encoding(name, "server", message_manager.OPCODE_NAME, name)
        message_manager.send_client_message(protocol_message, socket_client)

    if len(protocol_message_decoded) > 4:
        if "connect again and use another one" in protocol_message_decoded[len(protocol_message_decoded) - 1]:
            print_reply(protocol_message_decoded)
            run_menu = False
            stop_client = True
        else:
            my_address(protocol_message_decoded)
            print_reply(protocol_message_decoded)
            run_menu = True

    elif protocol_message_decoded[2] == message_manager.OPCODE_CONNECTION_ERROR:
        print_reply(protocol_message_decoded)
        run_menu = False

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
            run_menu = False

        else:
            if message_manager.MESSAGE_YOU_LEAVING in protocol_message_decoded[3]:
                close_client(protocol_message_decoded)
                run_menu = False

            if not (message_manager.MESSAGE_YOU_LEAVING in protocol_message_decoded[3]):
                print_reply(protocol_message_decoded)

    # Video conference Messages
    if protocol_message_decoded[2] == message_manager.OPCODE_VIDEO_CONFERENCE:
        run_menu = False

        if protocol_message_decoded[3] == message_manager.MESSAGE_REQUESTING:
            print("B1")
            message_data = message_manager.MESSAGE_ACCEPTED + ":" + get_my_address()
            protocol_message = message_manager.protocol_message_encoding(
                name, protocol_message_decoded[0], message_manager.OPCODE_VIDEO_CONFERENCE, message_data)
            message_manager.send_client_message(protocol_message, socket_client)
            run_menu = False

        if message_manager.MESSAGE_ACCEPTED in protocol_message_decoded[3]:
            print("A2")
            client_answer_address = protocol_message_decoded[3].split(":")
            ip = client_answer_address[1]
            port = client_answer_address[2]
            save_client_call_address(ip, port)

            message_data = get_my_address()
            protocol_message = message_manager.protocol_message_encoding(
                name, protocol_message_decoded[0], message_manager.OPCODE_CLIENT_ADDRESS_REQUEST, message_data)
            message_manager.send_client_message(protocol_message, socket_client)
            run_menu = False

    # address messages
    if protocol_message_decoded[2] == message_manager.OPCODE_CLIENT_ADDRESS_REQUEST:
        print("B2")

        client_answer_address = protocol_message_decoded[3].split(":")
        ip = client_answer_address[0]
        port = client_answer_address[1]
        save_client_call_address(ip, port)

        make_video_call(my_ip, int(my_port) + 1, 1)

        # send server address
        protocol_message = message_manager.protocol_message_encoding(
            name, protocol_message_decoded[0], message_manager.OPCODE_CLIENT_ADDRESS_SEND,
            message_manager.MESSAGE_SERVER_OPEN)
        message_manager.send_client_message(protocol_message, socket_client)
        run_menu = False

    if protocol_message_decoded[2] == message_manager.OPCODE_CLIENT_ADDRESS_SEND \
            and message_manager.MESSAGE_SERVER_OPEN in protocol_message_decoded[3]:
        print("A3")
        make_video_call(my_ip, int(my_port) + 1, 1)

        protocol_message = message_manager.protocol_message_encoding(
            name, protocol_message_decoded[0], message_manager.OPCODE_CLIENT_AVAILABLE,
            message_manager.MESSAGE_SERVER_OPEN)
        message_manager.send_client_message(protocol_message, socket_client)

    if protocol_message_decoded[2] == message_manager.OPCODE_CLIENT_AVAILABLE \
            and protocol_message_decoded[3] == message_manager.MESSAGE_SERVER_OPEN:
        print("B3")
        protocol_message = message_manager.protocol_message_encoding(
            name, protocol_message_decoded[0], message_manager.OPCODE_CLIENT_AVAILABLE,
            message_manager.MESSAGE_CLIENT_CONNECTED)
        message_manager.send_client_message(protocol_message, socket_client)

        # send and wait to finish
        address_send = get_client_call_address()
        ip_address_send = address_send.split(";")[0]
        port_address_send = int(address_send.split(";")[1]) + 1
        make_video_call(ip_address_send, port_address_send, 2)
        control_call()
        run_menu = True

    if protocol_message_decoded[2] == message_manager.OPCODE_CLIENT_AVAILABLE \
            and protocol_message_decoded[3] == message_manager.MESSAGE_CLIENT_CONNECTED:
        print("A4")
        # send and wait to finish
        address_send = get_client_call_address()
        ip_address_send = address_send.split(";")[0]
        port_address_send = int(address_send.split(";")[1]) + 1
        make_video_call(ip_address_send, port_address_send, 2)
        control_call()
        run_menu = True

    asyncio.run(user_menu())


def close_client(protocol_message_decoded):
    """
    Close the client and prints the messages containing all information by the operation.
    :param protocol_message_decoded: information by operation.
    """
    global stop_client
    print_reply(protocol_message_decoded)
    stop_client = True
    time.sleep(3)
    socket_client.close()
    print("Closing client (message received: exit)...")


def handle_client_receive_messages_error(socket_error):
    """
    Checks what happened with client connection and prints the message error.
    :param socket_error: error socket.
    """
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
    """
    Prints the menu to client decides what to do.
    """
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
    """
    Prints to client the message from server.
    """
    print("Server reply:")
    print(protocol_message_decoded[3])


def my_address(message_data):
    """
    Saves my address.
    :param message_data: contains my address.
    """
    global my_ip, my_port
    data = message_data[6]
    address = data.split("('")[1].split("',")
    if len(address) >= 2:
        my_ip = address[0].strip()
        my_port = address[1][:-1].split()
        my_port = my_port[0]
        print(my_ip, my_port)


def socket_connect():
    """
    Creates a connection.
    """
    global stop_client
    # new socket, family: Ipv4, type: TCP
    socket_connecting = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    connecting = True
    while connecting:
        host = str(input("Please input the server's ip:\n"))
        port = 5500  # int(input("Please input the server's port:\n"))
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


async def user_menu():
    """
    Async method to avoid input blocking on menu.
    """
    if run_menu:
        asyncio.create_task(client_send())
        await asyncio.sleep(1)
    else:
        print("Operation deactivated menu")


# Main function
if __name__ == "__main__":
    stop_client = False
    socket_client = socket_connect()
    run_menu = True
    if not stop_client:
        stop_call = False
        wait_server = True
        BUFFER_SIZE = 1024
        client_call_address = ";"
        name = str(input("Please, input your username:\n"))
        message_protocol = message_manager.protocol_message_encoding(name, "server", message_manager.OPCODE_NAME, name)
        # Send the first message to the server
        message_manager.send_client_message(message_protocol, socket_client)

        # Thread
        thread_receive = threading.Thread(target=client_receive)
        thread_receive.start()

        my_ip = ""
        my_port = 0

        while not stop_client:
            pass
        print("Finished.")
