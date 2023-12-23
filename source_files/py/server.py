import asyncio
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


def create_folder(folder_path):
    """
    Creates a folder to save all log messages.
    :param folder_path: folder to create.
    """
    try:
        if os.path.exists(folder_path):
            pass
        else:
            # Create a folder at the specified path
            os.makedirs(folder_path)
    except OSError as e:
        print("error log file")


def get_time(spaces=True):
    """
    Gets currently time to log messages
    :param spaces: indicates if it should include spaces or not.
    """
    # Get the current time
    current_time = datetime.now()
    formatted_time = ""

    # Format the time as a string
    if spaces:
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        formatted_time = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    return formatted_time


def on_main_window_destroy(window):
    """
    Closes the server
    """
    Gtk.main_quit()


def close_interface():
    """
    Close interface and the server
    """
    time.sleep(3)  # sleep used to see updates on interface
    Gtk.main_quit()


def get_client_socket_by_name(client_name, client_list):
    """
    Function to search for a client by name.
    :param client_name: client_name
    :param client_list: list of clients
    :return: the client obj or "Not found"
    """
    client_socket = client_list.get(client_name, "not found")
    return client_socket


def dict_empty(dict_clients):
    """Verify is dict is empty
    :param: dict_clients: dict to verify
    :return: True if empty else False
    """
    if not dict_clients:
        return True
    else:
        return False


class ServerInterface(Gtk.Window):
    """
    This class has an interface and controls all connections.
    """

    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_string(ui_server_glade)
        self.textview_logs = self.builder.get_object("user_monitor")
        self.text_buffer = self.builder.get_object("text_view_buffer")
        self.button_run_stop = self.builder.get_object("button_run_stop")
        self.button_run_stop.connect("clicked", self.on_button_run_stop_clicked)
        self.window = self.builder.get_object("main_window")
        self.window.connect("destroy", on_main_window_destroy)

        # Main variables
        self.BUFFER_SIZE = 1024
        self.SERVER_ITSELF = "Server"
        self.SENDS_TO_ALL = "All clients"
        self.FOLDER_PATH = "logs/"
        self.LOG_FILE_NAME = self.FOLDER_PATH + "log_" + get_time(False) + ".txt"
        self.socket_server = None
        self.user_sender = None

        # database
        self.clients_connected = {}
        """dictionary with all clients connected"""

        # Running control
        self.server_running = False
        self.thread_server_listening = None

        # creating folder to logs
        create_folder(self.FOLDER_PATH)

    def save_log_file(self, log_message):
        """
        Save logs messages into file.
        :param log_message: log message to save.
        """
        try:
            # writing log file
            with open(self.LOG_FILE_NAME, 'a') as file:
                file.write(str(log_message) + '\n')
        except OSError as e:
            print(e)

    def update_log_interface(self, log_message):
        """
        Prints on interface log message
        :param log_message: log to print on interface.
        """
        # showing message on ui
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, log_message + "\n")

    def log_file(self, log_message):
        """
        Save log file and prints on interface.
        :param log_message: log message to print and save.
        """
        log_message_with_time = get_time() + " - " + str(log_message)
        GLib.idle_add(self.save_log_file, log_message_with_time)
        GLib.idle_add(self.update_log_interface, log_message_with_time)

    def message_confirmation(self, user_sender, message_code):
        """
        Sends the message confirmation to client indicating that server has received the send message.
        :param user_sender: user that sent the message.
        :param message_code: the code of message.
        """
        if message_code in (message_manager.OPCODE_PRIVATE_MESSAGE, message_manager.OPCODE_BROADCAST_NOT_ME):
            self.server_sends(message_manager.protocol_message_encoding(
                self.SERVER_ITSELF, user_sender, message_manager.OPCODE_MESSAGE_CONFIRMATION, "message sent"))

    def server_sends(self, protocol_message, socket_client=None):
        """
        Prints the server message and sends it
        :param protocol_message: message to forward
        :param socket_client: socket used to send a message to a refused client connection
        """
        self.log_file("Server sends: %s" % protocol_message)
        if not socket_client:
            if self.clients_connected:
                message_manager.send_server_message(protocol_message, self.clients_connected)
            else:
                self.log_file("Server clients is empty!")
        else:
            socket_client.send(protocol_message)

    def server_checks(self, socket_error=""):
        """
        Verify if the server was closed due to a client message or error
        """
        if self.server_running:
            self.log_file(socket_error)
            self.log_file("Restarting the server...\n"
                          "Server restarted.\n "
                          "--------------\n")
            self.control_server()

    def get_all_list(self):
        """
        Function to show the list of connected clients in all pairs (clients, address).
        :return: list of clients
        """
        all_items = ""  # clients_connected.items()
        for key, value in self.clients_connected.items():
            address = str(value).split("raddr=")[1][:-1]
            all_items += key + " -> " + address + "\n"
        return all_items

    def add_client(self, username, client_socket):
        """
        Add client on dictionary
        :param: username: client's username to add
        :param: client_socket: client's socket to add
        """
        self.clients_connected[username] = client_socket

    def remove_client(self, client_username):
        """
        Removes element from dictionary
        :param: client_username: client's username to be removed from dict
        :dict_clients: dictionary to be updated without client
        """
        if client_username in self.clients_connected:
            self.clients_connected.pop(client_username, -1)

    def get_local_ip(self):
        """
        Function to get the local IP address.
        """
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip

        except socket.error as e:
            self.log_file(f"Error: {e}")
            return None

    def socket_connect(self):
        """
        Function to create a socket and connect it.
        """
        socket_connecting = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        host = self.get_local_ip()
        port = 5500
        try:
            if not self.server_running:
                self.log_file("Connection attempt...")
                socket_connecting.bind((host, port))
                socket_connecting.listen(10)
                self.log_file("Server is running and listening on (%s,%s)\n" % (host, port))
                return socket_connecting
            else:
                try:
                    socket_connecting.bind((host, port))
                except socket.error:
                    return None
        except socket.error as e:
            self.log_file(f"Error: {e}")
            self.log_file("Server connection error on (%s,%s)" % (host, port))
            self.server_running = True
            return None

    def server_listen(self):
        """
        The main function. Makes the server await for new messages and send the message to be processed.
        """
        while self.server_running:
            try:
                socket_client, address = self.socket_server.accept()
                protocol_message = message_manager.protocol_message_encoding("server", "client", "name")
                self.server_sends(protocol_message, socket_client)

                received_message = message_manager.protocol_message_decoding(socket_client.recv(self.BUFFER_SIZE))
                if received_message[0] == "":
                    continue
                self.log_file(received_message)

                client_username = received_message[3]
                if get_client_socket_by_name(client_username, self.clients_connected) == "not found":
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

    async def handle_client(self, client):
        """
        Process the messages received.
        :param client: client that sends the messages.
        """
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
                if message_received[2] == message_manager.OPCODE_PRIVATE_MESSAGE:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, message_received[1], message_manager.OPCODE_PRIVATE_MESSAGE,
                        message_received[3])
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_BROADCAST \
                        or message_received[2] == message_manager.OPCODE_BROADCAST_NOT_ME:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, message_manager.OPCODE_BROADCAST, message_received[2], message_received[3])
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_LIST_CLIENTS and message_received[1] == "server":
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, self.user_sender, message_manager.OPCODE_LIST_CLIENTS, self.get_all_list())
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_EXIT_CLIENT:
                    # Message sends to client before the client left
                    message_data = "You are exiting the server"
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, self.user_sender, message_manager.OPCODE_EXIT_CLIENT, message_data)
                    self.server_sends(protocol_message)
                    # Tell everyone that clients left
                    message_data = "client (" + self.user_sender + ") left"
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, message_manager.OPCODE_BROADCAST, message_manager.OPCODE_EXIT_CLIENT,
                        message_data)
                    self.server_sends(protocol_message)
                    # Finally removes it from connected clients
                    self.remove_client(self.user_sender)
                    continue
                elif message_received[2] in (
                        message_manager.OPCODE_VIDEO_CONFERENCE, message_manager.OPCODE_CLIENT_ADDRESS_REQUEST,
                        message_manager.OPCODE_CLIENT_ADDRESS_SEND, message_manager.OPCODE_CLIENT_AVAILABLE):
                    protocol_message = message_manager.protocol_message_encoding(
                        message_received[0], message_received[1], message_received[2], message_received[3])
                    self.server_sends(protocol_message)
                    continue
            except socket.error as socket_error:
                message_data = str(socket_error) + " \n; "
                socket_client = get_client_socket_by_name(message_received[0], self.clients_connected)
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

    def on_button_run_stop_clicked(self, button):
        """
        Receive the signal to start the server.
        :param button: button 'start'.
        """
        if not self.server_running:
            self.socket_server = self.socket_connect()
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

    def control_server(self):
        self.thread_server_listening = threading.Thread(target=self.server_listen, args=(), daemon=True)
        self.thread_server_listening.start()
        while self.server_running:
            pass
        time.sleep(2)
        # Forcing socket to disallow further sends and receives
        self.socket_server.shutdown(socket.SHUT_RDWR)
        # Closing socket
        self.socket_server.close()
        self.log_file("Server stopped.\n")

    def run(self):
        """
        Runs the server.
        """
        self.window.show_all()
        Gtk.main()


# Main function
if __name__ == "__main__":
    interface = ServerInterface()
    interface.run()
