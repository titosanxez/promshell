from abc import ABC, abstractmethod
from typing import List, Iterable, Mapping

from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.completion.word_completer import WordCompleter
from promshell.arguments import ArgDescriptor

class CompletionContext:
    def __init__(
            self,
            document: Document,
            event: CompleteEvent,
            arg_descriptor: ArgDescriptor,
            word: str = ''):
        self.document = document
        self.event = event
        self.arg_descriptor = arg_descriptor
        self.word = word


class ValueCompleter(ABC):
    @abstractmethod
    def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
        NotImplemented


class KeyValueCompleter(ValueCompleter):
    def __init__(self, key_names: List[str], operators: List[str]):
        self.key_names = key_names
        self.operators = operators

    def get_completions(
            self,
            context: CompletionContext) -> Iterable[Completion]:
        """Returns a list of completions based on the state of the key-value
        expression in the word.
        Possible outcomes are:

            - List of all keys
            - List of non-specified keys
            - Operator
            - Any value for the key (empty completion)

        Whichever the outcome list, it will include a 'comma' as key-value separator
        """

        if not self.key_names:
            yield Completion('', start_position=0)

        # Copy the list of values, from which we remove elements as they are found
        # in the word
        provide_keys = True
        used_keys = self.key_names.copy()
        key_value_items = context.word.split(',')
        while key_value_items:
            key_value = key_value_items.pop(0)
            key = key_value
            value = ''
            # separate key from value
            expression = []
            for op in ['=', '=~', '!=', '!~']:
                expression = key_value.partition(op)
                if expression[1] != '':
                    key = expression[0]
                    value = expression[2]
                    break

            if key_value_items:
                # If this is not the last key-value, remove it from the available key
                if key in used_keys:
                    used_keys.remove(key)
            else:
                # last key-value determines what to actually complete
                if expression[0] != '' and expression[1] == '':
                    provide_keys = False
                    for op in ['=', '=~', '!=', '!~']:
                        yield Completion(op, start_position=0)
                elif expression[1] != '':
                    provide_keys = False
                    if value != '':
                        yield Completion(',', start_position=0)
                    else:
                        yield Completion('<value>[,]', start_position=0)
                elif value != '':
                    yield Completion(',', start_position=0)

        if provide_keys:
            for key in used_keys:
                # provide a list of extended items
                yield Completion(key, start_position=0)


class ArgumentCompleter(Completer):
    """
        Completer implementation for a given command-line option sequence.

        The option model for the completer is based ona  list of ArgDescription
        objects, where each item represents a possible options. The completer
        semantics are based on:
        - Use ArgDescription to determine the possibilty of appearence for an option
        - A single option can be set only one
        - After an option is set specified, and it expects a value (or set of)
          it will autocomplete only the possible values and not the other options.
    """

    def __init__(self, arg_desc_set: Mapping[str, dict], completer: ValueCompleter = None):
        if isinstance(arg_desc_set, dict):
            self.arg_desc_list = []
            for key in arg_desc_set:
                self.arg_desc_list.append(ArgDescriptor(key, **arg_desc_set[key]))
        elif isinstance(arg_desc_set, list):
            self.arg_desc_list = arg_desc_set
        else:
            raise ValueError("argument description is not a dictionary or list ")

        self.value_completer = completer

    class State:
        def __init__(
                self,
                document: Document,
                event: CompleteEvent,
                word_list: List[str],
                arg_desc_list: List[ArgDescriptor],
                completer: ValueCompleter):
            self.document = document
            self.event = event
            self.trailing_space = document.text.endswith(' ')
            self.word_list = word_list
            self.arg_desc_list = arg_desc_list.copy()
            self.arg_descriptor = None
            self.completer = completer

        def remove_positional(self):
            # positional arg: remove first POSITIONAL arg from description list
            for desc in self.arg_desc_list:
                if desc.is_positional():
                    self.arg_desc_list.remove(desc)
                    break

        def completion_for_argument_set(self) -> Iterable[Completion]:
            completion_items = []
            for arg_descriptor in self.arg_desc_list:
                if arg_descriptor.is_positional():
                    # add remaining positionals
                    if self.completer:
                        context = CompletionContext(
                            self.document,
                            self.event,
                            arg_descriptor
                        )
                        for c in self.completer.get_completions(context):
                            yield c
                    else:
                        for value in arg_descriptor.choices:
                            completion_items.append(value)
                else:
                    completion_items.append(arg_descriptor.flags[0])

            completer = WordCompleter(completion_items)
            for c in completer.get_completions(self.document, self.event):
                yield c

        def completion_for_option(self, word: str) -> Iterable[Completion]:
            if self.arg_descriptor.is_flag():
                return self.completion_for_argument_set()

            if self.completer:
                context = CompletionContext(
                    self.document,
                    self.event,
                    self.arg_descriptor,
                    word
                )
                return self.completer.get_completions(context)

            completer = WordCompleter(self.arg_descriptor.choices)
            return completer.get_completions(self.document, self.event)

        def find_option(self, name) -> ArgDescriptor:
            for desc in self.arg_desc_list:
                if (not desc.is_positional()) and name in desc.flags:
                    return desc

            return None

    #
    # ArgumentCompleter implementation
    #

    def resolve_completion(self, state: State) -> Iterable[Completion]:
        """Recursive operation that traverses the list of words, processing one
        """

        if not state.word_list:
            # In the absence of words or last word, we display the available options
            return state.completion_for_argument_set()

        # iterate over all the words except the last one, which will determine
        # which completion to show.
        word = state.word_list.pop(0)
        last_word = not state.word_list
        matching_arg = state.find_option(word)

        if last_word:
            # base case is the last word, which determines what the completion list
            # should be
            if state.trailing_space:
                if matching_arg:
                    state.arg_descriptor = matching_arg
                    return state.completion_for_option('')
                elif not state.arg_descriptor:
                    state.remove_positional()
            else:
                if state.arg_descriptor:
                    return state.completion_for_option(word)

            return state.completion_for_argument_set()

        # else: For all previous word, skip one-time options and values that have been
        # already specified
        if matching_arg:
            state.arg_desc_list.remove(matching_arg)
            state.arg_descriptor = matching_arg
        else:
            if state.arg_descriptor is None:
                # positional
                state.remove_positional()
                # either positional or option value, we set the last option desc to None
            state.arg_descriptor = None

        return self.resolve_completion(state)

    def get_completions(self, document, complete_event):
        """
            This operation iterates over the option line and check for each:
            - If the word is a valid option, provide completion of the expected
              values (if any and if available)
            - If the word is not a valid option and doesn't folow a valid option
              autocomplete the with the available option names
            - Remove the specified option if it can appear only once
            - Autcomplete only the remaining set of options
        """

        # Get option line decomposed in words separated by spaces
        text = document.text.lstrip()
        word_list = text.split()
        state = self.State(
                document,
                complete_event,
                word_list,
                self.arg_desc_list,
                self.value_completer)

        for item in self.resolve_completion(state):
            yield item
        # Always add an 'empty' item as a way to prevent the prompt from automatically
        # adding the last remaining choice
        yield Completion('')
