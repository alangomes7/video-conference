import threading
import time

from utils import *
from ui_files import ui_client_glade, ui_test
from message_buffer import MessageBuffer

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class ClientInterface(Gtk.Window):
    def __init__(self):

        # Initialize Gtk Builder and load the UI
        self.builder = Gtk.Builder()
        self.builder.add_from_string(ui_client_glade)

        # Get UI elements
        self.text_buffer = self.builder.get_object("user_log_view_text_buffer")
        self.message_input = self.builder.get_object("user_message_input")
        self.button_send = self.builder.get_object("user_button_send")
        self.window = self.builder.get_object("user_main_window")

        # Connect signals to callback functions
        self.button_send.connect("clicked", self.on_button_send_press)
        self.window.connect("delete-event", self.on_main_window_destroy)

        # Create instances of MessageBuffer
        self.message_buffer_sending = MessageBuffer()
        self.message_buffer_receiving = MessageBuffer()

        # Define constants and variables
        self.stop_client = False
        self.socket_client = None
        self.run_menu = True
        self.button_send_pressed = False

    def run(self):
        """Runs the client."""
        GLib.idle_add(self.window.show_all)
        run_client_thread = threading.Thread(target=self.run_client)
        run_client_thread.start()
        Gtk.main()

    def on_main_window_destroy(self, widget, event):
        """Handles the main window destroy event."""
        return True

    def on_button_send_press(self, button):
        """Wait to the client press the button"""
        self.button_send_pressed = True
        return True

    # Helper functions

    def deactivate_user_input(self):
        self.message_input.set_sensitive(False)
        self.button_send.set_sensitive(False)
        self.button_send_pressed = False

    def activate_user_input(self):
        self.message_input.set_text("")
        self.message_input.set_sensitive(True)
        self.button_send.set_sensitive(True)

    def display_message_client(self, showing_message):
        """Display messages on monitor.
        :param showing_message: message to print to user."""
        showing_message = get_time()[1] + " - " + showing_message
        update_log_interface(showing_message, self.text_buffer)

    def get_message_client(self):
        """Get the input message."""
        self.activate_user_input()
        while not self.button_send_pressed:
            pass
        self.deactivate_user_input()
        user_input = str(self.message_input.get_text())
        self.display_message_client("user: "+user_input)
        return user_input

    def run_client(self):
        time.sleep(2)
        self.socket_client = self.socket_connect()

    def socket_connect(self):
        """
        Creates a connection.
        """
        # new socket, family: Ipv4, type: TCP
        socket_connecting = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        connecting = True
        while connecting:
            self.display_message_client("Please input the server's ip:\n")
            host = self.get_message_client()
            port = 5500
            try:
                # Time out necessary to connect to a specific ip
                socket_connecting.connect((host, port))
                # Removes time out. It needs to wait the user's input
                socket_connecting.settimeout(None)
                connecting = False
            except socket.error as e:
                self.display_message_client(f"Error: {e}")
                self.display_message_client("Client connection error on (%s,%s)" % (host, port))
                self.display_message_client("n = to finish or any key to try again...\n")
                user_client = self.get_message_client()
                if user_client == "n":
                    stop_client = True
                    connecting = False
        return socket_connecting


# Main Function
if __name__ == "__main__":
    interface = ClientInterface()
    interface.run()
