import os
import json
import argparse
import uuid

def parse_txt_line(line):
    """解析单行 TXT 数据"""
    parts = line.strip().split()
    if len(parts) < 8:
        return None
    
    try:
        # TXT 格式: x y z dx dy dz yaw class_name
        x = float(parts[0])
        y = float(parts[1])
        z = float(parts[2])
        dx = float(parts[3])
        dy = float(parts[4])
        dz = float(parts[5])
        yaw = float(parts[6])
        class_name = parts[7]
        
        return {
            "x": x, "y": y, "z": z,
            "dx": dx, "dy": dy, "dz": dz,
            "yaw": yaw,
            "className": class_name
        }
    except ValueError:
        return None

def convert_txt_to_json(txt_path, json_path):
    objects = []
    
    with open(txt_path, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        data = parse_txt_line(line)
        if data is None:
            continue
            
        # 构建 Xtreme1 对象结构
        obj = {
            "id": str(uuid.uuid4()).upper(), # 生成随机唯一ID
            "type": "3D_BOX",
            "classId": None, # 导入时通常会自动匹配类名
            "className": data['className'],
            "trackId": str(uuid.uuid4()),    # 生成随机 TrackID
            "trackName": "",
            "classValues": [],
            "contour": {
                "pointN": 0, # 可选
                "points": [],
                "size3D": {
                    "x": data['dx'],
                    "y": data['dy'],
                    "z": data['dz']
                },
                "center3D": {
                    "x": data['x'],
                    "y": data['y'],
                    "z": data['z']
                },
                "viewIndex": 0,
                "rotation3D": {
                    "x": 0,
                    "y": 0,
                    "z": data['yaw'] # 这里只还原 Yaw，Pitch/Roll 在 TXT 里丢失了则默认为 0
                }
            },
            "modelConfidence": None,
            "modelClass": ""
        }
        objects.append(obj)

    # 构建最终的 JSON 结构 (模拟 Xtreme1 导出/结果格式)
    # 注意：Xtreme1 导入结果时，通常是一个列表，包含一个由 "objects" 组成的字典
    final_json = [
        {
            "version": "Xtreme1 v0.9.1", # 伪装版本号
            "sourceName": "prediction",  # 或 "ground truth"
            "objects": objects
        }
    ]

    with open(json_path, 'w') as f:
        json.dump(final_json, f, indent=4)
    
    print(f"Converted: {txt_path} -> {json_path}")

def main():
    parser = argparse.ArgumentParser(description="将 TXT 标签转回 Xtreme1 JSON 格式")
    parser.add_argument('--input_dir', type=str, required=True, help='包含 TXT 文件的目录')
    parser.add_argument('--output_dir', type=str, required=True, help='输出 JSON 的目录')
    args = parser.parse_args()
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        
    files = [f for f in os.listdir(args.input_dir) if f.endswith('.txt')]
    print(f"Found {len(files)} txt files.")
    
    for filename in files:
        txt_path = os.path.join(args.input_dir, filename)
        # 对应 JSON 文件名通常与 PCD 文件名一致 (即去掉 .txt 后缀换成 .json)
        json_filename = os.path.splitext(filename)[0] + '.json'
        json_path = os.path.join(args.output_dir, json_filename)
        
        convert_txt_to_json(txt_path, json_path)

    print("Done.")

if __name__ == '__main__':
    main()