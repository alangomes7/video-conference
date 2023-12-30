import threading
import socket
import time
from datetime import datetime
from message_buffer import MessageBuffer
import message_handle as message_manager

BUFFER_SIZE = 1024


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


class ClientUtils:
    def __init__(self, button_send, message_input, text_buffer):
        """
        Initialize ServerUtils.

        Args:
            button_send: button to send message
            message_input: input to get user messages from interface
            text_buffer: Buffer to display log messages.
        """
        self.text_buffer = text_buffer
        self.message_input = message_input
        self.button_send = button_send
        self.socket_client = None
        self.name = None
        self.button_send_pressed = False
        self.stop = False

    def set_client_name(self, name):
        self.name = name

    def set_client_socket(self, socket_client):
        self.socket_client = socket_client

    def deactivate_user_input(self):
        self.message_input.set_sensitive(False)
        self.button_send.set_sensitive(False)
        self.button_send_pressed = False

    def activate_user_input(self):
        self.message_input.set_text("")
        self.message_input.set_sensitive(True)
        self.button_send.set_sensitive(True)

    def on_button_send_press(self, button):
        """Wait to the client press the button"""
        self.button_send_pressed = True
        return True

    def display_message_client(self, showing_message):
        """Display messages on monitor.
        :param showing_message: message to print to user."""
        print_message = get_time() + " - " + showing_message
        self.update_log_interface(print_message)

    def get_message_client(self):
        """Get the input message."""
        self.activate_user_input()
        while not self.button_send_pressed:
            pass
        self.deactivate_user_input()
        user_input = str(self.message_input.get_text())
        self.display_message_client("user: " + user_input)
        return user_input

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
                if "." not in host:
                    raise socket.error("Invalid address!")
                # Time out necessary to connect to a specific ip
                socket_connecting.connect((host, port))
                # Removes time out. It needs to wait the user's input
                socket_connecting.settimeout(None)
                connecting = False
            except socket.error as e:
                self.display_message_client(f"Error: {e}")
                self.display_message_client("Client connection error on (%s,%s)" % (host, port))
        return socket_connecting

    def update_log_interface(self, log_message):
        """
        Update the log interface with a log message.

        Args:
            log_message (str): Log message to be printed on the screen.
        """
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, f"{log_message}\n")

    def client_receive(self):
        """
        Await to messages from server or from another client.
        """
        message_buffer = MessageBuffer()
        try:
            while not self.stop:
                message_received = message_manager.protocol_message_decoding(self.socket_client.recv(BUFFER_SIZE))
                print(message_received)
                message_buffer.add_message(message_received)
                messages_buffered = message_buffer.get_messages()
                thread = threading.Thread(target=self.process_messages, args=(messages_buffered,), daemon=True)
                thread.start()
        except socket.error as socket_error:
            self.handle_client_receive_messages_error(socket_error)

    def handle_client_receive_messages_error(self, socket_error=None):
        """
        Checks what happened with client connection and prints the message error.
        :param socket_error: error socket.
        """
        if not self.stop:
            if not socket_error:
                message_data = "Message empty!"
            else:
                message_data = "Error with client connection (" + str(socket_error.args[0]) + ")"
            message_protocol = message_manager.protocol_message_encoding(
                self.name, self.name, message_manager.OPCODE_ERROR_MESSAGE, message_data)
            self.print_reply(message_manager.protocol_message_decoding(message_protocol))
        self.stop = True
        time.sleep(2)  # it needs waiting a little bit more
        self.close_client_socket()
        return True

    def process_messages(self, message_buffer_messages):
        """Process buffered messages."""
        for message in message_buffer_messages:
            if len(message) == 4:
                if message[0] == '':
                    self.handle_client_receive_messages_error()
                else:
                    self.handle_client_receive_messages(message)
            else:
                self.handle_client_receive_messages_error()
                self.stop = True
                time.sleep(2)

    def print_reply(self, protocol_message_decoded):
        """
        Prints to client the message from server.
        """
        messages = protocol_message_decoded[3].split("\n")
        for message in messages:
            self.display_message_client(message)

    def close_client_socket(self):
        """Close the server and/or the program."""
        try:
            # Attempt to shut down the socket only if it's still a valid socket
            if self.socket_client.fileno() != -1:
                self.socket_client.shutdown(socket.SHUT_RDWR)
                self.socket_client.close()
        except OSError as e:
            # Handle the case where the socket is already closed
            if e.errno != 9:
                raise "Socket already closed!"

    def handle_client_receive_messages(self, message):
        """
            Process the incoming message.
            :param message: incoming message to process.
            """
        if message[2] == message_manager.OPCODE_NAME:
            protocol_message = message_manager.protocol_message_encoding(
                self.name, "server", message_manager.OPCODE_NAME, self.name)
            message_manager.send_client_message(protocol_message, self.socket_client)
        if message[2] in (
                message_manager.OPCODE_UNKNOWN_OPERATION, message_manager.OPCODE_ECHO,
                message_manager.OPCODE_PRIVATE_MESSAGE, message_manager.OPCODE_LIST_CLIENTS,
                message_manager.OPCODE_BROADCAST_NOT_ME, message_manager.OPCODE_MESSAGE_CONFIRMATION,
                message_manager.OPCODE_CONNECTION_CONFIRMATION):
            self.print_reply(message)
