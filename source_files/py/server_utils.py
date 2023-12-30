import os
import socket
from datetime import datetime
import message_handle as message_manager
import gi
from gi.repository import GLib

gi.require_version("Gtk", "3.0")


def get_time(spaces=True):
    """
    Get the current time in a specific format.

    Args:
        spaces (bool): If True, include spaces in the formatted time.

    Returns:
        str: Formatted current time.
    """
    current_time = datetime.now()
    if spaces:
        return current_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return current_time.strftime("%Y-%m-%d_%H-%M-%S")


def get_client_socket_by_name(client_name, clients_connected):
    """
    Get a client socket by name from the dictionary of connected clients.

    Args:
        client_name (str): Name of the client.
        clients_connected (dict): Dictionary containing connected clients.

    Returns:
        socket or str: Socket object if found, or "not found" if not found.
    """
    return clients_connected.get(client_name, "not found")


def dict_empty(dict_clients):
    """
    Check if a dictionary is empty.

    Args:
        dict_clients (dict): The dictionary to check.

    Returns:
        bool: True if the dictionary is empty, False otherwise.
    """
    return not bool(dict_clients)


def create_folder(folder_path):
    """
    Create a folder and handle the case when it already exists.

    Args:
        folder_path (str): Path to the folder.
    """
    try:
        os.makedirs(folder_path, exist_ok=True)
    except OSError as e:
        raise Exception(f"Error creating log folder: {e}")


def get_all_list(clients_connected):
    """
    Get a formatted string listing all connected clients.

    Args:
        clients_connected (dict): Dictionary containing connected clients.

    Returns:
        str: Formatted string listing all connected clients.
    """
    all_items = ""
    for key, value in clients_connected.items():
        address = str(value).split("raddr=")[1][:-1]
        all_items += f"{key} -> {address}\n"
    return all_items


def add_client(username, clients_connected, client_socket):
    """
    Add a client to the dictionary of connected clients.

    Args:
        username (str): Username of the client.
        clients_connected (dict): Dictionary containing connected clients.
        client_socket: Socket object of the client.
    """
    clients_connected[username] = client_socket


def remove_client(client_username, clients_connected):
    """
    Remove a client from the dictionary of connected clients.

    Args:
        client_username (str): Username of the client to be removed.
        clients_connected (dict): Dictionary containing connected clients.
    """
    clients_connected.pop(client_username, None)


class ServerUtils:
    def __init__(self, log_file_name, text_buffer):
        """
        Initialize ServerUtils.

        Args:
            log_file_name (str): File to save the log messages.
            text_buffer: Buffer to display log messages.
        """
        self.log_file_name = log_file_name
        self.text_buffer = text_buffer

    def save_log_file(self, log_message):
        """
        Save log messages into a file.

        Args:
            log_message (str): Log message to save.
        """
        try:
            with open(self.log_file_name, 'a') as file:
                file.write(f"{log_message}\n")
        except OSError as e:
            raise Exception(f"Error saving log file: {e}")

    def update_log_interface(self, log_message):
        """
        Update the log interface with a log message.

        Args:
            log_message (str): Log message to be printed on the screen.
        """
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, f"{log_message}\n")

    def log_file(self, log_message):
        """
        Save log file and update the log interface.

        Args:
            log_message (str): Log message to be printed on the screen and saved in the log file.
        """
        GLib.idle_add(self.save_log_file, f"{get_time()} - {log_message}")
        GLib.idle_add(self.update_log_interface, f"{get_time()} - {log_message}")

    def message_confirmation(self, user_sender, message_code, server_name, clients_connected):
        """
        Send the message confirmation to a client.

        Args:
            user_sender (str): User that sends the message.
            message_code: Message code.
            server_name (str): Name of the server to answer.
            clients_connected (dict): Dictionary containing connected clients.
        """
        if message_code in (message_manager.OPCODE_PRIVATE_MESSAGE, message_manager.OPCODE_BROADCAST_NOT_ME):
            self.server_sends(message_manager.protocol_message_encoding(
                server_name, user_sender, message_manager.OPCODE_MESSAGE_CONFIRMATION, "message sent"),
                clients_connected)

    def server_sends(self, protocol_message, clients_connected, socket_client=None):
        """
        Print the server message and send it.

        Args:
            protocol_message (str): Message to send.
            clients_connected (dict): Dictionary containing connected clients.
            socket_client: Client that sends the message. Default is None.
        """
        self.log_file(f"Server sends: {protocol_message}")
        if not socket_client:
            if clients_connected:
                message_manager.send_server_message(protocol_message, clients_connected)
            else:
                self.log_file("Server clients is empty!")
        else:
            socket_client.send(protocol_message)

    def get_local_ip(self):
        """
        Get the local IP address.

        Returns:
            str or None: Local IP address or None if an error occurs.
        """
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except socket.error as e:
            self.log_file(f"Error getting local IP: {e}")
            return None

    def socket_connect_server(self, server_running, port):
        """
        Create a socket and connect it.

        Args:
            server_running: Flag to indicate if the server is running or not.
            port: Port to bind the socket.

        Returns:
            socket or None: Connected socket or None if an error occurs.
        """
        while True:
            socket_connecting = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            host = self.get_local_ip()
            try:
                while not server_running:
                    self.log_file("Connection attempt...")
                    socket_connecting.settimeout(None)
                    socket_connecting.bind((host, port))
                    socket_connecting.listen(10)
                    self.log_file(f"Server is running and listening on ({host}, {port})")
                    return socket_connecting
            except (socket.error, KeyboardInterrupt, Exception) as e:
                self.log_file(f"Error: {e}")
                self.log_file(f"Server connection error on ({host}, {port})")
                return None
