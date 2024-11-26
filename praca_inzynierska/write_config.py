import json

def write_config(path, variable):
    with open(path,'w') as file:
        json.dump(variable, file)
        file.close()
        return True
    return False