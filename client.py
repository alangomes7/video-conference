import socket
import threading
import time
import message as message_manager


def client_receive():
    """
    Receive messages from server and handle with them
    """
    global stop_client
    message_received = ""
    while not stop_client:
        try:
            message_received = message_manager.protocol_message_decoding(socket_client.recv(BUFFER_SIZE))
            # client actions
            if message_received[2] == "name":
                message_manager.send_client_message(
                    message_manager.protocol_message_encoding(name, "server", "name", name), socket_client)
                continue
            if message_received[2] == \
                    "Unknown_operation" or message_received[2] == "echo" or message_received[2] == "private_message" \
                    or message_received[2] == "broadcast_not_me" \
                    or message_received[2] == "connection_confirmation" \
                    or (message_received[2] == "broadcast" and message_received[3] != "server closed"):
                print_reply(message_received)
                continue
            if message_received[2] == "list_clients":
                print_reply(message_received)
                continue
            if message_received[2] == "connection_error" or message_received[2] == "exit" \
                    or (message_received[2] == "broadcast" and message_received[3] == "server closed"):
                print_reply(message_received)
                print("Closing client...")
                stop_client = True
                time.sleep(2)  # it needs waiting a little bit more
                continue
        except socket.error as socket_error:
            print("Error with client connection | %s" % socket_error)
            print_reply(message_received)
            stop_client = True
            time.sleep(2)  # it needs waiting a little bit more
            break
    socket_client.close()


def client_send():
    """
    Send client messages to the server
    """
    global stop_client
    time_to_wait = 0.3
    while not stop_client:
        # wait the server answer
        time.sleep(time_to_wait)
        time_to_wait = 0.3
        message = ""
        if not stop_client:
            operation = menu()
            match operation:
                case 1:  # echo message
                    print("--- Sent an echo message ---\n")
                    message_data = str(input("Echo message: \n"))
                    message = message_manager.protocol_message_encoding(name, name, "echo", message_data)
                case 2:  # list clients
                    print("--- Listing all clients connected ---\n")
                    message = message_manager.protocol_message_encoding(name, "server", "list_clients")
                case 3:  # private message
                    print("--- Sent a message to an specific user ---\n")
                    destination_client = str(input("Input the client to send the private message:\n"))
                    private_message = str(input("Input the private message to %s:\n" % destination_client))
                    message = message_manager.protocol_message_encoding(
                        name, destination_client, "private_message", private_message)
                case 4:  # broadcast
                    print("--- Sent a message to everyone on the Server ---\n")
                    time_to_wait = 1.3
                    broadcast_mode = str(input("Broadcast message except you? y/n\n"))
                    if broadcast_mode == "y":
                        operation = "broadcast_not_me"
                    message_data = str(input("Broadcast message: \n"))
                    message = message_manager.protocol_message_encoding(name, "all clients", operation, message_data)
                case 5:  # exit: client is leaving
                    print("--- You are leaving the server and are also closing yourself ---\n")
                    time_to_wait = 1.3
                    message_data = "client " + name + " closed"
                    message = message_manager.protocol_message_encoding(name, "server", "exit", message_data)
                case 6:  # close server. Everyone will be disconnected and closed
                    print("--- You are closing the server to everyone ---\n")
                    time_to_wait = 1.3
                    message_data = "close server"
                    message = message_manager.protocol_message_encoding(name, "server", "close_server", message_data)
                case default:
                    message = message_manager.protocol_message_encoding(name, "server", "Unknown operation", operation)
        if stop_client:
            break
        message_manager.send_client_message(message, socket_client)
    print("Closing client...")


def menu():
    # Menu
    user_answer = ""
    options = "Options: \n"
    options += "1 - echo\n"
    options += "2 - list clients\n"
    options += "3 - private message\n"
    options += "4 - broadcast message\n"
    options += "5 - exit\n"
    options += "6 - close server\n"
    print(options)
    try:
        user_answer = int(input("Input option's number:\n"))
    except ValueError:
        user_answer = 0
    finally:
        return user_answer


def print_reply(protocol_message_decoded):
    """
    Format the print to user
    :param protocol_message_decoded: message to extract the data to print
    """
    reply = "\nIncoming message:\n"
    reply += "   Client sender: " + protocol_message_decoded[0] + "\n"
    reply += "   Client destination: " + protocol_message_decoded[1] + "\n"
    reply += "   Operation: " + protocol_message_decoded[2] + "\n"
    reply += "   Message: " + "\n"
    reply += "      " + protocol_message_decoded[3] + "\n"
    print(reply)


if __name__ == "__main__":
    # client's setup
    name = str(input('write down your name: \n'))
    # new socket, family: Ipv4, type: TCP
    socket_client = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    host = "localhost"
    port = 1234
    socket_client.connect((host, port))
    BUFFER_SIZE = 1024
    stop_client = False

    # receive thread
    receive_thread = threading.Thread(target=client_receive)
    receive_thread.start()

    # send thread
    send_thread = threading.Thread(target=client_send)
    send_thread.start()
