import gi

from client_utils import *
from ui_files import ui_client_glade

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

        # Client Utils
        self.client_utils = ClientUtils(self.button_send,self.message_input, self.text_buffer)

        # Connect signals to callback functions
        self.button_send.connect("clicked", self.client_utils.on_button_send_press)
        self.window.connect("delete-event", self.on_main_window_destroy)

    def run(self):
        """Runs the client."""
        GLib.idle_add(self.window.show_all)
        run_client_thread = threading.Thread(target=self.run_client)
        run_client_thread.start()
        Gtk.main()

    def on_main_window_destroy(self, widget, event):
        """Handles the main window destroy event."""
        self.client_utils.close_client_socket()
        return False

    def run_client(self):
        time.sleep(2)
        self.client_utils.display_message_client("Your username:")
        self.client_utils.set_client_name( self.client_utils.get_message_client())
        self.client_utils.set_client_socket(self.client_utils.socket_connect())
        receive_messages_thread = threading.Thread(target=self.client_utils.client_receive, daemon=True)
        receive_messages_thread.start()
        while True:
            pass



# Main Function
if __name__ == "__main__":
    interface = ClientInterface()
    interface.run()
