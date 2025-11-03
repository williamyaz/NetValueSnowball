# 个人库
from Config import *
from Engine_Bt import Engine_Bt

###
if __name__ == '__main__':
    Engine_Bt(
        start_date, 
        end_date, 
        file_path, 
        udly, 
        hedge_ins, 
        u_ratios, 
        l_ratio, 
        k_ratio, 
        Coupon, 
        Rebate, 
        matu, 
        rf, 
        kots_0, 
        notional, 
        engine_name
    ).Go_()