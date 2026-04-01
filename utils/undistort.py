import cv2
import numpy as np
import os
import glob
import re
from pathlib import Path
from itertools import chain
import json
import argparse

def update_camera_config(camera_config_path, param_files, input_dirs):
    # 初始化空的配置数组
    camera_config = []

    # 加载外部参数
    with open('utils/base_to_sensor.json', 'r') as f:
        ext_params = json.load(f)

    # 遍历每个相机配置
    for i, (param_file, input_dir) in enumerate(zip(param_files, input_dirs)):
        # 【修改点1】：统一所有相机的分辨率，移除旧的判断逻辑
        width = 1920
        height = 1536
        
        internal_params = read_camera_parameters(param_file)
        fx = internal_params.get("FX")
        fy = internal_params.get("FY")
        cx = internal_params.get("CX")
        cy = internal_params.get("CY")
        # 获取外参
        external_matrix = ext_params.get(input_dir.split('/')[-1])
        # 增加容错：如果找不到外参，防止报错（可选）
        if external_matrix is None:
            print(f"警告: 未找到 {input_dir} 的外参配置")
            flat_external = [] 
        else:
            flat_external = sum(external_matrix, [])  # 展平为一维列表

        # 构建单个相机配置
        camera_entry = {
            "camera_internal": {
                "fx": fx,
                "fy": fy,
                "cx": cx,
                "cy": cy
            },
            "width": width,
            "height": height,
            "camera_external": flat_external,
            "rowMajor": True
        }

        # 添加到配置列表
        camera_config.append(camera_entry)

    # 写入新文件
    with open(camera_config_path, 'w') as f:
        json.dump(camera_config, f, indent=4)

    print(f"✅ 已成功创建并写入 {camera_config_path}")

def generate_camera_config_dir(camera_config_path):
    with open(camera_config_path, "r") as f:
        data = json.load(f)

    # 创建 camera_config 文件夹
    os.makedirs(f"{scene_dir}/camera_config", exist_ok=True)

    # 获取 LIDAR_CONCAT 下的所有 .pcd 文件名（去掉后缀）
    # 确保这个目录存在，否则可能会报错
    lidar_dir = f"{scene_dir}/lidar_point_cloud_0"
    if os.path.exists(lidar_dir):
        pcd_files = [f for f in os.listdir(lidar_dir) if f.endswith(".pcd")]
        base_names = [os.path.splitext(f)[0] for f in pcd_files]

        # 为每个文件名生成对应的 .json 文件，并写入相同的内容
        for name in base_names:
            json_path = os.path.join(scene_dir, "camera_config", f"{name}.json")
            with open(json_path, "w") as json_file:
                json.dump(data, json_file, indent=4)
        print("✅ 所有 JSON 文件已生成并保存到 camera_config 文件夹中。")
    else:
        print(f"⚠️ 未找到雷达目录 {lidar_dir}，跳过生成单帧 config 文件。")

def read_camera_parameters(param_file):
    """从参数文件中读取相机内参和畸变系数"""
    params = {}
    with open(param_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if value != '/' and value != 'null' and value != '':
                try:
                    params[key] = float(value)
                except ValueError:
                    params[key] = value
    return params

def undistort_fisheye_images(param_file, input_dir, output_dir):
    """对鱼眼相机拍摄的图像进行去畸变处理"""
    params = read_camera_parameters(param_file)
    fx, fy = params.get('FX'), params.get('FY')
    cx, cy = params.get('CX'), params.get('CY')
    k1 = params.get('K1', 0.0)
    k2 = params.get('K2', 0.0)
    k3 = params.get('K3', 0.0)
    k4 = params.get('K4', 0.0)
    
    required_params = ['FX', 'FY', 'CX', 'CY']
    if not all(param in params for param in required_params):
        missing = [param for param in required_params if param not in params]
        raise ValueError(f"缺少必要的相机参数: {', '.join(missing)}")
    
    camera_matrix = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
    dist_coeffs = np.array([k1, k2, k3, k4])
    
    os.makedirs(output_dir, exist_ok=True)
    image_files = glob.glob(os.path.join(input_dir, '*.png')) + glob.glob(os.path.join(input_dir, '*.jpg'))
    
    for image_file in image_files:
        img = cv2.imread(image_file)
        if img is None:
            print(f"无法读取图像: {image_file}")
            continue
        
        h, w = img.shape[:2]
        new_camera_matrix = camera_matrix.copy()
        
        map1, map2 = cv2.fisheye.initUndistortRectifyMap(
            camera_matrix, dist_coeffs, np.eye(3), new_camera_matrix, (w, h), cv2.CV_16SC2
        )
        undistorted_img = cv2.remap(img, map1, map2, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
        
        filename = os.path.basename(image_file)
        output_file = os.path.join(output_dir, filename)
        cv2.imwrite(output_file, undistorted_img)
        print(f"已处理: {image_file}")

# 【修改点2】：虽然这个函数在主流程没被调用，但建议更新尺寸以防混淆
def crop_image(image, cx, cy, crop_percent=1):
    """从光学中心裁剪图像"""
    width = 1920  # 更新为新尺寸
    height = 1536 # 更新为新尺寸
    
    # 注意：如果现在的图不需要裁剪，这个函数可能需要逻辑调整
    # 下面保留原有逻辑，假设 crop_width/height 是目标尺寸
    crop_width = 1920
    crop_height = 1536
    
    left = int((width - crop_width) / 2)
    right = left + crop_width
    top = int((height - crop_height) / 2)
    bottom = top + crop_height
    
    cropped = image[top:bottom, left:right]
    return cropped

def process_fisheye_camera(param_file, input_dir, output_dir):
    try:
        print(f'开始处理鱼眼 camera: {input_dir} 中的图片')
        undistort_fisheye_images(param_file, input_dir, output_dir)
        print(f"所有图像已处理完成并保存到 {output_dir} 目录")
    except Exception as e:
        print(f"处理出错: {e}")

def undistort_pinhole_image(image_path, params, input_dir):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    
    # 构建相机矩阵
    camera_matrix = np.array([
        [params['FX'], 0, params['CX']],
        [0, params['FY'], params['CY']],
        [0, 0, 1]
    ])
    
    # 构建畸变系数 (注意：如果你的新相机参数里没有P1/P2，这里需要处理一下get的默认值)
    dist_coeffs = np.array([
        params.get('K1', 0), params.get('K2', 0), 
        params.get('P1', 0), params.get('P2', 0),
        params.get('K3', 0), params.get('K4', 0), 
        params.get('K5', 0), params.get('K6', 0)
    ])
    
    # 去畸变
    undistorted_img = cv2.undistort(img, camera_matrix, dist_coeffs)
    return undistorted_img, camera_matrix

def process_pinhole_image(param_file, input_dir, output_dir):
    try:
        print(f'开始处理针孔 camera: {input_dir} 中的图片')
        params = read_camera_parameters(param_file)
        image_files = glob.glob(os.path.join(input_dir, '*.jpg')) + glob.glob(os.path.join(input_dir, '*.png'))
        
        for image_path in image_files:
            try:
                # 这里不需要 crop 了，因为输入输出尺寸一致
                undistorted_img, _ = undistort_pinhole_image(image_path, params, input_dir)
                filename = os.path.basename(image_path)
                output_path = os.path.join(output_dir, f'{filename}')
                cv2.imwrite(output_path, undistorted_img)
                print(f"已处理: {image_path}")
            except Exception as e:
                print(f"处理图像 {image_path} 时出错: {str(e)}")
        print(f"所有图像已处理完成并保存到 {output_dir} 目录")
    except Exception as e:
        print(f"处理图像时出错: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="图像去畸变以及保存内参外参配置文件")
    parser.add_argument('--path', type=str, required=True, help='场景路径，例如 scene_1')
    args = parser.parse_args()
    scene_dir = args.path

    # 参数文件列表
    param_files = [
        "utils/Parameters/pinhole-frontup.txt",
        "utils/Parameters/pinhole-frontmid.txt",
        "utils/Parameters/fisheye-frontdown.txt", 
        "utils/Parameters/fisheye-leftup.txt", 
        "utils/Parameters/pinhole-leftdown.txt", 
        "utils/Parameters/fisheye-rightup.txt", 
        "utils/Parameters/pinhole-rightdown.txt"
    ]
    
    # 输入文件夹列表
    input_dirs = [
        f"{scene_dir}/CAM_FRONTUP",
        f"{scene_dir}/CAM_FRONTMID",
        f"{scene_dir}/CAM_FRONTDOWN",
        f"{scene_dir}/CAM_LEFTUP", 
        f"{scene_dir}/CAM_LEFTDOWN", 
        f"{scene_dir}/CAM_RIGHTUP", 
        f"{scene_dir}/CAM_RIGHTDOWN"
    ]
    
    # 输出文件夹列表
    output_dirs = [
        f"{scene_dir}/camera_image_0", 
        f"{scene_dir}/camera_image_1", 
        f"{scene_dir}/camera_image_2",
        f"{scene_dir}/camera_image_3", 
        f"{scene_dir}/camera_image_4", 
        f"{scene_dir}/camera_image_5",
        f"{scene_dir}/camera_image_6",
    ]

    # 【修改核心】：定义哪些相机是针孔相机
    pinhole_camera_names = [
        "CAM_FRONTUP",
        "CAM_FRONTMID", 
        "CAM_LEFTDOWN", 
        "CAM_RIGHTDOWN"
    ]
    
    for param_file, input_dir, output_dir in zip(param_files, input_dirs, output_dirs):
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 判断当前处理的文件夹是否在针孔列表中
        # 使用 any() 函数检查路径中是否包含针孔相机的名字
        is_pinhole = any(name in input_dir for name in pinhole_camera_names)

        if is_pinhole:
            # 处理针孔相机 (FRONTUP,FRONTMID, LEFTDOWN, RIGHTDOWN)
            process_pinhole_image(param_file, input_dir, output_dir)
        else:
            # 处理鱼眼相机 (FRONTDOWN, LEFTUP,RIGHTUP)
            process_fisheye_camera(param_file, input_dir, output_dir)

    # 更新配置文件
    camera_config_path = "utils/camera_config.json"
    update_camera_config(camera_config_path, param_files, input_dirs)
    generate_camera_config_dir(camera_config_path)
    
    print("\n处理完所有图片")