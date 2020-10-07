from abc import ABC, abstractmethod
from typing import Iterable
from prompt_toolkit.completion import Completion
from promshell.arguments import ArgDescriptor
from promshell.completion import CompletionContext

# Interface for command handling
class CommandHandler(ABC):
    
    @abstractmethod
    def handle(self, command_args) -> dict:
        NotImplemented

    def help(self):
        NotImplemented


    def setup_argparser(self, parent):
        NotImplemented

    def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
        # return state.completions_for_option(word)
        pass

