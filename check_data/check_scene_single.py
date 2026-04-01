import os
import argparse
from glob import glob

# ================= 配置参数 =================
SENSOR_CONFIG = {
    "labels": [".txt"],  # 标签是地面真值
    "camera_config": [".json", ".txt", ".yaml"],
    "lidar_point_cloud_0": [".pcd", ".bin"],
    "camera_image_0": [".png", ".jpg"],
    "camera_image_1": [".png", ".jpg"],
    "camera_image_2": [".png", ".jpg"],
    "camera_image_3": [".png", ".jpg"],
    "camera_image_4": [".png", ".jpg"],
}
# ===========================================

def get_stems_from_folder(folder_path, extensions):
    stems = set()
    for ext in extensions:
        files = glob(os.path.join(folder_path, f"*{ext}"))
        for f in files:
            stems.add(os.path.splitext(os.path.basename(f))[0])
    return stems


def check_scene_integrity(scene_path):
    results = []
    is_pass = True
    
    # 1. Labels 检查
    label_dir = os.path.join(scene_path, "labels")
    if not os.path.exists(label_dir):
        return [f"[FAIL] 缺少核心目录: {label_dir}"], False

    gt_stems = get_stems_from_folder(label_dir, SENSOR_CONFIG['labels'])
    N = len(gt_stems)
    
    if N == 0:
        return [f"[FAIL] {scene_path}: labels 目录为空，无法检查"], False

    results.append(f"[INFO] 找到 {N} 个核心帧 (基于 labels)。")

    # 2. 遍历所有 sensor 文件夹
    for folder_name, extensions in SENSOR_CONFIG.items():
        sensor_dir = os.path.join(scene_path, folder_name)

        if not os.path.exists(sensor_dir):
            results.append(f"[FAIL] 缺少传感器目录: {folder_name}")
            is_pass = False
            continue

        sensor_stems = get_stems_from_folder(sensor_dir, extensions)

        # 完整性 (labels - sensor)
        missing_stems = gt_stems - sensor_stems
        if missing_stems:
            results.append(
                f"[FAIL] {folder_name}: 缺少 {len(missing_stems)} 个文件 (例如 {list(missing_stems)[:2]})"
            )
            is_pass = False
        else:
            results.append(f"[PASS] {folder_name} (完整性): 找到所有文件。")

        # 纯净性 (sensor - labels)
        extra_stems = sensor_stems - gt_stems
        if extra_stems:
            results.append(
                f"[WARN] {folder_name}: 发现 {len(extra_stems)} 个多余文件 (例如 {list(extra_stems)[:2]})"
            )
            is_pass = False
        else:
            results.append(f"[PASS] {folder_name} (纯净性): 无多余文件。")

    return results, is_pass


def main():
    parser = argparse.ArgumentParser(description="检查单个场景的数据完整性")
    parser.add_argument('scene_path', type=str, 
                        help='单个 scene 目录路径，例如 /home/liujie/code/xbzl_data-master/scene_9')
    args = parser.parse_args()

    scene_path = args.scene_path

    if not os.path.exists(scene_path):
        print(f"[ERROR] 路径不存在: {scene_path}")
        return

    print(f"🚀 开始检查场景: {scene_path}")

    results, is_pass = check_scene_integrity(scene_path)

    if is_pass:
        print(f"✅ {scene_path}: **通过所有检查**。")
    else:
        print(f"❌ {scene_path}: **存在错误或多余文件**。")
        for res in results:
            if '[FAIL]' in res or '[WARN]' in res:
                print(f"  {res}")

    print("=" * 50)


if __name__ == '__main__':
    main()
