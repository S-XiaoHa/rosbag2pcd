import numpy as np
import os
import math
import argparse

# ---------------- 配置区域 ----------------
# Lidar -> Base_link矩阵
# final-extrinsic.json 里的 "LIDAR_ZHU" 
TRANSFORM_MATRIX = np.array([
    [0.9995573062977514, -0.005867217025824479, 0.029167913726474395, 1.242380619049072],
    [0.0058177927724382215, 0.9999814939630773, 0.0017790499231211832, -0.001938401255756617],
    [-0.029177812015984742, -0.0016085694712592474, 0.9995729427061419, 2.319513082504272],
    [0.0, 0.0, 0.0, 1.0]
])
# ----------------------------------------

def transform_point(point, matrix):
    """变换 xyz 坐标"""
    # point: [x, y, z]
    # 构造齐次坐标 [x, y, z, 1]
    point_homo = np.append(point, 1.0)
    # 矩阵乘法
    point_new = np.dot(matrix, point_homo)
    return point_new[:3] # 返回 x, y, z

def transform_yaw(yaw, matrix):
    """变换朝向角 (Yaw)"""
    # 1. 将 Yaw 转换为局部方向向量 (假设物体在平面上朝向)
    # 向量为: [cos(yaw), sin(yaw), 0]
    direction_vec = np.array([math.cos(yaw), math.sin(yaw), 0.0, 0.0]) # 向量w=0
    
    # 2. 旋转向量
    direction_new = np.dot(matrix, direction_vec)
    
    # 3. 计算新的 Yaw (atan2 处理 x, y 分量)
    new_yaw = math.atan2(direction_new[1], direction_new[0])
    return new_yaw

def process_line(line):
    """处理单行标注数据"""
    parts = line.strip().split()
    if len(parts) < 8:
        return line # 数据不完整直接返回
    
    # 解析数据 (根据你的示例: x y z l w h yaw class)
    try:
        x = float(parts[0])
        y = float(parts[1])
        z = float(parts[2])
        l = float(parts[3]) # 尺寸保持不变
        w = float(parts[4])
        h = float(parts[5])
        yaw = float(parts[6])
        cls = parts[7]      # 类别字符串
        
        # 1. 变换中心点
        new_xyz = transform_point(np.array([x, y, z]), TRANSFORM_MATRIX)
        
        # 2. 变换角度
        new_yaw = transform_yaw(yaw, TRANSFORM_MATRIX)
        
        # 3. 重新组装字符串 (保留3位或6位小数)
        new_line = f"{new_xyz[0]:.6f} {new_xyz[1]:.6f} {new_xyz[2]:.6f} " \
                   f"{l:.6f} {w:.6f} {h:.6f} {new_yaw:.6f} {cls}"
        return new_line
        
    except ValueError:
        print(f"Skipping invalid line: {line}")
        return line

def main():
    parser = argparse.ArgumentParser(description="将标注结果从 LiDAR 坐标系变换到 Base_link")
    parser.add_argument('--input_dir', type=str,default="scene_16/labels", help='原始标注文件夹 (txt)')
    parser.add_argument('--output_dir', type=str, default="scene_16/new_labels", help='输出的新标注文件夹')
    args = parser.parse_args()
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        
    files = [f for f in os.listdir(args.input_dir) if f.endswith('.txt')]
    print(f"Found {len(files)} label files.")
    
    for filename in files:
        src_path = os.path.join(args.input_dir, filename)
        dst_path = os.path.join(args.output_dir, filename)
        
        with open(src_path, 'r') as f_in, open(dst_path, 'w') as f_out:
            lines = f_in.readlines()
            for line in lines:
                new_line = process_line(line)
                f_out.write(new_line + '\n')
                
    print(f"Done! Transformed labels saved to {args.output_dir}")

if __name__ == '__main__':
    main()