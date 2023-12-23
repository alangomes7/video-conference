import threading
import socket
import time
from datetime import datetime
import os

import message as message_manager

import gi
from ui_files import ui_server_glade

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class ServerInterface(Gtk.Window):
    def __init__(self):
        # Initialize Gtk Builder and load the UI
        self.builder = Gtk.Builder()
        self.builder.add_from_string(ui_server_glade)

        # Get UI elements
        self.textview_logs = self.builder.get_object("user_monitor")
        self.text_buffer = self.builder.get_object("text_view_buffer")
        self.button_run_stop = self.builder.get_object("button_run_stop")
        self.window = self.builder.get_object("main_window")

        # Connect signals to callback functions
        self.button_run_stop.connect("clicked", self.on_button_run_stop_clicked)
        self.window.connect("destroy", self.on_main_window_destroy)

        # Define constants and variables
        self.BUFFER_SIZE = 1024
        self.SERVER_ITSELF = "Server"
        self.SENDS_TO_ALL = "All clients"
        self.FOLDER_PATH = "logs/"
        self.LOG_FILE_NAME = self.FOLDER_PATH + "log_" + get_time(False) + ".txt"
        self.socket_server = None
        self.user_sender = None
        self.clients_connected = {}
        self.server_running = False
        self.thread_server_listening = None

        # Create a folder to store log messages
        create_folder(self.FOLDER_PATH)

    # Callback Functions

    def run(self):
        """Runs the server."""
        self.window.show_all()
        Gtk.main()

    def on_main_window_destroy(self, window):
        """Closes the interface and the server."""
        self.close_server()
        Gtk.main_quit()

    def on_button_run_stop_clicked(self, button):
        """Handles the click event of the 'Run/Stop' button."""
        if not self.server_running:
            self.socket_server = socket_connect(self.server_running, self.LOG_FILE_NAME, self.text_buffer)
            if not self.socket_server:
                self.log_file("Socket not connected!\n")
            else:
                self.server_running = True
                run_server = threading.Thread(target=self.control_server, args=())
                run_server.start()
                self.button_run_stop.set_label("Close server")
        else:
            time.sleep(4)
            self.button_run_stop.set_label("Start server")
            self.server_running = False

    # Server Control Functions

    def control_server(self):
        """Controls the server's main loop."""
        self.thread_server_listening = threading.Thread(target=self.server_listen, args=(), daemon=True)
        self.thread_server_listening.start()
        while self.server_running:
            pass
        self.close_server()

    def server_checks(self, socket_error=""):
        """
        Verify if the server was closed due to a client message or error.
        :param socket_error: states error message. Default is "".
        """
        if self.server_running:
            log_file(socket_error)
            log_file("Restarting the server...\n"
                     "Server restarted.\n "
                     "--------------\n")
            self.control_server()

    def close_server(self):
        time.sleep(2)
        self.socket_server.shutdown(socket.SHUT_RDWR)
        self.socket_server.close()
        log_file("Server stopped.\n", self.LOG_FILE_NAME, self.text_buffer)

    def server_listen(self):
        """Listens for incoming client connections and processes messages."""
        while self.server_running:
            try:
                socket_client, address = self.socket_server.accept()
                self.server_sends(message_manager.protocol_message_encoding("server", "client", "name"), socket_client)

                received_message = message_manager.protocol_message_decoding(socket_client.recv(self.BUFFER_SIZE))
                if received_message[0] == "":
                    continue
                self.log_file(received_message)

                client_username = received_message[3]
                if self.get_client_socket_by_name(client_username) == "not found":
                    self.log_file("Connection established: (%s) -> %s" % (received_message[3], address))
                    self.add_client(client_username, socket_client)

                    message_data = "You are now connected to the server.\n"
                    message_data += "Your address: " + str(address)
                    message_protocol = message_manager.protocol_message_encoding(
                        "server", received_message[3], message_manager.OPCODE_CONNECTION_CONFIRMATION, message_data)

                    self.server_sends(message_protocol)

                    thread_handle_client = threading.Thread(
                        target=self.handle_client, args=(socket_client,), daemon=True)
                    thread_handle_client.start()
                else:
                    message_data = "This username (" + received_message[3] + ") is already taken.\n"
                    message_data += "You need to connect again and use another one"
                    protocol_message = message_manager.protocol_message_encoding(
                        "server", received_message[3], message_manager.OPCODE_CONNECTION_ERROR, message_data)
                    self.log_file("Sent: %s" % protocol_message)
                    self.server_sends(protocol_message, socket_client)
            except socket.error as socket_error:
                self.server_checks(str(socket_error))
                break
        self.server_checks()

    def handle_client(self, client):
        """Processes the messages received from a specific client.
        :param client: client to be process message."""
        message_received = ["", "", "", ""]
        message_data = ""
        while not self.server_running:
            try:
                message_received = message_manager.protocol_message_decoding(client.recv(self.BUFFER_SIZE))
                if message_received[0] == "":
                    continue

                self.log_file("Server receive: %s" % message_received)
                self.user_sender = message_received[0]
                self.message_confirmation(self.user_sender, message_received[2])

                if message_received[2] == message_manager.OPCODE_UNKNOWN_OPERATION:
                    message_data = "Operation not supported!"
                    protocol_message = message_manager.protocol_message_encoding(
                        "server", self.user_sender, message_manager.OPCODE_UNKNOWN_OPERATION, message_data)
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_ECHO:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, self.user_sender, message_manager.OPCODE_ECHO, message_received[3])
                    self.server_sends(protocol_message)
                    continue
                # Add more conditions for handling different message types

            except socket.error as socket_error:
                message_data = str(socket_error) + " \n; "
                socket_client = self.get_client_socket_by_name(message_received[0])
                if socket_client:
                    message_data += "client (" + self.user_sender + ") disconnected"
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, self.SENDS_TO_ALL, message_manager.OPCODE_BROADCAST,
                        message_data)
                    self.server_sends(protocol_message)
                    self.remove_client(message_received[0])
                break
        if self.server_running:
            self.log_file("Closing server...")
            message_data += "\n User (" + message_received[0] + ") closes the server."
            protocol_message = message_manager.protocol_message_encoding(
                self.SERVER_ITSELF, self.SENDS_TO_ALL, message_manager.OPCODE_BROADCAST, message_data)
            self.server_sends(protocol_message)
        self.server_checks()


# Helper Functions

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


def get_time(spaces=True):
    """Gets the current time to log messages. :param spaces: default is True. That means the log will include spaces
    to separate date and time. Otherwise, is used (_) underscore."""
    current_time = datetime.now()
    formatted_time = ""
    if spaces:
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        formatted_time = current_time.strftime("%Y-%m-%d_%H-%M-%S")
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
    GLib.idle_add(save_log_file, log_message, log_file_name)
    GLib.idle_add(update_log_interface, log_message, text_buffer)


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


def socket_connect(server_running, log_file_name, text_buffer):
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


# Main Function
if __name__ == "__main__":
    interface = ServerInterface()
    interface.run()
