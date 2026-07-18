#!/usr/bin/env python3
"""
GLTF/GLB → FBX Converter
=========================
使用 Blender 作为后端引擎,完整支持:
  - 静态网格 (Static Mesh)
  - PBR 材质与纹理
  - 骨骼动画 (Skeletal Animation)
  - 形变目标 (Morph Targets / Shape Keys)
  - GLB (Binary) 和 GLTF (JSON) 两种格式

用法:
  blender --background --python gltf2fbx.py -- --input model.glb --output model.fbx
  blender --background --python gltf2fbx.py -- --input model.gltf --output model.fbx
  blender --background --python gltf2fbx.py -- --input model.glb --output model.fbx --scale 100

或通过包装脚本:
  python gltf2fbx.py --input model.glb --output model.fbx
  (自动查找系统中的 Blender)

依赖:
  - Blender 3.6+ (https://www.blender.org/download/)
"""

import argparse
import os
import sys
import subprocess
import shutil
import json
from pathlib import Path


# ─── Blender 内执行的转换逻辑 ───────────────────────────────────────────
def convert_inside_blender():
    """在 Blender Python 环境内执行。清理场景 → 导入 GLTF → 导出 FBX。"""
    import bpy

    # 从命令行参数中提取 --input/--output/--scale (在 -- 之后)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        print("错误: 未找到 -- 分隔符。用法: blender --background --python gltf2fbx.py -- --input x.glb --output x.fbx")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="GLTF to FBX (Blender backend)")
    parser.add_argument("--input", required=True, help="输入 GLTF/GLB 文件路径")
    parser.add_argument("--output", required=True, help="输出 FBX 文件路径")
    parser.add_argument("--scale", type=float, default=1.0, help="缩放因子 (默认 1.0)")
    parser.add_argument("--bake-animations", action="store_true", default=True,
                        help="烘焙动画 (默认启用)")
    parser.add_argument("--no-bake", dest="bake_animations", action="store_false",
                        help="不烘焙动画")
    parser.add_argument("--apply-modifiers", action="store_true", default=True,
                        help="应用修改器 (默认启用)")
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    print(f"▶ 输入: {input_path}")
    print(f"▶ 输出: {output_path}")
    print(f"▶ 缩放: {args.scale}")

    # 1. 重置场景
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. 导入 GLTF/GLB
    print("▶ 导入 GLTF/GLB...")
    try:
        if input_path.suffix.lower() == ".glb":
            bpy.ops.import_scene.gltf(filepath=str(input_path))
        else:
            bpy.ops.import_scene.gltf(filepath=str(input_path))
    except Exception as e:
        print(f"错误: 导入失败: {e}")
        sys.exit(1)

    # 3. 对场景中的所有对象应用缩放和变换
    if args.scale != 1.0:
        print(f"▶ 应用缩放因子 {args.scale}...")
        for obj in bpy.data.objects:
            obj.scale = (obj.scale[0] * args.scale,
                         obj.scale[1] * args.scale,
                         obj.scale[2] * args.scale)

    # 4. 应用变换 (Apply Transforms)
    print("▶ 应用变换...")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # 5. 烘焙动画 (可选)
    if args.bake_animations:
        print("▶ 检查动画数据...")
        has_animation = False
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action:
                has_animation = True
                break
        if has_animation:
            print("▶ 烘焙动画...")
            # 设置帧范围
            scene = bpy.context.scene
            frame_start = int(scene.frame_start)
            frame_end = int(scene.frame_end)
            bpy.ops.nla.bake(
                frame_start=frame_start,
                frame_end=frame_end,
                only_selected=False,
                visual_keying=True,
                clear_constraints=False,
                bake_types={'OBJECT'}
            )

    # 6. 导出 FBX
    print("▶ 导出 FBX...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        bpy.ops.export_scene.fbx(
            filepath=str(output_path),
            use_selection=False,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            bake_space_transform=False,
            object_types={'MESH', 'ARMATURE', 'EMPTY'},
            use_mesh_modifiers=args.apply_modifiers,
            use_mesh_modifiers_render=True,
            mesh_smooth_type='FACE',
            use_armature_deform_only=True,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_custom_props=True,
            axis_forward='-Z',
            axis_up='Y',
            path_mode='COPY',
            embed_textures=False,  # FBX 嵌入纹理会增大文件,改为复制到旁边
        )
    except Exception as e:
        print(f"错误: FBX 导出失败: {e}")
        sys.exit(1)

    print(f"✓ 转换完成: {output_path}")
    print(f"  文件大小: {output_path.stat().st_size / 1024:.1f} KB")

    # 7. 收集并显示统计信息
    mesh_count = len([o for o in bpy.data.objects if o.type == 'MESH'])
    armature_count = len([o for o in bpy.data.objects if o.type == 'ARMATURE'])
    print(f"  网格: {mesh_count}, 骨架: {armature_count}")


# ─── Blender 内执行的减面逻辑 ───────────────────────────────────────────
def decimate_inside_blender():
    """在 Blender Python 环境内执行。导入 FBX → 应用 Decimate 修改器 → 导出 FBX。"""
    import bpy

    # 从命令行参数中提取 (在 -- 之后)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        print("错误: 未找到 -- 分隔符。用法: blender --background --python gltf2fbx.py -- --mode decimate --input x.fbx --output y.fbx")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="FBX Decimate (Blender backend)")
    parser.add_argument("--mode", default="decimate", help="工作模式 (自动处理)")
    parser.add_argument("--input", required=True, help="输入 FBX 文件路径")
    parser.add_argument("--output", required=True, help="输出 FBX 文件路径")
    parser.add_argument("--ratio", type=float, default=0.5,
                        help="目标面数比例 (0.01-1.0, 默认 0.5 = 保留 50%)")
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    ratio = max(0.01, min(1.0, args.ratio))

    print(f"▶ 输入: {input_path}")
    print(f"▶ 输出: {output_path}")
    print(f"▶ 减面比例: {ratio*100:.0f}%")

    # 1. 重置场景
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. 导入 FBX
    print("▶ 导入 FBX...")
    try:
        bpy.ops.import_scene.fbx(filepath=str(input_path))
    except Exception as e:
        print(f"错误: FBX 导入失败: {e}")
        sys.exit(1)

    # 3. 统计原始面数
    total_faces_before = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            total_faces_before += len(obj.data.polygons)
    print(f"▶ 原始面数: {total_faces_before}")

    # 4. 对每个网格应用 Decimate 修改器
    print("▶ 应用减面...")
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
            mod.decimate_type = 'COLLAPSE'
            mod.ratio = ratio
            bpy.ops.object.modifier_apply(modifier="Decimate")

    # 5. 统计减面后面数
    total_faces_after = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            total_faces_after += len(obj.data.polygons)
    print(f"▶ 减面后面数: {total_faces_after}")
    if total_faces_before > 0:
        print(f"▶ 实际保留: {total_faces_after / total_faces_before * 100:.1f}%")

    # 6. 导出 FBX
    print("▶ 导出 FBX...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        bpy.ops.export_scene.fbx(
            filepath=str(output_path),
            use_selection=False,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE',
            bake_space_transform=False,
            object_types={'MESH', 'ARMATURE', 'EMPTY'},
            use_mesh_modifiers=True,
            use_mesh_modifiers_render=True,
            mesh_smooth_type='FACE',
            use_armature_deform_only=True,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_custom_props=True,
            axis_forward='-Z',
            axis_up='Y',
            path_mode='COPY',
            embed_textures=False,
        )
    except Exception as e:
        print(f"错误: FBX 导出失败: {e}")
        sys.exit(1)

    print(f"✓ 减面完成: {output_path}")
    print(f"  文件大小: {output_path.stat().st_size / 1024:.1f} KB")

    mesh_count = len([o for o in bpy.data.objects if o.type == 'MESH'])
    armature_count = len([o for o in bpy.data.objects if o.type == 'ARMATURE'])
    print(f"  网格: {mesh_count}, 骨架: {armature_count}")


# ─── 包装 CLI: 自动查找 Blender ─────────────────────────────────────────
def find_blender() -> str | None:
    """在系统中查找 Blender 可执行文件。"""
    if sys.platform == "win32":
        candidates = [
            # 常见安装路径
            r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
            # Steam 版本
            r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe",
        ]
        # 非标准路径 (自定义目录名、zip 解压版)
        import glob
        for pattern in [
            r"C:\Program Files\blender-*\blender.exe",
            r"D:\Program Files\blender-*\blender.exe",
            r"C:\Program Files\Blender\blender.exe",
            r"D:\Program Files\Blender\blender.exe",
        ]:
            candidates.extend(glob.glob(pattern))
        # 也搜索 PATH
        blender_path = shutil.which("blender")
        if blender_path:
            candidates.insert(0, blender_path)

    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender"),
        ]
        blender_path = shutil.which("blender")
        if blender_path:
            candidates.insert(0, blender_path)
    else:  # Linux
        candidates = [
            "/usr/bin/blender",
            "/usr/local/bin/blender",
            "/snap/bin/blender",
            os.path.expanduser("~/blender/blender"),
        ]
        blender_path = shutil.which("blender")
        if blender_path:
            candidates.insert(0, blender_path)

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def main():
    """CLI 入口: 解析参数,查找 Blender,调用转换。"""
    parser = argparse.ArgumentParser(
        description="GLTF/GLB → FBX 转换器 (基于 Blender)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --input model.glb --output model.fbx
  %(prog)s --input scene.gltf --output scene.fbx --scale 100
  %(prog)s --input model.glb --output model.fbx --blender "C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
  %(prog)s --mode decimate --input model.fbx --output model_low.fbx --ratio 0.5

如果不指定 --blender,脚本会自动搜索系统中的 Blender 安装。
        """,
    )
    parser.add_argument("--input", "-i", required=True,
                        help="输入 GLTF/GLB 文件路径")
    parser.add_argument("--output", "-o", required=True,
                        help="输出 FBX 文件路径")
    parser.add_argument("--blender", "-b",
                        help="Blender 可执行文件路径 (可选,自动检测)")
    parser.add_argument("--scale", "-s", type=float, default=1.0,
                        help="缩放因子 (默认 1.0, 例如 --scale 100 用于厘米→米)")
    parser.add_argument("--no-bake", action="store_true",
                        help="不烘焙动画")
    parser.add_argument("--no-modifiers", action="store_true",
                        help="不应用修改器")
    parser.add_argument("--mode", choices=["convert", "decimate"], default="convert",
                        help="工作模式: convert (GLTF→FBX, 默认) 或 decimate (FBX减面)")
    parser.add_argument("--ratio", type=float, default=0.5,
                        help="减面比例 0.01-1.0 (仅 decimate 模式, 默认 0.5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅打印将要执行的命令,不实际运行")

    args = parser.parse_args()

    # 验证输入文件
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    suffix = input_path.suffix.lower()
    if args.mode == "convert" and suffix not in (".gltf", ".glb"):
        print(f"警告: 输入文件后缀为 '{suffix}', 预期为 .gltf 或 .glb")
    elif args.mode == "decimate" and suffix not in (".fbx",):
        print(f"警告: 输入文件后缀为 '{suffix}', 预期为 .fbx")

    output_path = Path(args.output).resolve()

    # 查找 Blender
    blender_exe = args.blender or find_blender()
    if not blender_exe:
        print("错误: 未找到 Blender。请通过以下方式之一解决:")
        print("  1. 安装 Blender: https://www.blender.org/download/")
        print("  2. 通过 --blender 参数指定路径")
        print("  3. 将 Blender 添加到系统 PATH")
        sys.exit(1)

    if not os.path.isfile(blender_exe):
        print(f"错误: Blender 路径无效: {blender_exe}")
        sys.exit(1)

    print(f"▶ Blender: {blender_exe}")

    # 构建命令行
    script_path = Path(__file__).resolve()

    cmd = [
        blender_exe,
        "--background",
        "--python", str(script_path),
        "--",
        "--input", str(input_path),
        "--output", str(output_path),
    ]

    if args.mode == "decimate":
        cmd.extend(["--mode", "decimate", "--ratio", str(args.ratio)])
    else:
        cmd.extend(["--scale", str(args.scale)])
        if args.no_bake:
            cmd.append("--no-bake")
        if args.no_modifiers:
            cmd.append("--no-modifiers")

    if args.dry_run:
        print("▶ 命令 (dry-run):")
        print("  " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        return

    # 执行转换
    print("▶ 启动 Blender 进行转换...")
    print(f"  {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(f"✗ 转换失败 (退出码: {result.returncode})")
        sys.exit(result.returncode)

    # 验证输出
    if output_path.exists():
        print(f"✓ 成功! FBX 已生成: {output_path}")
        print(f"  文件大小: {output_path.stat().st_size / 1024:.1f} KB")
    else:
        print(f"✗ 转换似乎失败,输出文件未生成: {output_path}")
        sys.exit(1)


if __name__ == "__main__":
    # 判断是否在 Blender 内部运行
    try:
        import bpy  # noqa: F401
        IN_BLENDER = True
    except ImportError:
        IN_BLENDER = False

    if IN_BLENDER:
        # 根据 --mode 参数决定执行哪个功能
        argv = sys.argv
        post = argv[argv.index("--") + 1:] if "--" in argv else []
        mode = "convert"
        if "--mode" in post:
            idx = post.index("--mode")
            if idx + 1 < len(post):
                mode = post[idx + 1]
        if mode == "decimate":
            decimate_inside_blender()
        else:
            convert_inside_blender()
    else:
        main()
