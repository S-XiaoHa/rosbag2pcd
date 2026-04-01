import os
import shutil

# --- 配置路径 ---
# 源代码所在的根目录
SOURCE_ROOT = "/home/liujie/xbzl/bag_20251227_biaodingjian_caijiche/biaoding_parse"
# 目标保存根目录
TARGET_ROOT = "/home/liujie/xbzl/bag_20251227_biaodingjian_caijiche/biaoding_align"

# 需要处理的传感器文件夹名称
FOLDERS = [
    "CAM_FRONTMID", 
    "CAM_FRONTUP",
    "CAM_LEFTDOWN", 
    "CAM_RIGHTDOWN", 
    "CAM_FRONTDOWN", 
    "CAM_LEFTUP", 
    "CAM_RIGHTUP", 
    "LIDAR_RIGHT",
    "LIDAR_LEFT",
    "LIDAR_MID"
]

def truncate_timestamp(fname):
    """
    输入: 1758683129000352232.png 或 .pcd
    输出: 1758683129.png (去掉文件名主体最后9位)
    """
    base, ext = os.path.splitext(fname)
    if len(base) > 9:
        new_base = base[:-9]
        return new_base + ext
    return fname

def main():
    # 1. 遍历 data_parse 下的所有 bag 文件夹
    if not os.path.exists(SOURCE_ROOT):
        print(f"错误: 找不到源目录 {SOURCE_ROOT}")
        return

    bag_dirs = [d for d in os.listdir(SOURCE_ROOT) if d.startswith("bag_")]
    
    for bag_name in bag_dirs:
        bag_path = os.path.join(SOURCE_ROOT, bag_name)
        
        # 2. 遍历 bag 文件夹下的数字子目录 (0, 1, 2...)
        sub_dirs = [d for d in os.listdir(bag_path) if os.path.isdir(os.path.join(bag_path, d))]
        
        for sub_dir in sub_dirs:
            current_base_path = os.path.join(bag_path, sub_dir)
            
            # 3. 处理每个传感器文件夹
            for sensor in FOLDERS:
                src_sensor_dir = os.path.join(current_base_path, sensor)
                
                # 如果该路径不存在则跳过（防止某些包里缺少特定传感器）
                if not os.path.exists(src_sensor_dir):
                    continue
                
                # 构建目标路径：TARGET_ROOT/bag_日期/数字/传感器
                dst_sensor_dir = os.path.join(TARGET_ROOT, bag_name, sub_dir, sensor)
                os.makedirs(dst_sensor_dir, exist_ok=True)
                
                print(f"正在处理: {bag_name}/{sub_dir}/{sensor}")

                for fname in os.listdir(src_sensor_dir):
                    old_path = os.path.join(src_sensor_dir, fname)
                    
                    if not os.path.isfile(old_path):
                        continue
                        
                    new_name = truncate_timestamp(fname)
                    new_path = os.path.join(dst_sensor_dir, new_name)
                    
                    # 复制文件
                    shutil.copy2(old_path, new_path)

    print("\n任务完成！")

if __name__ == "__main__":
    main()