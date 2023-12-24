import queue


class MessageBuffer:
    """
    Class that buffers received messages.
    """

    def __init__(self):
        self.message_queue = queue.Queue()

    def add_message(self, message):
        """
        Adds messages to the buffer.
        :param message: message to be buffered.
        """
        self.message_queue.put(message)

    def get_messages(self):
        """
        Gets all messages from the buffer.
        """
        messages = []
        while not self.message_queue.empty():
            messages.append(self.message_queue.get())
        return messages
