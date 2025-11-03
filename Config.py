# 标准库
from os.path import join, dirname

# 第三方库
import numpy as np

###
file_path = join(dirname(__file__), "Data\\test_data.xlsx")
start_date = '20160101'
end_date = '20250101'
udly = "000905.SH"
hedge_ins = "IC"
matu = 252
l_ratio = 0.8
k_ratio = 1.
Coupon = 0.3
Rebate = Coupon 
rf = 0.01
temp = [63] + [21] * ((matu - 63) // 21)
kots_0 = temp if sum(temp) == matu else temp + [matu - sum(temp)]
u_ratios = np.around(np.linspace(1.0, 0.8, len(kots_0)), decimals=2).tolist()
notional = 1_000_000
engine_name = 'r'