import json
import os

def read_config(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'r') as file:
        tmp = json.load(file)
        file.close()
        print(path, " - ", tmp)
        return tmp