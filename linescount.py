import os

folder_path = "."

def get_items_in_dir(dir_path):
    dirs = os.listdir(dir_path)
    returns = []
    for item in dirs:
        item = (dir_path + "/").replace("//", "/") + item
        # print(item)
        if os.path.isdir(item):
            if item.split("/")[-1].startswith(".venv"):
                continue
            returns += (get_items_in_dir(item))
            continue
        returns.append(item)
    return returns

if __name__ == "__main__":
    items = get_items_in_dir(folder_path)
    py_items = []
    for item in items:
        if item.split(".")[-1] != "py":
            continue
        py_items.append(item)
    lines = 0
    for item in py_items:
        with open(item, 'r', encoding='utf-8') as py_file:
            lines += len(py_file.readlines())
    print(f"\"{folder_path}\" 文件夹里的 python 文件总共有 {lines} 行")
