import ast

def convert_json_strings(input_dict):
    """
    Recursively convert JSON strings in a dictionary back to dictionaries.
    """
    for key, value in input_dict.items():
        if isinstance(value, str):
            try:
                # Attempt to parse the string as JSON
                parsed_value = ast.literal_eval(value)
                # If successful, replace the string with the parsed dictionary or list
                input_dict[key] = parsed_value
                # If the parsed value is a dictionary, recurse into it
                if isinstance(parsed_value, dict):
                    convert_json_strings(parsed_value)
            except:
                # If it's not a valid JSON string, leave it as is
                pass
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            convert_json_strings(value)
    return input_dict