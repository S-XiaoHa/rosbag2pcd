import os
import shutil

def match_and_copy_pcd():
    # 1. 定义路径
    # PCD 源文件夹 (包含大量 .pcd 文件)
    pcd_source_dir = "/home/liujie/xbzl/bag_pcd/lidar_point_cloud_0"
    
    # 参考文件夹 (包含 .json 文件，作为筛选依据)
    json_ref_dir = "/home/liujie/code/xbzl_data-master/scene_1/camera_config"
    
    # PCD 目标保存文件夹 (匹配到的文件存到这里)
    pcd_dest_dir = "/home/liujie/code/xbzl_data-master/scene_1/lidar_point_cloud_0"

    # 2. 检查源目录是否存在
    if not os.path.exists(pcd_source_dir) or not os.path.exists(json_ref_dir):
        print("错误：源目录或参考目录不存在，请检查路径。")
        return

    # 3. 创建目标文件夹 (如果不存在则创建)
    if not os.path.exists(pcd_dest_dir):
        os.makedirs(pcd_dest_dir)
        print(f"已创建目标目录: {pcd_dest_dir}")

    # 4. 获取参考目录下的所有文件名 (去掉后缀 .json)
    print("正在读取参考文件名列表...")
    valid_names = set()
    for filename in os.listdir(json_ref_dir):
        if filename.endswith(".json"):
            # 获取文件名主干，例如 '1760429310.json' -> '1760429310'
            stem = os.path.splitext(filename)[0]
            valid_names.add(stem)
            
    print(f"参考列表中共有 {len(valid_names)} 个基准文件名。")

    # 5. 遍历 PCD 源目录并复制匹配的文件
    count = 0
    print("开始匹配并复制...")
    
    for filename in os.listdir(pcd_source_dir):
        if filename.endswith(".pcd"):
            stem = os.path.splitext(filename)[0]
            
            # 核心逻辑：如果 PCD 的文件名在 JSON 的集合里
            if stem in valid_names:
                source_file = os.path.join(pcd_source_dir, filename)
                dest_file = os.path.join(pcd_dest_dir, filename)
                
                try:
                    shutil.copy2(source_file, dest_file) # copy2 保留文件元数据
                    print(f"[复制成功] {filename}")
                    count += 1
                except Exception as e:
                    print(f"[复制失败] {filename}: {e}")

    print("-" * 30)
    print(f"处理完成！共成功复制了 {count} 个匹配的 PCD 文件。")
    print(f"文件保存在: {pcd_dest_dir}")

if __name__ == "__main__":
    match_and_copy_pcd()