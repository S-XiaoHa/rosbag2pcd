import os
import shutil
import random
import argparse
from glob import glob
from collections import defaultdict, Counter
import numpy as np
from tqdm import tqdm

# ================= 配置区域 =================
# 建议通过命令行传参，这里保留默认值方便调试
DEFAULT_SOURCE_DIR = "/home/liujie/code/xbzl_data-master"  
DEFAULT_OUTPUT_DIR = "/home/liujie/code/ADML3D/data/custom"
MAX_FRAMES_PER_SCENE = 300
VAL_RATIO = 0.15
LABELS = ['car', 'truck', 'bus', 'bicycle', 'pedestrian']
NUM_CAM = 5
# ===========================================

def parse_label_file(label_file):
    """读取 label 文件，返回该帧包含的类别列表"""
    classes = []
    if not os.path.exists(label_file):
        return classes
    with open(label_file, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 8:
                cls = parts[7] # 假设第8列是类别
                if cls in LABELS:
                    classes.append(cls)
    return classes

def save_statistics(scene_dir, frames_list):
    """为生成的场景生成 statistics.txt"""
    class_counts = defaultdict(int)
    for f in frames_list:
        for c in f['classes']:
            class_counts[c] += 1
    
    total_frames = len(frames_list)
    stat_file = os.path.join(scene_dir, 'statistics.txt')
    
    with open(stat_file, 'w') as f:
        f.write(f"总帧数: {total_frames}\n")
        f.write("类别分布:\n")
        for cls in LABELS: # 按固定顺序输出
            count = class_counts.get(cls, 0)


            
            f.write(f"{cls}: {count}\n")

def collect_all_frames(source_dir):
    frames = []
    # 查找所有 scene_* 文件夹
    scenes = sorted([d for d in os.listdir(source_dir) if d.startswith("scene_") and os.path.isdir(os.path.join(source_dir, d))])
    
    if not scenes:
        print(f"[Error] 在 {source_dir} 下未找到 scene_ 开头的文件夹")
        return []

    print(f"发现 {len(scenes)} 个源场景: {scenes}")

    for scene in scenes:
        label_dir = os.path.join(source_dir, scene, "labels")
        if not os.path.exists(label_dir):
            continue
            
        # 查找所有txt
        label_files = sorted(glob(os.path.join(label_dir, "*.txt")))
        
        for lf in tqdm(label_files, desc=f"解析 {scene}", leave=False):
            filename = os.path.basename(lf)
            frame_id = os.path.splitext(filename)[0]
            classes = parse_label_file(lf)
            
            frames.append({
                "original_scene": scene,
                "frame_id": frame_id,
                "src_path": os.path.join(source_dir, scene), # 记录源路径方便复制
                "classes": classes,
            })
    return frames

def check_distribution(frames, name="Set"):
    """统计并打印分布百分比，用于验证平衡性"""
    counter = Counter()
    for f in frames:
        counter.update(f["classes"])
    
    total_objects = sum(counter.values())
    print(f"\n--- {name} (共 {len(frames)} 帧, {total_objects} 个物体) ---")
    if total_objects == 0:
        return {}
        
    stats = {}
    for cls in LABELS:
        count = counter[cls]
        pct = (count / total_objects) * 100
        stats[cls] = pct
        print(f"{cls:<10}: {count:>5} ({pct:.2f}%)")
    return stats

def process_chunk_and_copy(frames, output_root, split_name):
    """
    1. 切分数据
    2. 创建文件夹
    3. 复制 Config (改为按帧复制!)
    4. 复制 Data (每帧一次)
    5. 生成 Statistics
    """
    total_frames = len(frames)
    chunks = [frames[i:i + MAX_FRAMES_PER_SCENE] for i in range(0, total_frames, MAX_FRAMES_PER_SCENE)]
    
    print(f"\n正在生成 {split_name} 数据集，共 {len(chunks)} 个场景...")

    for idx, chunk in enumerate(chunks):
        new_scene_name = f"{split_name}_scene_{idx:03d}" 
        new_scene_path = os.path.join(output_root, split_name, new_scene_name)
        
        # 1. 创建基础目录
        os.makedirs(new_scene_path, exist_ok=True)
        os.makedirs(os.path.join(new_scene_path, "labels"), exist_ok=True)
        os.makedirs(os.path.join(new_scene_path, "lidar_point_cloud_0"), exist_ok=True)
        # Config 目录也要创建
        os.makedirs(os.path.join(new_scene_path, "camera_config"), exist_ok=True) 
        
        for i in range(NUM_CAM):
            os.makedirs(os.path.join(new_scene_path, f"camera_image_{i}"), exist_ok=True)

        # 2. 【已删除】原先的批量复制 Config 代码块被删除了
        # 我们把它移动到下面的循环里，针对每一帧单独复制

        # 3. 复制每一帧的数据
        for frame in tqdm(chunk, desc=f"Writing {new_scene_name}", leave=False):
            src_root = frame['src_path']
            fid = frame['frame_id']
            
            # --- (A) 复制 Labels ---
            shutil.copy2(
                os.path.join(src_root, "labels", f"{fid}.txt"),
                os.path.join(new_scene_path, "labels", f"{fid}.txt")
            )
            
            # --- (B) 复制 Config (新增逻辑) ---
            # 假设 config 文件名和 frame_id 一致 (例如 123456.json 或 123456.txt)
            # 我们去源目录找名字匹配的文件
            src_config_dir = os.path.join(src_root, "camera_config")
            dst_config_dir = os.path.join(new_scene_path, "camera_config")
            
            # 使用 glob 查找该帧对应的 config 文件（匹配任意后缀）
            config_pattern = os.path.join(src_config_dir, f"{fid}.*")
            found_configs = glob(config_pattern)
            
            if found_configs:
                for cf in found_configs:
                    shutil.copy2(cf, dst_config_dir)
            else:
                # 备用方案：如果你的 config 不是按帧命名的，而是静态的（所有帧共用一个）
                # 这种情况下才需要特殊处理。但根据你的描述“文件变多”，说明是按帧命名的。
                pass

            # --- (C) 复制 Lidar ---
            src_lidar = os.path.join(src_root, "lidar_point_cloud_0", f"{fid}.pcd")
            if os.path.exists(src_lidar):
                shutil.copy2(src_lidar, os.path.join(new_scene_path, "lidar_point_cloud_0", f"{fid}.pcd"))
            
            # --- (D) 复制 Cameras ---
            for cam_i in range(NUM_CAM):
                src_cam = os.path.join(src_root, f"camera_image_{cam_i}", f"{fid}.png") 
                if not os.path.exists(src_cam): 
                    src_cam = os.path.join(src_root, f"camera_image_{cam_i}", f"{fid}.jpg")
                
                if os.path.exists(src_cam):
                    dst_cam = os.path.join(new_scene_path, f"camera_image_{cam_i}", os.path.basename(src_cam))
                    shutil.copy2(src_cam, dst_cam)

        # 4. 生成统计文件
        save_statistics(new_scene_path, chunk)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=str, default=DEFAULT_SOURCE_DIR, help='源数据根目录')
    parser.add_argument('--output', type=str, default=DEFAULT_OUTPUT_DIR, help='输出目录')
    args = parser.parse_args()

    # 1. 收集
    all_frames = collect_all_frames(args.source)
    if not all_frames:
        return

    # 2. 全局打乱 (这是最核心的一步，打乱后切分即满足同分布)
    # 使用固定种子复现
    random.seed(42)
    random.shuffle(all_frames)

    # 3. 划分索引
    total_num = len(all_frames)
    val_num = int(total_num * VAL_RATIO)
    train_num = total_num - val_num
    
    train_frames = all_frames[:train_num]
    val_frames = all_frames[train_num:]

    # 4. 验证分布 (如果不满意，可以重跑，但大数定律保证基本一致)
    print("="*40)
    print("分布一致性检查")
    t_stats = check_distribution(train_frames, "TRAIN SET")
    v_stats = check_distribution(val_frames, "VAL SET")
    print("="*40)

    # 简单检查差异
    max_diff = 0
    for cls in LABELS:
        diff = abs(t_stats.get(cls, 0) - v_stats.get(cls, 0))
        max_diff = max(max_diff, diff)
    print(f"最大类别分布差异: {max_diff:.2f}% (通常 < 2-3% 即为优秀)")

    confirm = input("\n确认开始复制文件? [y/n]: ")
    if confirm.lower() != 'y':
        return

    # 5. 执行复制
    if os.path.exists(args.output):
        print(f"[Warning] 输出目录 {args.output} 已存在，新文件将合并/覆盖。")
    
    process_chunk_and_copy(train_frames, args.output, "train")
    process_chunk_and_copy(val_frames, args.output, "val")

    print(f"\n✅ 全部完成！输出路径: {args.output}")

if __name__ == "__main__":
    main()