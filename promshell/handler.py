from abc import ABC, abstractmethod

# Interface for command handling
class CommandHandler(ABC):
    
    @abstractmethod
    def handle(self, command_args):
        NotImplemented

    @abstractmethod
    def help(self):
        NotImplemented

    @abstractmethod
    def setup_argparser(self, parent):
        NotImplemented

