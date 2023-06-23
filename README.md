更新：
2023年6月23日
添加并验证了circles_spatial2D，circles_spatial3D两个模型的python and c++ 版本。

## 目的
测试FlameGPU2框架三种不同情况下的速度。

## 结果
1. boids_spatial3D_c文件夹下C++结合cuda编写的代码，10000轮用时11.31秒。
2. boids_spatial3D_p.py是用纯python写的代码，10000轮用时36.74秒。
3. boids_spatial3D_c+p文件夹是python结合cuda编写的代码，10000轮用时11.44秒。拆分了单文件为多文件

## 结论
为了提升编写速度，同时提升运行速度，最好采用 python + cuda 混合编程。