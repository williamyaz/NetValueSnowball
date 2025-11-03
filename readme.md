# ***"NetValueSnowball"回测引擎框架***

# 基于

# Sobol序列数的蒙特卡洛法

# 用于

# <连续型|滚动型|单个>的净值化雪球回测



1. ##### 结构

**以下为该框架的结构:**

**\*\*\*\***

***NetValueSnowball***

\- Main.py

\- Main_Bt.py

\- Engine_Bt.py

\- Config.py

\- ***Data***

\- ***Result***

\- ***Tool***

   - HedgeBt_C.py

   - HedgeBt_R.py

   - HedgeBt_S.py

   - ***BasicTool***

       - HedgeBt_SOLE.py

       - Option.py

\*\*\*\*



2. ##### 依赖的第三方库

matplotlib

numba

numpy

pandas

scipy

seaborn



3. ##### 框架逻辑\&运行步骤

界面操作: 运行Main (后续为调用关系) - Main_Bt - Config - Engine_Bt - Tool (HedgeBt_C, HedgeBt_R, HedgeBt_S) - BasicTool (HedgeBt_SOLE - Option)

手动操作: 调整Config - 运行Main_Bt (后续为调用关系) - Engine_Bt - Tool (HedgeBt_C, HedgeBt_R, HedgeBt_S) - BasicTool (HedgeBt_SOLE - Option)



引擎名称:

'c': 连续雪球

'r': 滚动雪球

's': 单雪球



4. ##### 代码加速原理

HedgeBt_C.py: 基于多进程加速运行

Option.py: 提取核心矩阵计算步骤, 利用numba的@njit(fastmath=True, cache=True)加速计算; 初始化时固定随机数矩阵以减少不必要的矩阵生成时间; 强制矩阵计算的浮点数类型为np.float32以加速计算; 根据变量赋值频率分层为不同方法, 以最佳性能完成目标

