import json

def load_config(file_path='../config/config.txt'):
    try:
        with open(file_path, 'r') as file:
            config_data = json.load(file)
            return config_data
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    return {}

if __name__ == '__main__':
    config = load_config()

    if config:
        print("Loaded config:")
        for key, value in config.items():
            print(f"{key}: {value}")
