import os
import json

# ================== 配置 ==================
BASE_DIR = "/home/liujie/code/ADML3D/data/custom/scene_9"
SENSOR_DIRS = [
    "camera_config",
    "camera_image_0", 
    "camera_image_1", 
    "camera_image_2", 
    "camera_image_3", 
    "camera_image_4", 
    "camera_image_5", 
    "camera_image_6",
    "lidar_point_cloud_0",
    # "CAM_FRONTDOWN",
    "result"
]
# 选择数据最完整的传感器作为主传感器
MAIN_SENSOR = "lidar_point_cloud_0"  # 可以根据实际情况调整

EXCEPTION_FILE = os.path.join(BASE_DIR, "exception.txt")
# ========================================

def extract_seconds_from_files(folder):
    """提取某个文件夹下所有文件的时间戳（支持多种格式）"""
    if not os.path.exists(folder):
        print(f"警告：文件夹不存在 {folder}")
        return set()
    
    seconds = set()
    valid_extensions = ('.pcd', '.png', '.json')
    
    for f in os.listdir(folder):
        # 检查文件扩展名
        if not f.lower().endswith(valid_extensions):
            continue
        
        try:
            # 获取不带扩展名的文件名
            basename = os.path.splitext(f)[0]
            
            # 处理可能的命名格式，如 "1766730857" 或 "1766730857_xxx"
            if '_' in basename:
                # 如果有下划线，取第一部分
                ts_part = basename.split('_')[0]
            else:
                # 如果没有下划线，直接使用整个文件名
                ts_part = basename
            
            # 时间戳应该是纯数字
            if ts_part.isdigit():
                # 检查时间戳长度
                ts_len = len(ts_part)
                if ts_len == 10:  # 10位时间戳（秒级）
                    seconds.add(ts_part)
                elif ts_len > 10:  # 长于10位，可能是纳秒级，取前10位
                    seconds.add(ts_part[:10])
                elif ts_len < 10:  # 短于10位，可能是截断的，记录警告
                    print(f"警告：{folder}/{f} 时间戳过短: {ts_part}")
                else:
                    # 正好10位的情况已在第一个if处理
                    pass
            else:
                print(f"警告：{folder}/{f} 时间戳包含非数字: {ts_part}")
                
        except Exception as e:
            print(f"解析文件名失败 {f}: {e}")
    
    return seconds

def find_exception_seconds():
    """找出异常秒"""
    all_seconds = {}
    
    # 先检查所有传感器的数据
    print("检查各传感器文件数量：")
    for sensor in SENSOR_DIRS:
        folder = os.path.join(BASE_DIR, sensor)
        seconds = extract_seconds_from_files(folder)
        all_seconds[sensor] = seconds
        print(f"  {sensor}: {len(seconds)} 个时间戳")
    
    # 找出数据最丰富的传感器作为主传感器（如果MAIN_SENSOR没数据）
    if MAIN_SENSOR not in all_seconds or not all_seconds[MAIN_SENSOR]:
        print(f"主传感器 {MAIN_SENSOR} 没有数据，自动选择数据最丰富的传感器...")
        max_sensor = max(all_seconds.items(), key=lambda x: len(x[1]))[0]
        ref_seconds = all_seconds[max_sensor]
        print(f"自动选择 {max_sensor} 作为主传感器（{len(ref_seconds)} 个时间戳）")
    else:
        ref_seconds = all_seconds[MAIN_SENSOR]
        print(f"使用主传感器 {MAIN_SENSOR}（{len(ref_seconds)} 个时间戳）")
    
    if not ref_seconds:
        print("错误：没有找到有效的时间戳数据！")
        return set()
    
    exception_seconds = set()
    
    # 1. 检查其他传感器是否缺少主传感器的时间戳
    print("\n检查缺失的时间戳：")
    for sensor, secs in all_seconds.items():
        if sensor == MAIN_SENSOR:
            continue
        missing = ref_seconds - secs
        if missing:
            print(f"{sensor} 缺少 {len(missing)} 个时间戳：{list(sorted(missing))[:5]}...")
            exception_seconds.update(missing)
        else:
            print(f"{sensor} ✓ 时间戳完整")
    
    # 2. 检查其他传感器是否有主传感器没有的时间戳
    print("\n检查多余的时间戳：")
    for sensor, secs in all_seconds.items():
        if sensor == MAIN_SENSOR:
            continue
        extra = secs - ref_seconds
        if extra:
            print(f"{sensor} 有 {len(extra)} 个多余时间戳：{list(sorted(extra))[:5]}...")
            exception_seconds.update(extra)
        else:
            print(f"{sensor} ✓ 无多余时间戳")
    
    return exception_seconds

def save_exceptions(exception_seconds):
    """保存异常秒到txt"""
    with open(EXCEPTION_FILE, "w") as f:
        f.write(f"异常时间戳总数: {len(exception_seconds)}\n")
        f.write("=" * 50 + "\n")
        for sec in sorted(exception_seconds):
            f.write(f"{sec}\n")
    print(f"记录异常秒到 {EXCEPTION_FILE}, 共 {len(exception_seconds)} 条")

def remove_exceptions(exception_seconds):
    """删除所有文件夹下异常秒对应的文件"""
    if not exception_seconds:
        print("没有异常文件需要删除")
        return
    
    total_deleted = 0
    valid_extensions = ('.pcd', '.png', '.json')
    
    for sensor in SENSOR_DIRS:
        folder = os.path.join(BASE_DIR, sensor)
        if not os.path.exists(folder):
            continue
        
        deleted_count = 0
        for f in os.listdir(folder):
            # 检查文件扩展名
            if not f.lower().endswith(valid_extensions):
                continue
            
            try:
                # 获取不带扩展名的文件名
                basename = os.path.splitext(f)[0]
                
                # 提取时间戳部分
                if '_' in basename:
                    ts_part = basename.split('_')[0]
                else:
                    ts_part = basename
                
                # 检查是否应该删除
                if ts_part.isdigit() and len(ts_part) >= 10:
                    sec = ts_part[:10]  # 取前10位作为秒级时间戳
                    if sec in exception_seconds:
                        filepath = os.path.join(folder, f)
                        os.remove(filepath)
                        # print(f"删除: {folder}/{f}")
                        total_deleted += 1
                        deleted_count += 1
                        
            except Exception as e:
                print(f"处理文件失败 {folder}/{f}: {e}")
        
        if deleted_count > 0:
            print(f"  {sensor}: 删除了 {deleted_count} 个文件")
    
    print(f"总共删除了 {total_deleted} 个文件")

def find_common_time_range():
    """找到所有传感器共有的时间戳"""
    all_seconds = {}
    
    print("\n查找所有传感器的时间戳交集...")
    for sensor in SENSOR_DIRS:
        folder = os.path.join(BASE_DIR, sensor)
        seconds = extract_seconds_from_files(folder)
        all_seconds[sensor] = seconds
    
    # 找出所有传感器都有的时间戳
    if all_seconds:
        common_timestamps = set.intersection(*[set(secs) for secs in all_seconds.values() if secs])
        print(f"所有传感器共有的时间戳数量: {len(common_timestamps)}")
        
        if common_timestamps:
            print(f"时间戳范围: {min(common_timestamps)} 到 {max(common_timestamps)}")
            return common_timestamps
    
    return set()

if __name__ == "__main__":
    print("=" * 60)
    print("多传感器时间同步检查工具")
    print("支持文件类型: .pcd, .png, .json")
    print("=" * 60)
    
    # 先找出共有的时间戳
    common_timestamps = find_common_time_range()
    
    # 再检查异常
    exceptions = find_exception_seconds()
    
    if exceptions:
        print(f"\n发现 {len(exceptions)} 个异常时间戳")
        if common_timestamps:
            print(f"所有传感器共有的时间戳: {len(common_timestamps)} 个")
            
        # 显示部分异常时间戳
        if exceptions:
            sample = list(sorted(exceptions))[:10]
            print(f"异常时间戳示例: {sample}")
        
        # 显示统计信息
        print("\n按传感器统计异常时间戳分布:")
        for sensor in SENSOR_DIRS:
            if sensor in ["camera_config", "result"]:
                continue  # 跳过配置文件
            folder = os.path.join(BASE_DIR, sensor)
            if os.path.exists(folder):
                files = [f for f in os.listdir(folder) if f.lower().endswith(('.pcd', '.png'))]
                print(f"  {sensor}: {len(files)} 个文件")
        
        confirm = input("\n是否确认删除异常文件？(y/n): ")
        if confirm.lower() == 'y':
            save_exceptions(exceptions)
            remove_exceptions(exceptions)
            print("\n数据时间同步完成，异常文件已删除。")
            
            # 删除后重新统计
            print("\n删除后各传感器文件数量:")
            for sensor in SENSOR_DIRS:
                folder = os.path.join(BASE_DIR, sensor)
                if os.path.exists(folder):
                    files = [f for f in os.listdir(folder) if f.lower().endswith(('.pcd', '.png'))]
                    if files:  # 只显示有文件的传感器
                        print(f"  {sensor}: {len(files)} 个文件")
        else:
            print("已取消删除操作")
    else:
        print("\n✓ 完美！所有传感器的时间戳完全同步，无需删除文件。")