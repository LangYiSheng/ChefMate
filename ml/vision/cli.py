from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from vision.scripts.common import CONFIGS_DIR, find_latest_experiment_dir, find_latest_weight_file
from vision.scripts.export import run_export
from vision.scripts.infer import run_infer
from vision.scripts.prepare_foodseg103 import run_prepare
from vision.scripts.run_pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChefMate 图像模型训练 CLI")
    parser.add_argument("--interactive", action="store_true", help="进入交互式菜单")
    subparsers = parser.add_subparsers(dest="command")

    prepare_parser = subparsers.add_parser("prepare", help="准备 FoodSeg103 检测数据")
    prepare_parser.add_argument(
        "--mapping",
        type=Path,
        default=CONFIGS_DIR / "foodseg103_ingredient_map.example.yaml",
        help="类别映射文件",
    )
    prepare_parser.add_argument("--dataset-name", type=str, default="ingredient_detection_foodseg103")
    prepare_parser.add_argument("--max-samples-per-split", type=int, default=0)
    prepare_parser.add_argument("--clear-output", action="store_true")

    smoke_parser = subparsers.add_parser("smoke", help="快速跑一轮小规模训练检查")
    smoke_parser.add_argument("--device", type=str, default="0")
    smoke_parser.add_argument("--model-size", choices=["n", "s"], default="n")

    train_parser = subparsers.add_parser("train", help="正式训练默认配置")
    train_parser.add_argument("--device", type=str, default="0")
    train_parser.add_argument("--model-size", choices=["n", "s"], default="n")

    export_parser = subparsers.add_parser("export", help="导出最近一次实验模型")
    export_parser.add_argument("--format", type=str, default="onnx")
    export_parser.add_argument("--imgsz", type=int, default=640)

    infer_parser = subparsers.add_parser("infer", help="用最近一次实验模型做推理")
    infer_parser.add_argument("source", type=str, help="待推理图片或目录")
    infer_parser.add_argument("--imgsz", type=int, default=640)
    infer_parser.add_argument("--conf", type=float, default=0.25)
    infer_parser.add_argument("--name", type=str, default="predict")

    latest_parser = subparsers.add_parser("latest", help="查看最近一次实验结果位置")
    latest_parser.add_argument("--show-weight", action="store_true")

    return parser


def build_pipeline_args(*, model_size: str, device: str, smoke: bool) -> argparse.Namespace:
    imgsz = 512 if smoke else 640
    batch = 4 if smoke else 8
    workers = 2 if smoke else 4
    return argparse.Namespace(
        mapping=CONFIGS_DIR / "foodseg103_ingredient_map.example.yaml",
        dataset_name="ingredient_detection_foodseg103",
        model=f"yolo11{model_size}.pt",
        epochs=1 if smoke else 100,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        patience=30,
        conf=0.25,
        cache=False,
        export_format="onnx",
        max_samples_per_split=50 if smoke else 0,
        clear_output=smoke,
        experiment_name=f"{'smoke' if smoke else 'train'}_yolo11{model_size}",
    )


def prompt_text(label: str, default: str) -> str:
    value = input(f"{label} [{default}]: ").strip()
    return value or default


def prompt_menu_choice() -> str:
    print("\nChefMate Vision CLI")
    print("1. 准备数据")
    print("2. 快速检查训练链路")
    print("3. 正式训练")
    print("4. 导出最近一次训练模型")
    print("5. 使用最近一次训练模型做推理")
    print("6. 查看最近一次实验结果")
    print("0. 退出")
    return input("请输入选项编号: ").strip()


def run_prepare_command(args: argparse.Namespace) -> None:
    summary = run_prepare(
        argparse.Namespace(
            mapping=args.mapping,
            output_name=args.dataset_name,
            repo_id="EduardoPacheco/FoodSeg103",
            max_samples_per_split=args.max_samples_per_split,
            min_box_area_ratio=0.001,
            clear_output=args.clear_output,
        )
    )
    print(f"数据准备完成：{summary['output_root']}")
    print(f"数据集配置：{summary['dataset_yaml']}")


def run_smoke_command(args: argparse.Namespace) -> None:
    run_dir = run_pipeline(build_pipeline_args(model_size=args.model_size, device=args.device, smoke=True))
    print(f"快速检查完成：{run_dir}")
    print(f"报告位置：{(run_dir / 'report.md').as_posix()}")


def run_train_command(args: argparse.Namespace) -> None:
    run_dir = run_pipeline(build_pipeline_args(model_size=args.model_size, device=args.device, smoke=False))
    print(f"正式训练完成：{run_dir}")
    print(f"报告位置：{(run_dir / 'report.md').as_posix()}")


def run_export_command(args: argparse.Namespace) -> None:
    latest_weight = find_latest_weight_file()
    if latest_weight is None:
        raise SystemExit("未找到最近一次训练生成的 best.pt，请先执行 smoke 或 train。")
    result = run_export(argparse.Namespace(weights=latest_weight, format=args.format, imgsz=args.imgsz))
    print(result)


def run_infer_command(args: argparse.Namespace) -> None:
    latest_weight = find_latest_weight_file()
    if latest_weight is None:
        raise SystemExit("未找到最近一次训练生成的 best.pt，请先执行 smoke 或 train。")
    run_infer(
        argparse.Namespace(
            weights=latest_weight,
            source=args.source,
            imgsz=args.imgsz,
            conf=args.conf,
            project=find_latest_experiment_dir() or Path("vision/experiments"),
            name=args.name,
        )
    )
    print("推理完成。")


def run_latest_command(args: argparse.Namespace) -> None:
    latest_experiment = find_latest_experiment_dir()
    if latest_experiment is None:
        raise SystemExit("当前还没有实验输出。")
    print(f"latest_experiment={latest_experiment.as_posix()}")
    if args.show_weight:
        latest_weight = find_latest_weight_file()
        if latest_weight is not None:
            print(f"latest_weight={latest_weight.as_posix()}")


def run_interactive_menu() -> None:
    while True:
        choice = prompt_menu_choice()

        if choice == "0":
            print("已退出。")
            return

        if choice == "1":
            dataset_name = prompt_text("输出数据集目录名", "ingredient_detection_foodseg103")
            max_samples = int(prompt_text("每个 split 最多处理多少样本，0 表示全部", "0"))
            clear_output = prompt_text("是否清空旧输出（y/n）", "n").lower() == "y"
            run_prepare_command(
                argparse.Namespace(
                    mapping=CONFIGS_DIR / "foodseg103_ingredient_map.example.yaml",
                    dataset_name=dataset_name,
                    max_samples_per_split=max_samples,
                    clear_output=clear_output,
                )
            )
            continue

        if choice == "2":
            model_size = prompt_text("模型尺寸（n/s）", "n")
            device = prompt_text("训练设备", "0")
            print("快速检查默认使用更保守的参数：imgsz=512, batch=4, workers=2")
            run_smoke_command(argparse.Namespace(model_size=model_size, device=device))
            continue

        if choice == "3":
            model_size = prompt_text("模型尺寸（n/s）", "n")
            device = prompt_text("训练设备", "0")
            print("正式训练默认参数：imgsz=640, batch=8, workers=4")
            run_train_command(argparse.Namespace(model_size=model_size, device=device))
            continue

        if choice == "4":
            export_format = prompt_text("导出格式", "onnx")
            imgsz = int(prompt_text("导出图像尺寸", "640"))
            run_export_command(argparse.Namespace(format=export_format, imgsz=imgsz))
            continue

        if choice == "5":
            source = input("请输入待推理图片或目录路径: ").strip()
            if not source:
                print("路径不能为空。")
                continue
            imgsz = int(prompt_text("推理图像尺寸", "640"))
            conf = float(prompt_text("置信度阈值", "0.25"))
            name = prompt_text("结果目录名", "predict")
            run_infer_command(argparse.Namespace(source=source, imgsz=imgsz, conf=conf, name=name))
            continue

        if choice == "6":
            show_weight = prompt_text("是否同时显示权重路径（y/n）", "y").lower() == "y"
            run_latest_command(argparse.Namespace(show_weight=show_weight))
            continue

        print("输入无效，请重新选择。")


def main() -> None:
    # 启动时优先加载 ml/.env，避免每次手动设置 Hugging Face Token。
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

    if len(sys.argv) == 1:
        run_interactive_menu()
        return

    args = build_parser().parse_args()
    if args.interactive:
        run_interactive_menu()
        return

    if args.command == "prepare":
        run_prepare_command(args)
        return

    if args.command == "smoke":
        run_smoke_command(args)
        return

    if args.command == "train":
        run_train_command(args)
        return

    if args.command == "export":
        run_export_command(args)
        return

    if args.command == "infer":
        run_infer_command(args)
        return

    if args.command == "latest":
        run_latest_command(args)
        return

    run_interactive_menu()


if __name__ == "__main__":
    main()
