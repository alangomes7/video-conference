import threading
import socket
import time

import message as message_manager

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class ServerInterface:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("ui/server_gui.glade")
        self.textview_logs = self.builder.get_object("text_view_logs")
        self.textbuffer = self.textview_logs.get_buffer()
        self.button_run_stop = self.builder.get_object("button_run_stop")
        self.button_run_stop.connect("clicked", self.on_button_run_stop_clicked)
        self.window = self.builder.get_object("window_main")
        self.window.connect("destroy", self.on_main_window_destroy)

        # Main variables
        self.BUFFER_SIZE = 1024
        self.SERVER_ITSELF = "Server"
        self.SENDS_TO_ALL = "All clients"
        self.socket_server = None

        # database
        self.clients_connected = {}
        """dictionary with all clients connected"""
        self.clients_moderators = {}
        """dictionary with all moderators clients"""

        # Running control
        self.close_server = threading.Event()
        self.running = False

    def on_main_window_destroy(self, window):
        Gtk.main_quit()

    def save_log_file(self, log_message):
        # writing log file
        log_file_path = 'log.txt'
        with open(log_file_path, 'a') as file:
            file.write(str(log_message) + '\n')

    def update_log_interface(self, log_message):
        # showing message on ui
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.insert(end_iter, log_message + "\n")

    def log_file(self, log_message):
        GLib.idle_add(self.save_log_file, log_message)
        GLib.idle_add(self.update_log_interface, log_message)

    def message_confirmation(self, user_sender, message_code):
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
        time.sleep(2)

    def server_checks(self, socket_error=""):
        """
        Verify if the server was closed due to a client message or error
        """
        if self.close_server:
            self.log_file("Server closed")
            self.close_server.set()
        else:
            self.log_file(socket_error)
            self.log_file("Restarting the server...\n")
            self.on_button_run_stop_clicked()

    def get_client_socket_by_name(self, client_name, client_list):
        """
        Function to search for a client by name.
        :param client_name: client_name
        :param client_list: list of clients
        :return: the client obj or "Not found"
        """
        client_socket = client_list.get(client_name, "not found")
        return client_socket

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
        self.add_moderator(username, client_socket)

    def add_moderator(self, client_username, client_socket):
        """
        Verify is the server has moderators. If it has not then adds else do not add it.
        :param: client_username: client's username to add.
        :param: client_socket: client's socket to add.
        """
        if self.dict_empty(self.clients_moderators):
            self.clients_moderators[client_username] = client_socket

    def remove_client(self, client_username):
        """
        Removes element from dictionary
        :param: client_username: client's username to be removed from dict
        :dict_clients: dictionary to be updated without client
        """
        self.clients_moderators.pop(client_username, -1)
        self.clients_connected.pop(client_username, -1)
        self.server_has_at_least_one_moderator()

    def server_has_at_least_one_moderator(self):
        """
        Verify if the server can continue open.
        The server can only continue open if exists at least one moderator.
        """
        if not self.clients_moderators:
            self.close_server.set()
            time.sleep(3)

    def dict_empty(self, dict_clients):
        """Verify is dict is empty
        :param: dict_clients: dict to verify
        :return: True if empty else False
        """
        if not dict_clients:
            return True
        else:
            return False

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
        port = 1234
        try:
            self.log_file("Connection attempt...")
            socket_connecting.bind((host, port))
            socket_connecting.listen(10)
            self.log_file("Server is running and listening on (%s,%s)\n" % (host, port))
            return socket_connecting
        except socket.error as e:
            self.log_file(f"Error: {e}")
            self.log_file("Server connection error on (%s,%s)" % (host, port))
            self.close_server.set()
            return None

    def up_server(self):
        while not self.close_server.is_set():
            try:
                self.log_file("Waiting for connection...")

                socket_client, address = self.socket_server.accept()
                self.log_file("Connection established")

                protocol_message = message_manager.protocol_message_encoding("server", "client", "name")
                self.server_sends(protocol_message, socket_client)

                received_message = message_manager.protocol_message_decoding(socket_client.recv(self.BUFFER_SIZE))
                self.log_file(received_message)

                client_username = received_message[3]
                if self.get_client_socket_by_name(client_username, self.clients_connected) == "not found":
                    self.log_file("Connection established: (%s) -> %s" % (received_message[3], address))
                    self.add_client(client_username, socket_client)

                    message_data = "You are now connected to the server.\n"
                    message_data += "Your address: " + str(address)
                    message_protocol = message_manager.protocol_message_encoding(
                        "server", received_message[3], message_manager.OPCODE_CONNECTION_CONFIRMATION, message_data)

                    self.server_sends(message_protocol)

                    thread_handle_client = threading.Thread(
                        target=self.handle_client, args=(socket_client,))
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
        message_received = ["", "", "", ""]
        message_data = ""
        while not self.close_server.is_set():
            try:
                message_received = message_manager.protocol_message_decoding(client.recv(self.BUFFER_SIZE))
                self.log_file("Server receive: %s" % message_received)
                user_sender = message_received[0]
                self.message_confirmation(user_sender, message_received[2])

                if message_received[2] == message_manager.OPCODE_UNKNOWN_OPERATION:
                    message_data = "Operation not supported!"
                    protocol_message = message_manager.protocol_message_encoding(
                        "server", user_sender, message_manager.OPCODE_UNKNOWN_OPERATION, message_data)
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_ECHO:
                    protocol_message = message_manager.protocol_message_encoding(
                        user_sender, user_sender, message_manager.OPCODE_ECHO, message_received[3])
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_PRIVATE_MESSAGE:
                    protocol_message = message_manager.protocol_message_encoding(
                        user_sender, message_received[1], message_manager.OPCODE_PRIVATE_MESSAGE,
                        message_received[3])
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_BROADCAST \
                        or message_received[2] == message_manager.OPCODE_BROADCAST_NOT_ME:
                    protocol_message = message_manager.protocol_message_encoding(
                        user_sender, message_manager.OPCODE_BROADCAST, message_received[2], message_received[3])
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_LIST_CLIENTS and message_received[1] == "server":
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, user_sender, message_manager.OPCODE_LIST_CLIENTS, self.get_all_list())
                    self.server_sends(protocol_message)
                    continue
                if message_received[2] == message_manager.OPCODE_EXIT_CLIENT:
                    message_data = "client (" + user_sender + ") left"
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, message_manager.OPCODE_BROADCAST, message_manager.OPCODE_EXIT_CLIENT,
                        message_data)
                    self.server_sends(protocol_message)
                    message_data = "You are exiting the server"
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, user_sender, message_manager.OPCODE_EXIT_CLIENT, message_data)
                    self.server_sends(protocol_message)
                    self.remove_client(user_sender)
                    continue
                if message_received[2] == message_manager.OPCODE_CLOSE_SERVER:
                    if self.get_client_socket_by_name(user_sender, self.clients_moderators) != "not found":
                        message_data = "server closed"
                        self.close_server.set()
                    else:
                        message_data = "You do not have enough permissions to execute that action!"
                        protocol_message = message_manager.protocol_message_encoding(
                            self.SERVER_ITSELF, user_sender, message_manager.OPCODE_PRIVATE_MESSAGE, message_data)
                        self.server_sends(protocol_message)
                        continue
                if message_received[2] == message_manager.OPCODE_VIDEO_CONFERENCE \
                        and message_received[3] == message_manager.MESSAGE_REQUESTING:
                    message_data = "Client " + message_received[0] + " is requesting a video conference"
                    protocol_message = message_manager.protocol_message_encoding(
                        message_received[0], message_received[1], message_received[2], message_data)
                    self.server_sends(protocol_message)
                    continue
            except socket.error as socket_error:
                message_data = str(socket_error) + " | "
                message_data += "client (" + user_sender + ") disconnected"
                protocol_message = message_manager.protocol_message_encoding(
                    self.SERVER_ITSELF, message_manager.OPCODE_BROADCAST, message_manager.OPCODE_BROADCAST,
                    message_data)
                socket_client = self.get_client_socket_by_name(message_received[0], self.clients_connected)
                self.remove_client(socket_client)
                self.server_sends(protocol_message)
                self.receive()
                break
        if self.close_server.is_set():
            self.log_file("Closing server...")
            message_data += "\nUser (" + message_received[0] + ") closes the server."
            protocol_message = message_manager.protocol_message_encoding(
                self.SERVER_ITSELF, message_manager.OPCODE_BROADCAST, message_manager.OPCODE_BROADCAST, message_data)
            self.server_sends(protocol_message)
            time.sleep(2)
            self.socket_server.close()
        else:
            self.up_server()

    def on_button_run_stop_clicked(self, button):
        if not self.running:
            self.socket_server = self.socket_connect()
            if not self.socket_server:
                self.log_file("Socket not connected!")
                self.close_server.set()
            else:
                self.button_run_stop.set_label("Stop")
                thread_server_listening = threading.Thread(target=self.up_server, args=(), daemon=True)
                thread_server_listening.start()

                # Update the button
                self.running = not self.running
        else:
            self.log_file("Stopping...")
            self.close_server.set()
            self.button_run_stop.set_label("Run")

            # Update the button
            self.running = not self.running

    def run(self):
        self.window.show_all()
        Gtk.main()


# Main function
if __name__ == "__main__":
    interface = ServerInterface()
    interface.run()
