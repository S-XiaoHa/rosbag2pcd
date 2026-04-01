import os
import json
import argparse

def convert_annotations(scene_dir):
    """
    从 scene_train1-xxxxxx/result 中提取 3D 标注，
    保存到 scene_train1-xxxxxx/labels 下
    """
    # 输入目录（直接在 scene_dir 下）
    input_dir = os.path.join(scene_dir, 'result')
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"未找到 result 目录: {input_dir}")

    # 输出目录：scene_xxx/labels
    output_dir = os.path.join(scene_dir, 'labels')
    os.makedirs(output_dir, exist_ok=True)

    # 遍历所有 JSON 文件
    for filename in os.listdir(input_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(input_dir, filename)
        label_file_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '.txt')

        with open(file_path, 'r') as f:
            data = json.load(f)

        with open(label_file_path, 'w') as label_file:
            print(f"正在处理: {file_path}")

            # 遍历 data 下的每一组 source（可能是 Ground Truth 和 模型结果）
            for annotation in data:
                for obj in annotation.get('objects', []):
                    contour = obj.get('contour', {})
                    if not contour or not isinstance(contour, dict):
                       print(f"⚠️ 跳过无效 contour 对象: {obj.get('id', 'unknown')}")
                       continue

                    center3D = contour.get('center3D', {})
                    if not center3D:
                         print(f"⚠️ 对象 {obj.get('id', 'unknown')} 缺少 center3D")
                         continue
                    size3D = contour.get('size3D', {})
                    rotation3D = contour.get('rotation3D', {})
                    class_name = obj.get('className', 'unknown')

                    # 跳过缺失关键字段的对象
                    if not center3D or not size3D:
                        continue

                    # 提取并四舍五入
                    x = round(center3D.get('x', 0), 3)
                    y = round(center3D.get('y', 0), 3)
                    z = round(center3D.get('z', 0), 3)
                    dx = round(size3D.get('x', 0), 3)
                    dy = round(size3D.get('y', 0), 3)
                    dz = round(size3D.get('z', 0), 3)
                    yaw = round(rotation3D.get('z', 0), 3)

                    label_file.write(f"{x} {y} {z} {dx} {dy} {dz} {yaw} {class_name}\n")

    print(f"\n✅ 提取完成！结果保存在: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="提取 Xtreme1 标注信息")
    parser.add_argument('--path', type=str, required=True, help='场景路径，例如 scene_train1-20251022021524')
    args = parser.parse_args()

    convert_annotations(args.path)
