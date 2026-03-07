数据库驱动的 SUMO 演示项目

运行方式
1. 安装 SUMO 并确保 sumo-gui 可用
2. 进入 Chapter02 目录
3. 运行 python 1.py

流程
- 从网上下载出租车数据到 data/taxi_sample.csv（仅取前 1200 行）
- 写入 sqlite 数据库 taxi_chapter02.db
- 读取数据库生成车辆并启动 SUMO GUI

输出文件
- taxi_chapter02.db
- data/taxi_sample.csv
