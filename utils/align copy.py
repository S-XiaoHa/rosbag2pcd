import os

# ================== 配置 ==================
BASE_DIR = "/home/liujie/code/ADML3D/data/custom/scene_check"

# 根据你的 ls 输出配置文件夹
SENSOR_DIRS = [
    "camera_image_0", 
    "camera_image_1", 
    "camera_image_2", 
    "camera_image_3", 
    "camera_image_4", 
    "lidar_point_cloud_0",
    "result",
    "labels",
    "labels_check",
    "camera_config"  
]

# 建议：以雷达数据为基准（源头），或者以 result 为基准（结果）
# MAIN_SENSOR = "result" 
MAIN_SENSOR = "result" 

EXCEPTION_FILE = os.path.join(BASE_DIR, "exception.txt")
# ========================================

def extract_seconds_from_files(folder):
    """提取某个文件夹下所有文件的秒级时间戳"""
    seconds = set()
    if not os.path.exists(folder):
        print(f"[警告] 文件夹不存在: {folder}")
        return seconds

    for f in os.listdir(folder):
        # 增加支持 .txt (result) 和 .json (config)
        valid_ext = (".pcd", ".png", ".jpg", ".txt", ".json", ".bin")
        if not f.lower().endswith(valid_ext):
            continue
        
        # 逻辑：文件名通常是 176xxxxx.pcd 或 176xxxxx_cam0.png
        # splitext 去掉后缀 -> split("_") 去掉尾部标识 -> 取前10位作为秒级对齐
        filename_no_ext = os.path.splitext(f)[0]
        ts_part = filename_no_ext.split("_")[0] 
        
        # 简单校验一下是不是数字，防止读到非时间戳文件
        if ts_part.isdigit():
            # 这里取前10位作为秒级时间戳 (Unix时间戳通常是10位秒或13/16/19位毫秒纳秒)
            # 如果你的文件名已经是秒级（如 1760428492.txt），[:10] 刚好取全部
            sec = ts_part[:10]
            seconds.add(sec)
        else:
            print(f"[跳过] 非时间戳命名文件: {folder}/{f}")
            
    return seconds

def find_exception_seconds():
    """找出异常秒"""
    all_seconds = {}
    print(f"正在扫描文件夹 (基准: {MAIN_SENSOR})...")
    
    for sensor in SENSOR_DIRS:
        folder = os.path.join(BASE_DIR, sensor)
        all_seconds[sensor] = extract_seconds_from_files(folder)
        print(f"  - {sensor}: {len(all_seconds[sensor])} 个文件")

    if MAIN_SENSOR not in all_seconds or not all_seconds[MAIN_SENSOR]:
        print(f"错误：基准传感器 {MAIN_SENSOR} 为空或不存在！")
        return set()

    ref_seconds = all_seconds[MAIN_SENSOR]  # 基准秒集合
    exception_seconds = set()

    # 1. 检查其他传感器是否缺少基准里的时间
    for sec in ref_seconds:
        for sensor, secs in all_seconds.items():
            if sensor == MAIN_SENSOR:
                continue
            if sec not in secs:
                exception_seconds.add(sec)

    # 2. 检查其他传感器是否有多余的时间（基准里没有的）
    for sensor, secs in all_seconds.items():
        if sensor == MAIN_SENSOR:
            continue
        for sec in secs:
            if sec not in ref_seconds:
                exception_seconds.add(sec)

    return exception_seconds

def save_exceptions(exception_seconds):
    """保存异常秒到txt"""
    if not exception_seconds:
        print("完美！没有发现异常时间戳。")
        return

    with open(EXCEPTION_FILE, "w") as f:
        for sec in sorted(exception_seconds):
            f.write(f"{sec}\n")
    print(f"记录异常秒到 {EXCEPTION_FILE}, 共 {len(exception_seconds)} 条")

def remove_exceptions(exception_seconds):
    """删除所有文件夹下异常秒对应的文件"""
    if not exception_seconds:
        return

    print("开始清理异常文件...")
    count = 0
    for sensor in SENSOR_DIRS:
        folder = os.path.join(BASE_DIR, sensor)
        if not os.path.exists(folder): continue

        for f in os.listdir(folder):
            valid_ext = (".pcd", ".png", ".jpg", ".txt", ".json", ".bin")
            if not f.lower().endswith(valid_ext):
                continue
            
            ts = os.path.splitext(f)[0].split("_")[0]
            if len(ts) >= 10:
                sec = ts[:10]
                if sec in exception_seconds:
                    try:
                        file_path = os.path.join(folder, f)
                        os.remove(file_path)
                        # print(f"删除: {file_path}") # 文件太多时可以注释掉这行
                        count += 1
                    except Exception as e:
                        print(f"删除失败 {folder}/{f}: {e}")
    print(f"清理完成，共删除 {count} 个文件。")

if __name__ == "__main__":
    # 二次确认，防止误删
    print(f"即将对目录 {BASE_DIR} 进行同步检查。")
    print(f"基准文件夹: {MAIN_SENSOR}")
    
    exceptions = find_exception_seconds()
    
    if exceptions:
        user_input = input(f"发现 {len(exceptions)} 组异常时间戳，是否确人删除这些不同步的文件？(y/n): ")
        if user_input.lower() == 'y':
            save_exceptions(exceptions)
            remove_exceptions(exceptions)
            print("数据时间同步完成。")
        else:
            print("已取消删除操作。")
    else:
        print("所有文件夹数据已同步，无需操作。")