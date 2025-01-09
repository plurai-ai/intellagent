import ast
import random
import string
import json


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


def fix_duplicate_indices_with_random_strings(df, length=6):
    """
    Modify duplicate indices in a DataFrame by assigning random strings.

    Parameters:
    - df: pandas.DataFrame
      The DataFrame whose index needs to be fixed.
    - length: int, optional (default=6)
      The length of the random string to assign to duplicate indices.

    Returns:
    - pandas.DataFrame
      A DataFrame with a unique index.
    """

    def generate_random_string(length=6):
        """Generate a random string of given length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    # Track seen indices
    seen_indices = set()
    new_index = []

    for idx in df.index:
        if idx in seen_indices:
            # Generate a random string for duplicate indices
            random_idx = generate_random_string(length)
            while random_idx in seen_indices:  # Ensure uniqueness
                random_idx = generate_random_string(length)
            new_index.append(random_idx)
            seen_indices.add(random_idx)
        else:
            new_index.append(idx)
            seen_indices.add(idx)

    df = df.copy()
    df.index = new_index
    return df


def get_dict_json(df, index_column):
    df = df.set_index(index_column, drop=False)
    js = df.to_dict(orient='index')
    return convert_json_strings(js)


def update_df(df, row, index_key):
    """
    Updates a row in a DataFrame based on the provided row dictionary.

    Parameters:
        df (pd.DataFrame): The DataFrame that should be updated .
        row (dict): The row data to update.
        index_key (str): The column name that identifies the index.

    Returns:
        None
    """
    for key, value in row.items():
        if key in df.columns:
            if isinstance(value, dict) or isinstance(value, list):
                value = json.dumps(value)  # Convert dictionaries or lists to JSON strings
            df.loc[df[index_key] == row[index_key], key] = value
