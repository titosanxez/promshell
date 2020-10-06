from abc import ABC, abstractmethod
from typing import List, Iterable

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.completion.word_completer import WordCompleter
from promshell.prometheus.rest_builder import Series

class UpdatableCompleter(Completer, ABC):
    def __init__(self, params):
        self.completer = self.from_params(params)

    def get_completions(self, document, complete_event):
        return self.completer.get_completions(document, complete_event)

    def update(self, params):
        self.completer = self.from_params(params)

    @abstractmethod
    def from_params(self, params):
        NotImplemented


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

    def __init__(self, arg_desc):
        if not isinstance(arg_desc, list):
            raise ValueError("argument description is not a dictionary")

        self.arg_desc_list = arg_desc

    class State:
        def __init__(self, document, event, word_list, desc_list):
            self.document = document
            self.event = event
            self.word_list = word_list
            self.desc_list = desc_list
            self.last_desc = None
            self.value_list = None
            self.trailing_space = False

        pass

        def remove_positional(self):
            # positional arg: remove first POSITIONAL arg from description list
            for desc in self.desc_list:
                if desc.is_positional():
                    self.desc_list.remove(desc)
                    break

        def items(self) -> Iterable[Completion]:
            completion_items = []
            for desc in self.desc_list:
                if not desc.is_positional():
                    completion_items.append(desc.name)
                else:
                    # add remaining positionals
                    if desc.value:
                        for value in desc.value:
                            completion_items.append(value)
                    else:
                        completion_items.append(desc.name)

            completer = WordCompleter(completion_items)
            return completer.get_completions(self.document, self.event)

        def items_for_keyvalue(self, word: str) -> Iterable[Completion]:
            """Returns a list of completions based on the state of the key-value
               expression in the word.
               Possible outcomes are:
               - List of all keys
               - List of non-specified keys
               - Operator
               - Any value for the key (empty completion)

               Whichever the outcome list, it will include a 'comma' as key-value separator
            """

            if not self.last_desc.value:
                yield Completion('', start_position=0)

            # Copy the list of values, from which we remove elements as they are found
            # in the word
            provide_keys = True
            items = self.last_desc.value.copy()
            keyval_elements = word.split(',')
            while keyval_elements:
                keyval = keyval_elements.pop(0)
                key = keyval
                val = ''
                # separate key from value
                expression = []
                for op in promrest_builder.Series.OPERATORS:
                    expression = keyval.partition(op)
                    if expression[1] != '':
                        key = expression[0]
                        val = expression[2]
                        break

                if keyval_elements:
                    # If this is not the last keyval, remove it from the available key
                    if key in items:
                        items.remove(key)
                else:
                    # last keyval determines what to actually complete
                    if expression[0] != '' and expression[1] == '':
                        provide_keys = False
                        for op in promrest_builder.Series.OPERATORS:
                            yield Completion(op, start_position=0)
                    elif expression[1] != '':
                        provide_keys = False
                        if expression[2] != '':
                            yield Completion(',', start_position=0)
                        else:
                            yield Completion('<value>[,]', start_position=0)
                    elif expression[2] != '':
                        yield Completion(',', start_position=0)

            if provide_keys:
                for key in items:
                    # provide a list of extended items
                    yield Completion(key, start_position=0)

        def items_for_arg(self, word: str) -> Iterable[Completion]:
            if self.last_desc.is_keyvalue():
                return self.items_for_keyvalue(word)
            elif self.last_desc.is_flag():
                return self.items()
            else:
                completer = WordCompleter(self.last_desc.value)
                return completer.get_completions(self.document, self.event)

    def resolve_completion(self, state: State) -> Iterable[Completion]:
        """Recursive operation that traverses the list of words, processing one
        """

        if not state.word_list:
            # In the absence of words or last word, we display the available options
            return state.items()

        # iterate over all the words except the last one, which will determine
        # which completion to show.
        word = state.word_list.pop(0)
        last_word = not state.word_list
        matching_arg = ArgumentCompleter.find_option(state.desc_list, word)

        if last_word:
            # base case is the last word, which determines what the completion list
            # should be
            if state.trailing_space:
                if matching_arg:
                    state.last_desc = matching_arg
                    return state.items_for_arg('')
                elif not state.last_desc:
                    state.remove_positional()
            else:
                if state.last_desc:
                    return state.items_for_arg(word)

            return state.items()

        # else: For all previous word, skip one-time options and values that have been
        # already specified
        if matching_arg:
            state.desc_list.remove(matching_arg)
            state.last_desc = matching_arg
        else:
            if state.last_desc is None:
                # positional
                state.remove_positional()
                # either positional or option value, we set the last option desc to None
            state.last_desc = None

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
                self.arg_desc_list.copy())
        if text.endswith(' '):
            state.trailing_space = True

        for item in self.resolve_completion(state):
            yield item
        # Always add an 'empty' item as a way to prevent the prompt from automatically
        # adding the last remaining choice
        yield Completion('')

    def find_option(argdesc_list, name):
        for desc in argdesc_list:
            if (not desc.is_positional()) and name == desc.name:
                return desc

        return None
