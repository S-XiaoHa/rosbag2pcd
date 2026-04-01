import json
import os

# ================= 配置路径 =================
INPUT_DIR = "/home/liujie/code/check_data/caitu-0-2-20260113034448/result"
OUTPUT_BASE_DIR = os.path.join(INPUT_DIR, "label") # 输出到新文件夹以示区别
OUTPUT_LIDAR_DIR = os.path.join(OUTPUT_BASE_DIR, "lidar")
OUTPUT_CAMERA_DIR = os.path.join(OUTPUT_BASE_DIR, "camera")

# ================= 转换逻辑 =================

def get_obj_type_id(class_name):
    """
    1: 行人
    2: 骑行者
    3: 小车
    4: 大车 (7座及以上)
    """
    name = str(class_name).lower()
    
    # 行人 (Pedestrian) -> 1
    if 'pedestrian' in name or 'person' in name:
        return "0"
    
    # 骑行者 (Cyclist) -> 2
    elif 'cyclist' in name or 'bike' in name or 'motor' in name:
        return "1"
    
    # 小车 (Car) -> 3
    elif 'car' in name:
        return "2"
    
    # 大车 (Truck/Bus) -> 4
    elif 'truck' in name or 'bus' in name or 'van' in name:
        return "3"
        
    else:
        return "4" # 其他/未知

def convert_single_file(file_path, filename_no_ext):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            xtreme_data = json.load(f)
    except Exception as e:
        print(f"❌ 读取文件失败 {file_path}: {e}")
        return None, None

    # 改为列表，去除外层的 "3": {} 这种 Key
    objects_list = [] 
    
    # 初始化 ID 计数器，每帧从 1 开始
    obj_counter = 1

    # 遍历 Xtreme1 列表中的所有数据源
    for entry in xtreme_data:
        if "objects" in entry:
            for obj in entry["objects"]:
                
                # 1. 生成新的 obj_id (单帧内唯一，从1开始)
                current_obj_id = str(obj_counter)
                obj_counter += 1
                
                # 2. 获取类别 ID
                class_name = obj.get("className", "")
                obj_type = get_obj_type_id(class_name)

                # 3. 提取 3D 信息
                contour = obj.get("contour", {})
                center = contour.get("center3D", {"x": 0, "y": 0, "z": 0})
                rotation = contour.get("rotation3D", {"x": 0, "y": 0, "z": 0})
                size = contour.get("size3D", {"x": 0, "y": 0, "z": 0})

                # 4. 构建单个目标结构
                standard_obj = {
                    "obj_id": current_obj_id,  # 使用重新生成的 ID
                    "obj_type": obj_type,
                    "psr": {
                        "position": {
                            "x": center.get("x", 0),
                            "y": center.get("y", 0),
                            "z": center.get("z", 0)
                        },
                        "rotation": {
                            "x": rotation.get("x", 0),
                            "y": rotation.get("y", 0),
                            "z": rotation.get("z", 0)
                        },
                        "scale": {
                            "x": size.get("x", 0),
                            "y": size.get("y", 0),
                            "z": size.get("z", 0)
                        }
                    }
                }
                
                # 添加到列表
                objects_list.append(standard_obj)

    # 构建 Lidar JSON
    lidar_data = {
        "lidars": {
            "middle": f"{filename_no_ext}.pcd", 
            "left": None
        },
        "objects": objects_list # 这里现在是一个列表 List
    }

    # 构建 Camera JSON
    camera_data = {
        "cameras": {
            "front": f"{filename_no_ext}.jpg",
            "back": None
        },
        "objects": objects_list # 这里的 objects 也是列表
    }

    return lidar_data, camera_data

# ================= 主程序 =================

def main():
    if not os.path.exists(OUTPUT_LIDAR_DIR):
        os.makedirs(OUTPUT_LIDAR_DIR)
    if not os.path.exists(OUTPUT_CAMERA_DIR):
        os.makedirs(OUTPUT_CAMERA_DIR)

    print(f"📂 输入目录: {INPUT_DIR}")
    print(f"📂 输出目录: {OUTPUT_BASE_DIR}")

    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
    total_files = len(files)
    print(f"🔍 发现 {total_files} 个 JSON 文件，开始处理...\n")

    count = 0
    for file_name in files:
        file_path = os.path.join(INPUT_DIR, file_name)
        filename_no_ext = os.path.splitext(file_name)[0]

        l_data, c_data = convert_single_file(file_path, filename_no_ext)

        if l_data and c_data:
            with open(os.path.join(OUTPUT_LIDAR_DIR, file_name), 'w', encoding='utf-8') as f:
                json.dump(l_data, f, indent=4, ensure_ascii=False)

            with open(os.path.join(OUTPUT_CAMERA_DIR, file_name), 'w', encoding='utf-8') as f:
                json.dump(c_data, f, indent=4, ensure_ascii=False)
            
            count += 1
            if count % 10 == 0:
                print(f"✅ 已处理 {count}/{total_files} 个文件...")

    print(f"\n🎉 处理完成! 结果保存在: {OUTPUT_BASE_DIR}")

if __name__ == "__main__":
    main()