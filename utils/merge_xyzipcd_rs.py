import numpy as np
import struct
import json
import os
import argparse

def read_pcd_binary_xyzi(path):
    """读取 binary PCD (x,y,z,intensity) 并返回 Nx4 numpy 数组"""
    with open(path, 'rb') as f:
        header = []
        while True:
            line = f.readline().decode('utf-8').strip()
            header.append(line)
            if line.startswith("DATA"):
                break

        # 获取点数
        points = 0
        width = 1  # 默认值
        height = 1  # 默认值
        for l in header:
            if l.startswith("POINTS"):
                points = int(l.split()[1])
            elif l.startswith("WIDTH"):
                width = int(l.split()[1])
            elif l.startswith("HEIGHT"):
                height = int(l.split()[1])

        # 读取 binary 数据
        data = f.read(points * 16)  # 每点 4*float*4 bytes = 16 字节
        points_np = np.frombuffer(data, dtype=np.float32).reshape(-1, 4)
        return points_np, header, width, height


def write_pcd_binary_xyzi_compatible(path, points, original_width, original_height):
    """按照原始格式写回 PCD，保持 WIDTH/HEIGHT 设置兼容性"""
    
    # 保持原始文件的 WIDTH 和 HEIGHT 设置
    if original_width == 1 and original_height > 1:
        # 原始是有组织的 (1列×N行)
        height = points.shape[0]
        width = 1
    else:
        # 其他情况：无组织点云
        width = points.shape[0]
        height = 1
    
    header = [
        "# .PCD v0.7 - Point Cloud Data file format",
        "VERSION 0.7",
        "FIELDS x y z intensity",
        "SIZE 4 4 4 4",
        "TYPE F F F F",
        "COUNT 1 1 1 1",
        f"WIDTH {width}",
        f"HEIGHT {height}",
        "VIEWPOINT 0 0 0 1 0 0 0",
        f"POINTS {points.shape[0]}",
        "DATA binary"
    ]
    
    with open(path, "wb") as f:
        for line in header:
            f.write((line + "\n").encode('utf-8'))
        
        # 写入数据（保持原始字节顺序）
        data = points.astype(np.float32).tobytes(order='C')
        f.write(data)


def apply_transform(points_xyzi, matrix):
    """对 xyz 做变换，intensity 不变"""
    xyz = points_xyzi[:, :3]
    i = points_xyzi[:, 3:]

    # 扩展为齐次坐标
    xyz_h = np.hstack((xyz, np.ones((xyz.shape[0], 1))))
    xyz_t = xyz_h @ matrix.T
    xyz_new = xyz_t[:, :3]

    return np.hstack((xyz_new, i))


def merge_all_lidars_compatible(timestamp, scene_dir, transforms):
    """兼容版：保持原始 PCD 的组织结构"""
    merged = None
    original_width = 1  # 默认值
    original_height = 1  # 默认值

    # 按正确的顺序处理雷达
    lidar_list = ["LIDAR_MID", "LIDAR_LEFT", "LIDAR_RIGHT"]

    for lidar_name in lidar_list:
        pcd_path = f"{scene_dir}/{lidar_name}/{timestamp}.pcd"
        if not os.path.exists(pcd_path):
            print(f"[WARN] 文件不存在: {pcd_path}")
            continue

        points_xyzi, header, width, height = read_pcd_binary_xyzi(pcd_path)

        # 记录第一个雷达的原始尺寸（通常是LIDAR_MID）
        if lidar_name == "LIDAR_MID":
            original_width = width
            original_height = height
            print(f"[INFO] {lidar_name} 原始尺寸: WIDTH={width}, HEIGHT={height}")

        if lidar_name != "LIDAR_MID":
            # 应用变换：将LEFT/RIGHT变换到LIDAR_MID坐标系
            if lidar_name in transforms:
                matrix = np.array(transforms[lidar_name])
                print(f"[INFO] 对 {lidar_name} 应用变换矩阵")
                points_xyzi = apply_transform(points_xyzi, matrix)

        if merged is None:
            merged = points_xyzi
        else:
            merged = np.vstack((merged, points_xyzi))

    if merged is None:
        print(f"[ERROR] 没有找到任何点云数据: {timestamp}")
        return

    # 检查数据有效性
    xyz = merged[:, :3]
    intensity = merged[:, 3]
    
    print(f"[INFO] 合并后点云统计:")
    print(f"       点数: {merged.shape[0]}")
    print(f"       X范围: [{xyz[:, 0].min():.2f}, {xyz[:, 0].max():.2f}]")
    print(f"       Y范围: [{xyz[:, 1].min():.2f}, {xyz[:, 1].max():.2f}]")
    print(f"       Z范围: [{xyz[:, 2].min():.2f}, {xyz[:, 2].max():.2f}]")
    print(f"       强度范围: [{intensity.min():.2f}, {intensity.max():.2f}]")
    
    # 检查NaN或inf值
    if np.any(np.isnan(xyz)) or np.any(np.isinf(xyz)):
        print("[WARN] 检测到NaN或Inf值，正在清理...")
        valid_mask = ~(np.isnan(xyz).any(axis=1) | np.isinf(xyz).any(axis=1))
        merged = merged[valid_mask]
        print(f"       清理后点数: {merged.shape[0]}")

    # 输出路径
    out_dir = f"{scene_dir}/lidar_point_cloud_0"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/{timestamp}.pcd"

    # 使用兼容的写入函数
    write_pcd_binary_xyzi_compatible(out_path, merged, original_width, original_height)
    print(f"[OK] 合并完成：{out_path}")


def main_compatible():
    parser = argparse.ArgumentParser(description="兼容版：合并多个雷达点云到TOP_32坐标系")
    parser.add_argument('--path', type=str, required=True, help='场景目录路径')
    parser.add_argument('--transform', type=str, default="utils/lidar2m32.json", 
                       help='变换矩阵JSON文件路径')
    parser.add_argument('--test-only', action='store_true', help='只测试第一帧')
    args = parser.parse_args()

    scene_dir = args.path

    # 读取外参
    try:
        with open(args.transform, "r") as f:
            transforms = json.load(f)
        print(f"[INFO] 已加载变换矩阵:")
        for lidar_name, matrix in transforms.items():
            matrix_np = np.array(matrix)
            print(f"       {lidar_name}: 形状={matrix_np.shape}")
    except Exception as e:
        print(f"[ERROR] 无法加载变换矩阵文件: {e}")
        return

    # 时间戳列表
    top32_dir = f"{scene_dir}/LIDAR_MID"
    if not os.path.exists(top32_dir):
        print(f"[ERROR] 目录不存在: {top32_dir}")
        return

    timestamps = sorted([
        f[:-4] for f in os.listdir(top32_dir) if f.endswith(".pcd")
    ])
    print(f"共检测到 {len(timestamps)} 个时间戳")

    # 处理每个时间戳
    for i, ts in enumerate(timestamps):
        print(f"\n[{i+1}/{len(timestamps)}] 处理时间戳: {ts}")
        merge_all_lidars_compatible(ts, scene_dir, transforms)
        
        if args.test_only and i == 0:
            print("\n[INFO] 测试模式：只处理第一帧")
            break


def check_pcd_structure(scene_dir):
    """检查原始PCD文件的结构"""
    print("=== 检查原始PCD文件结构 ===")
    
    lidars = ["LIDAR_MID", "LIDAR_LEFT", "LIDAR_RIGHT"]
    
    for lidar in lidars:
        lidar_dir = f"{scene_dir}/{lidar}"
        if not os.path.exists(lidar_dir):
            print(f"[WARN] 目录不存在: {lidar_dir}")
            continue
            
        pcd_files = [f for f in os.listdir(lidar_dir) if f.endswith(".pcd")]
        if not pcd_files:
            print(f"[WARN] {lidar} 没有PCD文件")
            continue
            
        first_pcd = pcd_files[0]
        pcd_path = f"{lidar_dir}/{first_pcd}"
        
        print(f"\n--- {lidar} ({first_pcd}) ---")
        
        with open(pcd_path, 'rb') as f:
            lines = []
            while True:
                try:
                    line = f.readline().decode('utf-8').strip()
                except:
                    break
                    
                if not line:
                    break
                    
                lines.append(line)
                if line.startswith("DATA"):
                    break
            
            # 提取关键信息
            points = 0
            width = 1
            height = 1
            data_type = "binary"
            
            for line in lines:
                if line.startswith("POINTS"):
                    points = int(line.split()[1])
                elif line.startswith("WIDTH"):
                    width = int(line.split()[1])
                elif line.startswith("HEIGHT"):
                    height = int(line.split()[1])
                elif line.startswith("DATA"):
                    data_type = line.split()[1]
            
            print(f"  POINTS: {points}")
            print(f"  WIDTH: {width}")
            print(f"  HEIGHT: {height}")
            print(f"  DATA: {data_type}")
            print(f"  结构: {'有组织的' if width == 1 and height > 1 else '无组织的'}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # 检查模式
        if len(sys.argv) > 2:
            check_pcd_structure(sys.argv[2])
        else:
            print("用法: python merge_xyzipcd.py --check <场景目录>")
    else:
        # 正常合并模式
        main_compatible()