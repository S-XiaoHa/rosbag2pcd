import os
import shutil

def replace_files_content():
    # 1. 源文件路径 (你要把内容复制出来的那个文件)
    source_file = "/home/liujie/code/xbzl_data-master/1763797063.json"
    
    # 2. 目标文件夹路径 (你要修改的那些文件所在的目录)
    target_dir = "/home/liujie/code/xbzl_data-master/scene_16/camera_config"

    # 检查源文件是否存在
    if not os.path.exists(source_file):
        print(f"错误: 源文件不存在 -> {source_file}")
        return

    # 遍历目标文件夹
    count = 0
    for filename in os.listdir(target_dir):
        # 只处理 .json 文件，且排除掉源文件本身（虽然源文件不在这个目录下，但作为好习惯）
        if filename.endswith(".json"):
            target_file_path = os.path.join(target_dir, filename)
            
            try:
                # 使用 shutil.copyfile 将源文件内容覆盖到目标文件
                # 这会保留目标文件的文件名，只改变内容
                shutil.copyfile(source_file, target_file_path)
                print(f"已替换内容: {filename}")
                count += 1
            except Exception as e:
                print(f"替换失败 {filename}: {e}")

    print("-" * 30)
    print(f"完成！共替换了 {count} 个文件。")

if __name__ == "__main__":
    replace_files_content()