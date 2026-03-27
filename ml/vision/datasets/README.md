# Datasets

该目录用于存放训练数据。

推荐结构：

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

说明：

- `raw/`：原始下载数据与采集数据
- `processed/`：转换为训练框架可直接读取的格式
- 当前 YOLO 检测训练使用 `images/` 与 `labels/` 配对结构

