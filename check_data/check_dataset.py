import os
import argparse
from glob import glob
from collections import defaultdict
import time

# ================= 配置参数 =================
# 传感器文件夹列表及常见文件扩展名 (用于查找匹配)
SENSOR_CONFIG = {
    "labels": [".txt"],  # 标签是地面真值
    "camera_config": [".json", ".txt", ".yaml"], # config 文件可能有多重扩展名
    "lidar_point_cloud_0": [".pcd", ".bin"],
    "camera_image_0": [".png", ".jpg"],
    "camera_image_1": [".png", ".jpg"],
    "camera_image_2": [".png", ".jpg"],
    "camera_image_3": [".png", ".jpg"],
    "camera_image_4": [".png", ".jpg"],
}
# ===========================================

def get_stems_from_folder(folder_path, extensions):
    """获取给定文件夹内所有符合扩展名的文件 stem (帧ID) 的集合"""
    stems = set()
    for ext in extensions:
        # 使用 glob 查找所有匹配的文件
        files = glob(os.path.join(folder_path, f"*{ext}"))
        for f in files:
            stems.add(os.path.splitext(os.path.basename(f))[0])
    return stems


def check_scene_integrity(scene_path):
    """检查单个场景文件夹的数据完整性和纯净性"""
    results = []
    is_pass = True
    
    # 1. 获取地面真值清单 (Labels Stems)
    label_dir = os.path.join(scene_path, "labels")
    if not os.path.exists(label_dir):
        return [f"[FAIL] 缺少核心目录: {label_dir}"], False

    # 获取 Labels 文件夹中所有文件的 Stem (帧ID) 集合，作为 Ground Truth (GT)
    gt_stems = get_stems_from_folder(label_dir, SENSOR_CONFIG['labels'])
    N = len(gt_stems)
    
    if N == 0:
        return [f"[FAIL] {scene_path}: labels 目录为空，无法检查"], False

    results.append(f"[INFO] 找到 {N} 个核心帧 (基于 labels)。")

    # 2. 遍历所有传感器文件夹进行双向检查
    for folder_name, extensions in SENSOR_CONFIG.items():
        sensor_dir = os.path.join(scene_path, folder_name)
        
        # 2a. 检查目录是否存在
        if not os.path.exists(sensor_dir):
            results.append(f"[FAIL] 缺少传感器目录: {folder_name}")
            is_pass = False
            continue

        # 2b. 获取当前传感器文件夹中的所有 Stem 集合
        sensor_stems = get_stems_from_folder(sensor_dir, extensions)
        
        # --- 双向检查 ---
        
        # 3. 完整性检查 (Completeness): Labels 集合 - Sensor 集合
        # 检查 GT 有的，传感器文件夹是否缺失
        missing_stems = gt_stems - sensor_stems
        if missing_stems:
            missing_count = len(missing_stems)
            results.append(f"[FAIL] {folder_name}: 缺少 {missing_count} 个必需文件 (e.g., {list(missing_stems)[:2]}...)")
            is_pass = False
        else:
            results.append(f"[PASS] {folder_name} (完整性): 找到所有 {N} 个文件。")

        # 4. 纯净性检查 (Purity/Junk): Sensor 集合 - Labels 集合
        # 检查传感器文件夹有的，GT 是否缺失 (即多余文件)
        extra_stems = sensor_stems - gt_stems
        if extra_stems:
            extra_count = len(extra_stems)
            results.append(f"[WARN] {folder_name}: 发现 {extra_count} 个多余文件 (e.g., {list(extra_stems)[:2]}...)")
            is_pass = False # 仍然标记为不完美
        else:
             results.append(f"[PASS] {folder_name} (纯净性): 无多余文件。")


    return results, is_pass


def main():
    parser = argparse.ArgumentParser(description="检查新生成的数据集场景完整性")
    parser.add_argument('root_path', type=str, 
                        help='包含 train/ 和 val/ 子目录的数据集根路径，例如 /home/lhn/Downloads/dataset_reshuffled')
    args = parser.parse_args()

    root_path = args.root_path
    all_scenes = []
    
    # 查找所有 train_scene_* 和 val_scene_* 文件夹
    for split in ['train', 'val']:
        split_path = os.path.join(root_path, split)
        if os.path.exists(split_path):
            scenes = glob(os.path.join(split_path, '*scene_*'))
            all_scenes.extend(scenes)

    if not all_scenes:
        print(f"[ERROR] 在 {root_path} 下未找到任何有效的 scene_* 文件夹。")
        return

    print(f"--- 🚀 开始检查 {len(all_scenes)} 个场景的一致性 ---")
    
    total_scenes = len(all_scenes)
    fail_count = 0

    for idx, scene_path in enumerate(all_scenes):
        scene_name = os.path.basename(scene_path)
        print(f"\n[{idx+1}/{total_scenes}] 检查 {scene_name}...")
        
        results, is_pass = check_scene_integrity(scene_path)
        
        if is_pass:
            print(f"✅ {scene_name}: **通过所有检查**。")
        else:
            print(f"❌ {scene_name}: **发现错误或警告**。")
            fail_count += 1
            for res in results:
                if '[FAIL]' in res or '[WARN]' in res:
                    print(f"  {res}")
        
    if fail_count == 0:
        print("🎉 **恭喜！所有场景数据完整且纯净。**")
    else:
        print(f"🚨 **警告：发现 {fail_count} 个场景存在错误或多余文件。** 请检查上方日志中的 [FAIL] 和 [WARN] 信息。")
    print("="*50)


if __name__ == '__main__':
    main()