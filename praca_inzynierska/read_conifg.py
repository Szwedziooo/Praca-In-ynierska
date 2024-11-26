import json

def read_config(path):
    print("odczytano")
    with open(path,'r') as file:
        tmp = json.load(file)
        file.close()
        return tmp