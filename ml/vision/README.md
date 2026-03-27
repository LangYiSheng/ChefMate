# ChefMate Vision Training

## 1. 目标

该目录用于训练项目中的食材图像识别模型。

当前目标与课程报告保持一致：

- 识别用户摆放在台面上的食材种类
- 作为“自主训练的智能方法”重点展示模块
- 当前不把冰箱复杂遮挡场景和重量估计作为首期目标

推荐方法路线：

- 检测框架：Ultralytics YOLO
- 数据来源：FoodSeg103 + 自补充台面食材图片
- 训练目标：输出食材类别与检测框

## 2. 目录结构

```text
vision/
  configs/          # 数据集配置、类别模板
  datasets/         # 数据目录说明
  experiments/      # 训练输出
  scripts/          # 训练、验证、导出、推理、数据准备脚本
  weights/          # 导出的权重文件
```

## 3. 推荐开发流程

1. 安装依赖
2. 通过 `datasets.load_dataset()` 拉取 FoodSeg103
3. 将分割标注转换为项目需要的检测标注
4. 生成 YOLO 数据集配置
5. 训练 YOLO 模型
6. 验证、导出并生成量化报告
7. 将最终权重接入后端推理服务

## 4. 数据目录约定

推荐将数据整理成如下结构：

```text
datasets/
  raw/
    foodseg103/
    custom_tabletop/
  processed/
    ingredient_detection/
      images/
        train/
        val/
        test/
      labels/
        train/
        val/
        test/
```

## 5. 快速开始

安装依赖：

```bash
cd ml
uv sync
```

如果你希望使用 NVIDIA GPU 训练，可在依赖同步后安装 CUDA 版 PyTorch：

```bash
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

安装完成后建议先检查一下 GPU 是否可见：

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.device_count())"
```

启动交互式菜单：

```bash
cd ml
uv run python -m vision.cli
```

启动后会先显示菜单，再让你输入编号，例如：

```text
1. 准备数据
2. 快速检查训练链路
3. 正式训练
4. 导出最近一次训练模型
5. 使用最近一次训练模型做推理
6. 查看最近一次实验结果
0. 退出
```

如果你还是想直接用命令，也仍然支持：

```bash
cd ml
uv run python -m vision.cli prepare
```

快速检查训练链路：

```bash
cd ml
uv run python -m vision.cli smoke
```

正式训练：

```bash
cd ml
uv run python -m vision.cli train
```

导出最近一次训练模型：

```bash
cd ml
uv run python -m vision.cli export
```

使用最近一次训练模型做推理：

```bash
cd ml
uv run python -m vision.cli infer 你的图片路径.jpg
```

## 6. 关于 FoodSeg103

FoodSeg103 原本是分割数据集，而当前项目更适合检测任务，因此这里提供了“通过 `datasets.load_dataset()` 读取数据集，再将分割掩码转换为 YOLO 检测框”的脚本。

如果你们后续决定只保留一部分高频食材类别，也可以先做类别映射，再进入训练。

## 7. 输出结果

一键流水线跑完后，实验目录下会自动生成：

- `weights/best.pt`
- `metrics_summary.json`
- `report.md`

其中 `report.md` 可以直接作为后续实现报告中的量化结果草稿。
