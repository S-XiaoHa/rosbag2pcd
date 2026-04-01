import numpy as np
import json
import os
import argparse
import struct

# ---------------- 配置区域 ----------------
# 雷达文件夹名称与 JSON 键值的映射关系
# 请根据你实际的文件夹名称修改字典的 Key
LIDAR_MAP = {
    # "文件夹名称": "final-extrinsic.json 中的 Key"
    "LIDAR_TOP_32": "LIDAR_ZHU",       # 主雷达
    "LIDAR_FRONT": "LIDAR_FRONT",  # 前雷达
    "LIDAR_REAR": "LIDAR_REAR"     # 后雷达 
}
# ----------------------------------------

def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def read_pcd_with_intensity(file_path):
    """
    读取 PCD 文件并保留强度信息 (支持 ASCII 和 Binary 格式)
    返回: numpy array (N, 4) -> [x, y, z, intensity]
    """
    if not os.path.exists(file_path):
        # 很多时候某些帧可能某个雷达没数据，报 Warning 但不中断
        # print(f"[Warning] File not found: {file_path}") 
        return np.zeros((0, 4), dtype=np.float32)

    with open(file_path, 'rb') as f:
        header = []
        while True:
            line = f.readline().decode('utf-8').strip()
            header.append(line)
            if line.startswith('DATA'):
                break
        
        # 解析 Header
        data_type = 'ascii'
        for line in header:
            if line.startswith('DATA'):
                data_type = line.split()[-1]
            if line.startswith('POINTS'):
                num_points = int(line.split()[1])
        
        if data_type == 'ascii':
            data = np.loadtxt(f, dtype=np.float32)
            # 兼容只有 XYZ 的情况
            if data.ndim == 1: data = data.reshape(1, -1)
            if data.shape[1] == 3:
                data = np.hstack((data, np.zeros((data.shape[0], 1))))
            return data[:, :4]
            
        elif data_type == 'binary':
            content = f.read()
            # 假设 float32 x 4 (x, y, z, i)
            expected_floats = num_points * 4 
            if len(content) >= expected_floats * 4:
                data = np.frombuffer(content, dtype=np.float32)
                data = data.reshape(-1, 4)
                return data
            else:
                # 尝试只读 xyz
                data = np.frombuffer(content, dtype=np.float32)
                data = data.reshape(-1, 3)
                return np.hstack((data, np.zeros((data.shape[0], 1))))
        else:
            print(f"[Error] Unsupported PCD data type: {data_type}")
            return np.zeros((0, 4), dtype=np.float32)

def save_pcd_with_intensity(points, file_path):
    """保存为 ASCII PCD，包含 intensity"""
    num_points = len(points)
    header = f"""# .PCD v0.7 - Point Cloud Data file format
VERSION 0.7
FIELDS x y z intensity
SIZE 4 4 4 4
TYPE F F F F
COUNT 1 1 1 1
WIDTH {num_points}
HEIGHT 1
VIEWPOINT 0 0 0 1 0 0 0
POINTS {num_points}
DATA ascii
"""
    with open(file_path, 'w') as f:
        f.write(header)
        if num_points > 0:
            np.savetxt(f, points, fmt='%.6f %.6f %.6f %.2f')
    print(f"已保存: {file_path} (点数: {num_points})")

def apply_transform_numpy(points, matrix):
    """对点云进行刚体变换 (N,4) -> (N,4)"""
    if len(points) == 0:
        return points
    
    xyz = points[:, :3]
    intensity = points[:, 3:]
    
    # 构造齐次坐标
    ones = np.ones((xyz.shape[0], 1))
    xyz_homo = np.hstack((xyz, ones))
    
    # 变换: (T * P^T)^T
    xyz_transformed = np.dot(matrix, xyz_homo.T).T
    
    return np.hstack((xyz_transformed[:, :3], intensity))

def merge_lidars(timestamp, scene_dir, extrinsic_data):
    merged_points_list = []
    
    for folder_name, json_key in LIDAR_MAP.items():
        # 拼接读取路径
        pcd_path = os.path.join(scene_dir, folder_name, f"{timestamp}.pcd")
        
        # 1. 读取 (保留强度)
        points = read_pcd_with_intensity(pcd_path)
        if len(points) == 0:
            continue
            
        # 2. 变换 (直接变换到 Base_link)
        if json_key in extrinsic_data:
            trans_matrix = np.array(extrinsic_data[json_key])
            points_transformed = apply_transform_numpy(points, trans_matrix)
            merged_points_list.append(points_transformed)
        else:
            print(f"[Error] JSON中找不到Key: {json_key}")

    # 3. 合并与保存
    if merged_points_list:
        final_points = np.vstack(merged_points_list)
        
        # --- 修改处：输出路径为 lidar_point_cloud_0 ---
        output_dir = os.path.join(scene_dir, "lidar_point_cloud_0")
        os.makedirs(output_dir, exist_ok=True)
        
        save_path = os.path.join(output_dir, f"{timestamp}.pcd")
        save_pcd_with_intensity(final_points, save_path)
    else:
        print(f"Timestamp {timestamp}: 没有读取到任何雷达数据")

def main():
    parser = argparse.ArgumentParser(description="合并多雷达点云到 Base_link 并保留强度")
    parser.add_argument('--path', type=str, default='/home/liujie/xbzl/bag_pcd', help='场景路径，例如 scene_1')
    parser.add_argument('--extrinsic', type=str, default='utils/final-extrinsic.json', help='外参文件路径')
    args = parser.parse_args()
    
    scene_dir = args.path
    
    # 加载外参
    if not os.path.exists(args.extrinsic):
        print(f"Error: 找不到外参文件 {args.extrinsic}")
        return
    extrinsic_data = load_json(args.extrinsic)
    
    # 确定主雷达目录以获取时间戳
    # 这里默认使用 LIDAR_MAP 的第一个键作为主目录来遍历文件名
    main_lidar_folder = list(LIDAR_MAP.keys())[0]
    lidar_path = os.path.join(scene_dir, main_lidar_folder)
    
    if not os.path.exists(lidar_path):
        print(f"Error: 主雷达目录不存在: {lidar_path}. 请检查 LIDAR_MAP 配置。")
        return

    # 获取所有时间戳
    timestamps = sorted([f.split('.')[0] for f in os.listdir(lidar_path) if f.endswith('.pcd')])
    
    print(f"开始处理 {len(timestamps)} 帧数据...")
    print(f"输入目录: {scene_dir}")
    print(f"输出目录: {os.path.join(scene_dir, 'lidar_point_cloud_0')}")
    
    for ts in timestamps:
        merge_lidars(ts, scene_dir, extrinsic_data)
        
    print("处理完成。")

if __name__ == '__main__':
    main()