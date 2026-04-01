import os

# ================== 配置 ==================
BASE_DIR = "/home/liujie/code/ADML3D/data/custom/scene_6"
# SENSOR_DIRS = ["BACK_AIRY", "CAM_BACK", "CAM_FRONT", "CAM_LEFT", "CAM_RIGHT", "CAM_TOP", "FRONT_AIRY", "TOP_H32"]
# MAIN_SENSOR = "TOP_H32"
SENSOR_DIRS = ["CAM_FRONTUP","CAM_FRONTMID", "CAM_LEFTDOWN", "CAM_RIGHTDOWN", "CAM_FRONTDOWN", "CAM_LEFTUP", "CAM_RIGHTUP", "LIDAR_RIGHT","LIDAR_LEFT","LIDAR_MID"]
MAIN_SENSOR = "LIDAR_MID"
EXCEPTION_FILE = os.path.join(BASE_DIR, "exception.txt")
# ========================================

def extract_seconds_from_files(folder):
    """提取某个文件夹下所有文件的秒级时间戳"""
    seconds = set()
    for f in os.listdir(folder):
        if not f.endswith(".pcd") and not f.endswith(".png"):
            continue
        ts = os.path.splitext(f)[0].split("_")[0]  # 例如 1758682311000124693
        seconds.add(ts[:10])  # 前10位是秒级时间戳
    return seconds

def find_exception_seconds():
    """找出异常秒"""
    all_seconds = {}
    for sensor in SENSOR_DIRS:
        folder = os.path.join(BASE_DIR, sensor)
        all_seconds[sensor] = extract_seconds_from_files(folder)

    ref_seconds = all_seconds[MAIN_SENSOR]  # TOP_H32 秒集合
    exception_seconds = set()

    # TOP_H32 有，但其他传感器缺少
    for sec in ref_seconds:
        for sensor, secs in all_seconds.items():
            if sensor == MAIN_SENSOR:
                continue
            if sec not in secs:
                exception_seconds.add(sec)

    # 其他传感器有，但 TOP_H32 没有
    for sensor, secs in all_seconds.items():
        if sensor == MAIN_SENSOR:
            continue
        for sec in secs:
            if sec not in ref_seconds:
                exception_seconds.add(sec)

    return exception_seconds

def save_exceptions(exception_seconds):
    """保存异常秒到txt"""
    with open(EXCEPTION_FILE, "w") as f:
        for sec in sorted(exception_seconds):
            f.write(f"{sec}\n")
    print(f"记录异常秒到 {EXCEPTION_FILE}, 共 {len(exception_seconds)} 条")

def remove_exceptions(exception_seconds):
    """删除所有文件夹下异常秒对应的文件"""
    for sensor in SENSOR_DIRS:
        folder = os.path.join(BASE_DIR, sensor)
        for f in os.listdir(folder):
            if not (f.endswith(".pcd") or f.endswith(".png")):
                continue
            ts = os.path.splitext(f)[0].split("_")[0]
            sec = ts[:10]
            if sec in exception_seconds:
                try:
                    os.remove(os.path.join(folder, f))
                    print(f"删除: {folder}/{f}")
                except Exception as e:
                    print(f"删除失败 {folder}/{f}: {e}")

if __name__ == "__main__":
    exceptions = find_exception_seconds()
    save_exceptions(exceptions)
    remove_exceptions(exceptions)
    print("数据时间同步完成，异常文件已删除。")
