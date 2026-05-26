import os

def delete_empty_folders(root_folder):
    for root, dirs, files in os.walk(root_folder, topdown=False):
        for folder in dirs:
            folder_path = os.path.join(root, folder)
            if not os.listdir(folder_path):
                print(f"Deleting empty folder: {folder_path}")
                os.rmdir(folder_path)


# 指定要遍历的根文件夹路径
root_folder_path = r"d:\ADC_data"

# 调用函数删除空文件夹
delete_empty_folders(root_folder_path)