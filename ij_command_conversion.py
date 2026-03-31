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
            result += f' {key}={value}'
    return result

def command_str_to_dict(cmd: str) -> dict[str, str] | None:
    cmd_split = cmd.split()
    if len(cmd_split) == 0:
        return None
    result = {'command': cmd_split[0]}
    for param in cmd_split[1:]:
        param_split = param.split('=', 1)
        if len(param_split) == 2:
            result[param_split[0]] = param_split[1]
        else:
            result[param_split[0]] = ''
    return result