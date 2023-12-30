import threading
import time

from server_utils import *
from ui_files import ui_server_glade
from gi.repository import Gtk, GLib

gi.require_version("Gtk", "3.0")


class ServerInterface(Gtk.Window):
    """
    The main interface for the server application.
    """

    def __init__(self):
        """
        Initializes the ServerInterface.
        """
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

        # Define constants
        self.BUFFER_SIZE = 1024
        self.SERVER_PORT = 5500
        self.SERVER_ITSELF = "Server"
        self.SENDS_TO_ALL = "All clients"
        self.FOLDER_PATH = "logs/"
        self.LOG_FILE_NAME = self.FOLDER_PATH + "log_" + get_time() + ".txt"

        # Define variables
        self.socket_server = None
        self.user_sender = None
        self.clients_connected = {}
        self.server_running = False
        self.server_utils = ServerUtils(self.LOG_FILE_NAME, self.text_buffer)

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
        if self.server_running:
            thread_close_server = threading.Thread(target=self.close_server)
            thread_close_server.start()
        else:
            self.socket_server = self.server_utils.socket_connect_server(self.server_running, self.SERVER_PORT)
            if not self.socket_server:
                self.server_utils.log_file("Socket not connected!\n")
            else:
                thread_start_server = threading.Thread(target=self.button_run_stop_starting_server)
                thread_start_server.start()

    # Server Control Functions
    def button_run_stop_starting_server(self):
        self.server_running = True
        self.button_run_stop.set_label("Close server")
        self.button_run_stop.set_sensitive(False)
        run_server = threading.Thread(target=self.control_server)
        run_server.start()
        # Sleep is necessary for a safe server start.
        time.sleep(3)
        self.button_run_stop.set_sensitive(True)

    def button_run_stop_stopping_server(self):
        """Wait for the server to stop safely and update the start button."""
        self.button_run_stop.set_sensitive(False)
        self.button_run_stop.set_label("Start server")
        # Sleep is necessary for a safe server stop.
        time.sleep(3)
        self.button_run_stop.set_sensitive(True)

    def control_server(self):
        """Controls the server's main loop."""
        if self.server_running:
            thread_server_listening = threading.Thread(target=self.server_listen)
            thread_server_listening.start()

        while self.server_running:
            pass

    def server_checks(self, socket_error=""):
        """
        Verify if the server was closed due to a client message or error.
        :param socket_error: states error message. Default is "".
        """
        time.sleep(3)
        if self.server_running:
            self.server_utils.log_file(socket_error)
            self.server_utils.log_file("Restarting the server...\n"
                                       "Server restarted.\n "
                                       "--------------\n")
            self.control_server()

    def close_server(self, close_interface=False):
        """Close the server and/or the program.
        :param close_interface: states if the interface must be closed. Default is False.
        """
        if self.server_running:
            try:
                # Attempt to shut down the socket only if it's still a valid socket
                if self.socket_server.fileno() != -1:
                    self.socket_server.shutdown(socket.SHUT_RDWR)
                    self.socket_server.close()
            except OSError as e:
                # Handle the case where the socket is already closed
                if e.errno != 9:
                    raise

            self.server_running = False
            self.server_utils.log_file("Server stopped.\n")
            button_run_stop_thread = threading.Thread(target=self.button_run_stop_stopping_server)
            button_run_stop_thread.start()

        if close_interface:
            self.server_utils.log_file("Exiting...\n"
                                       "--------------------------------")
            time.sleep(2)
            self.window.destroy()
            Gtk.main_quit()

    def server_listen(self):
        """Listens for incoming client connections and processes messages."""
        try:
            while self.server_running:
                socket_client, address = self.socket_server.accept()
                self.server_utils.server_sends(
                    message_manager.protocol_message_encoding("server", "client", "name"), socket_client,)

                received_message = message_manager.protocol_message_decoding(socket_client.recv(self.BUFFER_SIZE))
                if received_message[0] == "":
                    continue
                self.server_utils.log_file(received_message)

                client_username = received_message[3]
                if self.get_client_socket_by_name(client_username) == "not found":
                    self.server_utils.log_file("Connection established: (%s) -> %s" % (received_message[3], address))
                    add_client(client_username, self.clients_connected, socket_client)

                    message_data = "You are now connected to the server.\n"
                    message_data += "Your address: " + str(address)
                    message_protocol = message_manager.protocol_message_encoding(
                        "server", received_message[3], message_manager.OPCODE_CONNECTION_CONFIRMATION, message_data)

                    self.server_utils.server_sends(message_protocol, self.clients_connected, socket_client)

                    thread_handle_client = threading.Thread(
                        target=self.handle_client, args=(socket_client,), daemon=True)
                    thread_handle_client.start()
                else:
                    message_data = "This username (" + received_message[3] + ") is already taken.\n"
                    message_data += "You need to connect again and use another one"
                    protocol_message = message_manager.protocol_message_encoding(
                        "server", received_message[3], message_manager.OPCODE_CONNECTION_ERROR, message_data)
                    self.server_utils.log_file("Sent: %s" % protocol_message)
                    self.server_utils.server_sends(protocol_message, socket_client)
        except Exception as error:
            self.server_checks(str(error))

    def handle_client(self, socket_client):
        """Processes the messages received from a specific client.
        :param socket_client: client to be process message."""
        message_received = ["", "", "", ""]

        while not self.server_running:
            try:
                message_received = message_manager.protocol_message_decoding(socket_client.recv(self.BUFFER_SIZE))
                if message_received[0] == "":
                    continue

                self.server_utils.log_file("Server receive: %s" % message_received)
                self.user_sender = message_received[0]
                self.server_utils.message_confirmation(self.user_sender, message_received[2], self.SERVER_ITSELF,
                                                       self.clients_connected)

                # UNKNOWN_OPERATION
                if message_received[2] == message_manager.OPCODE_UNKNOWN_OPERATION:
                    message_data = "Operation not supported!"
                    protocol_message = message_manager.protocol_message_encoding(
                        "server", self.user_sender, message_manager.OPCODE_UNKNOWN_OPERATION, message_data)
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    continue
                # OPCODE_ECHO
                if message_received[2] == message_manager.OPCODE_ECHO:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, self.user_sender, message_manager.OPCODE_ECHO, message_received[3])
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    continue
                # PRIVATE_MESSAGE
                if message_received[2] == message_manager.OPCODE_PRIVATE_MESSAGE:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, message_received[1], message_manager.OPCODE_PRIVATE_MESSAGE,
                        message_received[3])
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    continue
                # BROADCAST
                if message_received[2] == message_manager.OPCODE_BROADCAST \
                        or message_received[2] == message_manager.OPCODE_BROADCAST_NOT_ME:
                    protocol_message = message_manager.protocol_message_encoding(
                        self.user_sender, message_manager.OPCODE_BROADCAST, message_received[2], message_received[3])
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    continue
                # LIST_CLIENTS
                if message_received[2] == message_manager.OPCODE_LIST_CLIENTS and message_received[1] == "server":
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, self.user_sender, message_manager.OPCODE_LIST_CLIENTS, self.get_all_list())
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    continue
                # EXIT_CLIENT
                if message_received[2] == message_manager.OPCODE_EXIT_CLIENT:
                    # Message sends to the client before the client left
                    message_data = "You are exiting the server"
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, self.user_sender, message_manager.OPCODE_EXIT_CLIENT, message_data)
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    # Tell everyone that clients left
                    message_data = "client (" + self.user_sender + ") left"
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, message_manager.OPCODE_BROADCAST, message_manager.OPCODE_EXIT_CLIENT,
                        message_data)
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    # Finally removes it from connected clients
                    remove_client(self.user_sender, self.clients_connected)
                    continue
                # VIDEO_CONFERENCE, just forward
                elif message_received[2] in (
                        message_manager.OPCODE_VIDEO_CONFERENCE, message_manager.OPCODE_CLIENT_ADDRESS_REQUEST,
                        message_manager.OPCODE_CLIENT_ADDRESS_SEND, message_manager.OPCODE_CLIENT_AVAILABLE):
                    protocol_message = message_manager.protocol_message_encoding(
                        message_received[0], message_received[1], message_received[2], message_received[3])
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    continue

            except socket.error as socket_error:
                message_data = str(socket_error) + " \n; "
                socket_client = get_client_socket_by_name(message_received[0], self.clients_connected)
                if socket_client:
                    message_data += "client (" + self.user_sender + ") disconnected"
                    protocol_message = message_manager.protocol_message_encoding(
                        self.SERVER_ITSELF, self.SENDS_TO_ALL, message_manager.OPCODE_BROADCAST,
                        message_data)
                    self.server_utils.server_sends(protocol_message, self.clients_connected, socket_client)
                    remove_client(message_received[0], self.clients_connected)
                break
        self.server_checks()


# Main Function
if __name__ == "__main__":
    interface = ServerInterface()
    interface.run()
