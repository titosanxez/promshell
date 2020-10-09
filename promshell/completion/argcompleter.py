from abc import ABC, abstractmethod
from typing import List, Iterable, Mapping

from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.completion.word_completer import WordCompleter
from promshell.arguments import ArgDescriptor


class CompletionContext:
    """
    This is a class that represents a state of elements provided as part of
    the argument completion. This class allows grouping the elements in a single
    object instead of passing multiple parameters, as well as easier evolution
    without breaking interfaces.

    :param document: Document object associated with the prompt
    :type document: :class:`prompt_toolkit.document.Document`
    :param event: event object that caused the completion
    :type event: :class:`prompt_toolkit.completion.CompleteEvent`
    :param arg_descriptor: Descriptor of the argument for which the completion
        triggers
    :type arg_descriptor: :class:`promshell.arguments.ArgDescriptor`
    :param word: Last word preceding the cursor. Default is '' when only spaces
        precede the completion
    :type word: str, optional
    """
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
    """
        Interface to generate completions for individual arguments.
    """

    @abstractmethod
    def get_completions(self, context: CompletionContext) -> Iterable[Completion]:
        """
        Generator that yield `Completion` objects. This operation is invoked whenever
        a completion event triggers for an argument, whose descriptor is contained
        in the `context` parameter.

        Implementations can delegate to existing completers for the final result. For
        example an expected pattern is to have a `ValueCompleter` implementation to
        obtain the a list of possible choices and rely on a `WordCompleter`. For
        example:

        .. code-block:: python

            arg_choices = [...] # list of possible values for the argument
            return WordCompleter(arg_choices).get_completions(
                context.document,
                context.event)

        :param context: Container of elements associated with the completion
            event.
        :type context: :class:`.CompletionContext`.
        :return: An iterable object of completions.
        :rtype: Iterable[prompt_toolkit.completion.Completion]
        """
        NotImplemented


class KeyValueCompleter(ValueCompleter):
    """
    Implementation of a :class:`.ValueCompleter` that compute the completions
    for an expression consisting of comma-separated name-value pairs:

    .. code-block:: console

        <name1><op><value1>,<name2><op><value2>,...,<nameN><op><valueN>

    where:
    - <name> name of the item being assigned
    - <op> operator of the assignment expression
    - <value> value assigned to the item

    The implementation assumes a known list of name items (keys) and
    an infinite set of values, that is, any string is a valid value for a key.

    :param key_names: List of item names part of the left-side expression
    :type key_names: List[str]
    :param operators: List of possible operators. Default is ['=']
    :type operators: List[str]
    """

    def __init__(self, key_names: List[str], operators: List[str] = ['=']):
        self.key_names = key_names
        self.operators = operators

    def get_completions(
            self,
            context: CompletionContext) -> Iterable[Completion]:
        """
        Generates completions based on the state of the key-value expression in the word.
        Possible outcomes are:

            - List of all keys
            - List of non-specified keys
            - Operator
            - Any value for the key (empty completion)

        Based on the completion state, it will also generate a `Completion`
        containing the 'comma' as key-value separator.
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
            for op in self.operators:
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
                    for op in self.operators:
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
            key_completer = WordCompleter(used_keys)
            for key in key_completer.get_completions(context.document, context.event):
                # provide a list of extended items
                yield Completion(
                    key.text,
                    start_position=key.start_position,
                    style='fg:ansiblue')


class ArgumentCompleter(Completer):
    """
    Implementation of a :class:`prompt_toolkit.complete.Completer` that interprets
    a command-line option sequence with known description and generates the
    proper set of completions:

    The argument model for the completer is based on a set of `ArgDescriptor`
    objects, where each item represents a possible option. The completer
    semantics are based on:

    - Use ArgDescriptor set to determine which available options and/or values
      can be part of the completion.
    - Remove options from the completion sequence based on their multiplicity
      (e.g., `nargs=?` can appear only once). This is similar to the semantics
      of the argparse.ArgumentParser itself.
    - Completing for a specific option (matching the last word following a space)
      generates only the possible values for the option. This is performed
      through a `ValueCompleter`, the list of option `choices`, or simply showing
      the `metavar` description of the argument.

    :param arg_desc_set: ArgDescriptor set that specifies the syntax and semantics
        of the possible command sequence
    :type arg_desc_set: Mapping[str, dict]
    :param completer: Implementation of a `ValueCompleter` to be invoked for the
    completion of argument values. Default is `None`
    :type completer: :class:`.ValueCompleter`, optional
    """
    def __init__(
            self,
            arg_desc_set: Mapping[str, dict],
            completer: ValueCompleter = None):
        self.arg_desc_list = arg_desc_set
        self.value_completer = completer

        if isinstance(arg_desc_set, dict):
            self.arg_desc_list = []
            for key in arg_desc_set:
                self.arg_desc_list.append(ArgDescriptor(key, **arg_desc_set[key]))
        elif not isinstance(arg_desc_set, list):
            raise ValueError("argument description is not a dictionary or list ")

    #
    # State implementation
    #
    class State:
        """
        A class to consolidate the state of the arguments completion and provide
        behavior to determine the required completion.
        """
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
            """
                Removes the first occurrence of a positional argument in the
                current argument descriptor list.
            """
            for desc in self.arg_desc_list:
                if desc.is_positional():
                    self.arg_desc_list.remove(desc)
                    break

        def completion_for_argument_set(self) -> Iterable[Completion]:
            """
            Generates the completions for the remaining set of arguments
            that can be specified. That is, yields a `Completion` for each
            argument available in the descriptor list.

            For positional arguments, it will attempt to complete the list of
            possible values for the positional.

            :return: `Completion` yields for the current set of arguments
            :rtype: Iterable[Completion]
            """
            completion_items = []
            for arg_descriptor in self.arg_desc_list:
                if arg_descriptor.is_positional():
                    for c in self.completion_for_positional(arg_descriptor):
                        yield c
                else:
                    completion_items.append(arg_descriptor.flags[0])

            completer = WordCompleter(completion_items)
            for c in completer.get_completions(self.document, self.event):
                yield c

        def completion_for_positional(
                self,
                arg_descriptor: ArgDescriptor,
                word: str = '') -> Iterable[Completion]:
            """
            Generates the completions for the specified positional argument.

            :param arg_descriptor: Descriptor for the positional argument
            :type arg_descriptor: `shell.arguments.ArgDescriptor`
            :param word: Text word upon the completion is invoked. Default is ''
            :type word: str
            :return: yields `Completions`
            """
            assert arg_descriptor.is_positional()
            if self.completer:
                context = CompletionContext(
                    self.document,
                    self.event,
                    arg_descriptor,
                    word
                )
                return self.completer.get_completions(context)

            return WordCompleter(arg_descriptor.choices).get_completions(
               self.document,
               self.event
           )

        def completion_for_argument(self, word: str) -> Iterable[Completion]:
            """
            Generates the completions for the current argument, that is, the
            last word that matches an argument in the descriptor set, following a
            space.

            param word: Text word upon the completion is invoked. Default is ''
            :type word: str
            :return: yields `Completions`
            """

            if self.arg_descriptor.is_flag():
                return self.completion_for_argument_set()

            return self.completion_for_positional(self.arg_descriptor)

        def find_option_argument(self, name) -> ArgDescriptor:
            """
            Looks up non-positional argument in the current list of remaining
            arguments, provided its option flag as defined for the `ArgumentParsers`.

            :param name: Name of the argument descriptor
            :return: :class:`arguments.ArgDescriptor` or None if not found.
            """
            for desc in self.arg_desc_list:
                if (not desc.is_positional()) and name in desc.flags:
                    return desc

            return None

    #
    # ArgumentCompleter implementation
    #
    def resolve_completion(self, state: State) -> Iterable[Completion]:
        """
        Recursive operation to generate the completions for a specified command line.
        This operation processes each word in the line (part of the `state`) to
        discard already specified arguments and determine the valid completions.
        """
        empty_line = not state.word_list
        if empty_line:
            # Complete the available options
            return state.completion_for_argument_set()

        # iterate over all the words except the last one, which ultimately
        # determines which completion to show.
        word = state.word_list.pop(0)
        last_word = not state.word_list
        matching_arg = state.find_option_argument(word)
        if last_word:
            # base case
            if state.trailing_space:
                if matching_arg:
                    state.arg_descriptor = matching_arg
                    return state.completion_for_argument('')
                elif not state.arg_descriptor:
                    state.remove_positional()
            else:
                if state.arg_descriptor:
                    return state.completion_for_argument(word)

            return state.completion_for_argument_set()

        # else: For all previous words, discard options and values already specified
        if matching_arg:
            state.arg_desc_list.remove(matching_arg)
            state.arg_descriptor = matching_arg
        else:
            previous_word_is_option = state.arg_descriptor is not None
            if not previous_word_is_option:
                # When the previous word did not match an option, then the current
                # word shall be a positional
                state.remove_positional()

            # else is an option value. Either way, the current descriptor is not
            # a matching option
            state.arg_descriptor = None

        return self.resolve_completion(state)

    def get_completions(self, document, complete_event):
        """
            Generates completions for the current command option line.
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
