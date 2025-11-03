# 标准库
from os.path import dirname
import sys
sys.path.append(dirname(__file__))

# 个人库
from BasicTool.HedgeBt_SOLE import HedgeBt_SOLE
from BasicTool.Option import Autocallable

###
class HedgeBt_S(HedgeBt_SOLE):
    def __init__(
            self, 
            start_dt: str, 
            end_dt: str, 
            file_path: str, 
            udly: str, 
            hedge_ins: str, 
            optn: Autocallable
        ):

        '''
        创建单雪球回测类(高级类)
        '''
        
        super().__init__(
            start_dt, 
            end_dt, 
            file_path, 
            udly, 
            hedge_ins, 
            optn
        )