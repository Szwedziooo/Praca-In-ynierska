import json
import os

def read_config(path):
    print("odczytano")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'r') as file:
        tmp = json.load(file)
        file.close()
        return tmp