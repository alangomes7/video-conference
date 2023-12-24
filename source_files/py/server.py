import threading
import time

from utils import *
from ui_files import ui_server_glade

import gi

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
        self.window.connect("delete-event", self.on_main_window_destroy)

        # Define constants and variables
        self.BUFFER_SIZE = 1024
        self.SERVER_ITSELF = "Server"
        self.SENDS_TO_ALL = "All clients"
        self.FOLDER_PATH = "logs/"
        self.LOG_FILE_NAME = self.FOLDER_PATH + "log_" + get_time()[0] + ".txt"
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
        GLib.idle_add(self.window.show_all)
        Gtk.main()

    def on_main_window_destroy(self, window, event=None):
        """Closes the interface and the server."""
        thread_close_server = threading.Thread(target=self.close_server, args=(True,))
        thread_close_server.start()
        return True

    def on_button_run_stop_clicked(self, button):
        """Handles the click event of the 'Run/Stop' button."""
        if not self.server_running:
            self.socket_server = socket_connect_server(self.server_running, self.LOG_FILE_NAME, self.text_buffer)
            if not self.socket_server:
                log_file("Socket not connected!\n", self.LOG_FILE_NAME, self.text_buffer)
            else:
                self.server_running = True
                run_server = threading.Thread(target=self.control_server)
                run_server.start()
                self.button_run_stop.set_label("Close server")
        else:
            thread_close_server = threading.Thread(target=self.close_server())
            thread_close_server.start()

    # Server Control Functions

    def button_run_stop_stopping_server(self):
        """Wait the server safely stop to update the start button."""
        self.button_run_stop.set_label("Start server")
        self.button_run_stop.set_sensitive(False)
        # Sleep is necessary to server safe stop.
        time.sleep(3)
        self.button_run_stop.set_sensitive(True)

    def control_server(self):
        """Controls the server's main loop."""
        if self.server_running:
            self.thread_server_listening = threading.Thread(target=self.server_listen, daemon=True)
            self.thread_server_listening.start()
        i = 0
        while self.server_running:
            pass

    def server_checks(self, socket_error=""):
        """
        Verify if the server was closed due to a client message or error.
        :param socket_error: states error message. Default is "".
        """
        time.sleep(3)
        if self.server_running:
            log_file(socket_error, self.LOG_FILE_NAME, self.text_buffer)
            log_file("Restarting the server...\n"
                     "Server restarted.\n "
                     "--------------\n",
                     self.LOG_FILE_NAME, self.text_buffer)
            self.control_server()

    def close_server(self, close_interface=False):
        """Close the server and/or the program.
        :param close_interface: states if the interface must be closed. Default is False.
        """
        if self.server_running:
            self.server_running = False
            self.socket_server.shutdown(socket.SHUT_RDWR)
            self.socket_server.close()
            log_file("Server stopped.\n", self.LOG_FILE_NAME, self.text_buffer)
            button_run_stop_thread = threading.Thread(target=self.button_run_stop_stopping_server)
            button_run_stop_thread.start()
        if close_interface:
            log_file("Exiting...\n"
                     "--------------------------------"
                     , self.LOG_FILE_NAME, self.text_buffer)
            time.sleep(2)
            self.window.destroy()
            Gtk.main_quit()

    def server_listen(self):
        """Listens for incoming client connections and processes messages."""
        try:
            while self.server_running:
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
        except Exception as error:
            self.server_checks(str(error))

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

                # UNKNOWN_OPERATION
                if message_received[2] == message_manager.OPCODE_UNKNOWN_OPERATION:
                    message_data = "Operation not supported!"
                    protocol_message = message_manager.protocol_message_encoding(
                        "server", self.user_sender, message_manager.OPCODE_UNKNOWN_OPERATION, message_data)
                    self.server_sends(protocol_message)
                    continue
                # OPCODE_ECHO
                if message_received[2] == message_manager.OPCODE_ECHO:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, self.user_sender, message_manager.OPCODE_ECHO, message_received[3])
                    self.server_sends(protocol_message)
                    continue
                # PRIVATE_MESSAGE
                if message_received[2] == message_manager.OPCODE_PRIVATE_MESSAGE:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, message_received[1], message_manager.OPCODE_PRIVATE_MESSAGE,
                        message_received[3])
                    self.server_sends(protocol_message)
                    continue
                # BROADCAST
                if message_received[2] == message_manager.OPCODE_BROADCAST \
                        or message_received[2] == message_manager.OPCODE_BROADCAST_NOT_ME:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, message_manager.OPCODE_BROADCAST, message_received[2], message_received[3])
                    self.server_sends(protocol_message)
                    continue
                # LIST_CLIENTS
                if message_received[2] == message_manager.OPCODE_LIST_CLIENTS and message_received[1] == "server":
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, self.user_sender, message_manager.OPCODE_LIST_CLIENTS, self.get_all_list())
                    self.server_sends(protocol_message)
                    continue
                # EXIT_CLIENT
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
                # VIDEO_CONFERENCE, just forward
                elif message_received[2] in (
                        message_manager.OPCODE_VIDEO_CONFERENCE, message_manager.OPCODE_CLIENT_ADDRESS_REQUEST,
                        message_manager.OPCODE_CLIENT_ADDRESS_SEND, message_manager.OPCODE_CLIENT_AVAILABLE):
                    protocol_message = message_manager.protocol_message_encoding(
                        message_received[0], message_received[1], message_received[2], message_received[3])
                    self.server_sends(protocol_message)
                    continue

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
        self.server_checks()


# Main Function
if __name__ == "__main__":
    interface = ServerInterface()
    interface.run()
