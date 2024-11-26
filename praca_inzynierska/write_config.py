import json
import os

def write_config(path, variable):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path,'w') as file:
        json.dump(variable, file)
        file.close()
        return True
    return False