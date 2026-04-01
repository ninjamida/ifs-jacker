def command_dict_to_str(cmd_dict: dict[str, str]) -> str | None:
    result = cmd_dict.get('command', None)
    if result == None:
        return None
    for key, value in cmd_dict.items():
        if key == 'command':
            continue
        if value == '':
            result += f' {key}'
        else:
            result += f' {key}={escape(value)}'
    return result

def command_str_to_dict(cmd: str) -> dict[str, str] | None:
    cmd_split = cmd.split(None, 1)
    if len(cmd_split) == 0:
        return None
    result = {'command': cmd_split[0]}
    if len(cmd_split) > 1:
        quote_active = False
        escape_active = False
        build_str = ''
        param_name = None
        for i, c in enumerate(cmd_split[1]):
            if escape_active:
                if c == 'r':
                    build_str += '\r'
                elif c == 'n':
                    build_str += '\n'
                else:
                    build_str += c
                escape_active = False
                if i < len(cmd_split[1]) - 1:
                    continue

            if (
                ((c == ' ' or c == '\t') and not quote_active) or
                i == len(cmd_split[1]) - 1
                ):
                if param_name is None:
                    if len(build_str) > 0:
                        result[build_str] = ''
                else:
                    result[param_name] = build_str
                param_name = None
                build_str = ''
                continue
            
            if (c == '=' and param_name is None and not quote_active):
                param_name = build_str
                build_str = ''
                continue

            if c == '\\':
                escape_active = True
                continue

            if c == '"':
                quote_active = not quote_active
                continue

            build_str += c         

    return result

def escape(text: str) -> str:
    text = text.replace('\\', '\\\\')
    text = text.replace('\r', '\\r')
    text = text.replace('\n', '\\n')
    text = text.replace('"', '\\"')
    if ' ' in text or '\t' in text or '=' in text:
        text = f'"{text}"'
    return text