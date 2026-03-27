# ChefMate ML Workspace

该目录用于承载项目中的机器学习与模型训练工作区。

当前重点为：

- `vision/`：食材图像识别模型训练、验证、导出与推理

建议在 PyCharm 中直接打开 `ml/` 作为单独工程目录，后续如果继续加入推荐实验或其他智能方法，也可以保持统一结构。

训练依赖入口在：

- `ml/pyproject.toml`

因此建议在 `ml/` 目录下执行：

```bash
cd ml
uv sync
```

如果你希望使用 NVIDIA GPU 训练，可在同步依赖后手动安装 CUDA 版 PyTorch：

```bash
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

安装完成后，可用下面这条命令检查是否识别到 CUDA：

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.device_count())"
```
