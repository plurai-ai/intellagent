def dict_to_str(d: dict, mode='items') -> str:
    final_str = ''
    for key, value in d.items():
        if mode == 'items':
            final_str+=f'- {key}: {value}\n'
        elif mode == 'rows':
            final_str+=f'# {key}: \n{value}\n----------------\n'
    return final_str