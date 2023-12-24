# Helper Functions
import socket
from datetime import datetime
import os
import message_handle as message_manager

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


def create_folder(folder_path):
    """Creates a folder to save all log messages.
    :param folder_path: path to create a folder."""
    try:
        if os.path.exists(folder_path):
            pass
        else:
            os.makedirs(folder_path)
    except OSError as e:
        print("Error creating log folder")


def get_time():
    """Gets the current time to log messages in a list. [0] = time without blank spaces, [1] = time with blank
    spaces"""
    current_time = datetime.now()
    formatted_time = [current_time.strftime("%Y-%m-%d_%H-%M-%S"), current_time.strftime("%Y-%m-%d %H:%M:%S")]
    return formatted_time


def get_client_socket_by_name(client_name, clients_connected):
    """Function to search for a client by name.
    :param client_name: client name to scour.
    :param clients_connected: list of connected clients."""
    client_socket = clients_connected.get(client_name, "not found")
    return client_socket


def dict_empty(dict_clients):
    """Verify if dict is empty.
    :param dict_clients: dictionary with all clients connected."""
    return not bool(dict_clients)


def save_log_file(log_message, log_file_name):
    """Saves log messages into a file.
    :param log_message: log message to be saved on log file.
    :param log_file_name: log file name to save messages."""
    try:
        with open(log_file_name, 'a') as file:
            file.write(str(log_message) + '\n')
    except OSError as e:
        print(e)


def update_log_interface(log_message, text_buffer):
    """Prints log messages on the interface.
    :param log_message: log message to be printed on screen.
    :param text_buffer: text buffer by interface."""
    end_iter = text_buffer.get_end_iter()
    text_buffer.insert(end_iter, log_message + "\n")


def log_file(log_message, log_file_name, text_buffer):
    """Saves log file and prints on the interface.
    :param log_message: log message to be printed on screen and saved on log file.
    :param log_file_name: log file name to save messages.
    :param text_buffer: text buffer by interface."""
    GLib.idle_add(save_log_file, get_time()[0] + " - " + str(log_message), log_file_name)
    GLib.idle_add(update_log_interface, get_time()[1] + " - " + str(log_message), text_buffer)


def message_confirmation(user_sender, message_code, server_name):
    """Sends the message confirmation to a client.
    :param user_sender: user that sends the message.
    :param message_code: message code."""
    if message_code in (message_manager.OPCODE_PRIVATE_MESSAGE, message_manager.OPCODE_BROADCAST_NOT_ME):
        server_sends(message_manager.protocol_message_encoding(
            server_name, user_sender, message_manager.OPCODE_MESSAGE_CONFIRMATION, "message sent"))


def server_sends(protocol_message, clients_connected, socket_client=None):
    """Prints the server message and sends it.
    :param protocol_message: message to send.
    :param clients_connected: list of connected clients.
    :param socket_client: client that sends the message. Default is None."""
    log_file("Server sends: %s" % protocol_message)
    if not socket_client:
        if clients_connected:
            message_manager.send_server_message(protocol_message, clients_connected)
        else:
            log_file("Server clients is empty!")
    else:
        socket_client.send(protocol_message)


def get_all_list(clients_connected):
    """Function to show the list of connected clients in all pairs (clients, address).
    :param clients_connected: list of connected clients."""
    all_items = ""
    for key, value in clients_connected.items():
        address = str(value).split("raddr=")[1][:-1]
        all_items += key + " -> " + address + "\n"
    return all_items


def add_client(username, clients_connected, client_socket):
    """Add client to the dictionary.
    :param username: username by client socket.
    :param clients_connected: list of connected clients.
    :param client_socket: socket client to add."""
    clients_connected[username] = client_socket


def remove_client(client_username, clients_connected):
    """Removes a client from the dictionary.
    :param clients_connected: list of connected clients.
    :param client_username: username by client."""
    clients_connected.pop(client_username, -1)


def get_local_ip():
    """Function to get the local IP address."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip

    except socket.error as e:
        log_file(f"Error: {e}")
        return None


def socket_connect_server(server_running, log_file_name, text_buffer):
    """Function to create a socket and connect it.
    :param server_running: flag to indicate if the server is running or not.
    :param log_file_name: log file name to save messages.
    :param text_buffer: text buffer by interface."""
    socket_connecting = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    host = get_local_ip()
    port = 5500
    try:
        if not server_running:
            log_file("Connection attempt...", log_file_name, text_buffer)
            socket_connecting.bind((host, port))
            socket_connecting.listen(10)
            log_file("Server is running and listening on (%s,%s)\n" % (host, port), log_file_name, text_buffer)
            return socket_connecting
        else:
            return None
    except socket.error as e:
        log_file(f"Error: {e}", log_file_name, text_buffer)
        log_file("Server connection error on (%s,%s)" % (host, port), log_file_name, text_buffer)
        return None
