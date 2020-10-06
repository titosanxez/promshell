from promshell.shell import Shell, ShellProperty

if __name__ == "__main__":
    # __package__ = 'promshell'
    property = ShellProperty()

    property.prompt_name = "rtiddsstat"
    property.address = "localhost:9090"

    promStat = Shell(property)
    promStat.configure_autocompletion()

    while True:
        text = promStat.prompt.prompt()
        if text.strip() == '':
            continue
        # dispatch to appropriate handler
        arguments = None
        try:
            command_spec = text.strip().split(' ')
            arguments = promStat.parser.parse_args(command_spec)
        except SystemExit:
            continue

        try:
            # promStat.parser.exit = parser_exit
            # parse input: obtain list of commad words separated by space
            result = promStat.handler_map[arguments.command].handle(arguments)
            if (result):
                promStat.printer.pprint(result)
        except Exception as exc:
            print("command error:", exc)