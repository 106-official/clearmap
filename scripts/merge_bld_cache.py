# -*- coding: utf-8 -*-
"""合并北京建筑分块缓存为单一 beijing_buildings.json，供 build_map.py 直接使用。

遍历 15x13 网格，对每个 (x,y) 位置：
  1. 优先加载基础块缓存 bld_beijing_X_Y.json
  2. 若不存在，递归加载子块 bld_beijing_X_Y_*.json
  3. 都不存在则跳过（该区域无建筑数据）
"""
import json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE, "build_cache")
CITY = "beijing"
BTILE_X, BTILE_Y = 15, 13  # 与 build_map.py 的 btiles 一致


def load_elements(filename):
    path = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def merge_tile(base_key, depth=0):
    """递归加载一个块及其子块。返回 elements 列表。"""
    # 尝试加载基础块
    elems = load_elements(base_key + ".json")
    if elems is not None:
        return elems

    if depth >= 3:  # MAX_SPLIT_DEPTH
        return []

    # 尝试加载 4 个子块
    total = []
    for qy in (0, 1):
        for qx in (0, 1):
            sub_key = "%s_%d_%d" % (base_key, qx, qy)
            sub_elems = merge_tile(sub_key, depth + 1)
            total.extend(sub_elems)
    return total


if __name__ == "__main__":
    all_elems = []
    found = 0
    missing = 0

    for iy in range(BTILE_Y):
        for ix in range(BTILE_X):
            key = "bld_%s_%d_%d" % (CITY, ix, iy)
            elems = merge_tile(key)
            if elems:
                all_elems.extend(elems)
                found += 1
            else:
                # 检查是否有任何子块缓存
                has_sub = any(
                    os.path.exists(os.path.join(CACHE_DIR, "%s_%d_%d.json" % (key, qx, qy)))
                    for qy in (0, 1) for qx in (0, 1)
                )
                if not has_sub:
                    missing += 1

    print("已合并 %d 个位置，%d 个位置无数据，共 %d 条建筑要素" % (found, missing, len(all_elems)))

    out_path = os.path.join(CACHE_DIR, "%s_buildings.json" % CITY)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_elems, f, ensure_ascii=False)
    print("已写入合并缓存: %s (%.1f KB)" % (out_path, os.path.getsize(out_path) / 1024))
