# 标准库
from os.path import dirname
import sys
sys.path.append(dirname(__file__))

# 第三方库
from numba import njit
import numpy as np
from scipy.stats import norm
from scipy.stats.qmc import Sobol

###
def get_Next_Power_Of_Two(
        num: int
    ) -> int:

    '''
    计算大于等于num的最小2的幂次\n
    如 1000 → 1024 = 2^10
    '''

    m = num.bit_length() - 1
    if (1 << m) < num:
        m += 1
    return 1 << m

###
def gen_Sobol_Normal_Shocks(
        num_simu: int, 
        matu: int, 
        seed: int = 0
    ) -> np.ndarray:

    '''
    利用Sobol序列数生成 (num_simu, matu) 维度的随机数矩阵\n
    通过行列坐标直接采用
    '''

    sampler = Sobol(d=matu, rng=np.random.default_rng(seed=seed))
    sample_uniform = sampler.random(n=get_Next_Power_Of_Two(num_simu))
    sample_normal = norm.ppf(sample_uniform)
    
    return sample_normal.astype(np.float32)

###
@njit  # 启用Numba即时编译，自动优化循环
def gen_KotsVec(kots_0: list) -> list:

    '''
    生成初始的每日的敲出日期列
    '''

    kots_vec = []
    n = len(kots_0)
    temp = kots_0.copy()
    kots_vec.append(temp.copy())
    
    current_start = 0
    for i in range(n):
        count = kots_0[i]
        for _ in range(count):
            temp[current_start] -= 1
            kots_vec.append(temp[current_start:].copy())
        current_start += 1
    
    return kots_vec

###
@njit(fastmath=True, cache=True)
def _gen_Simu_Path(
        S,
        num_simu,
        num_step, 
        random_shocks,
        drift, 
        vol, 
    ) -> np.ndarray:
    
    '''
    生成模拟路径的核心函数, 通过@njit加速生成
    '''

    cumu_shocks = np.empty((num_simu, num_step), dtype=np.float32)
    
    for i in range(num_simu):
        cumu_shocks[i, 0] = drift + vol * random_shocks[i, 0]
        for j in range(1, num_step):
            cumu_shocks[i, j] = cumu_shocks[i, j-1] + drift + vol * random_shocks[i, j]
    
    simu_path = np.empty((num_simu, num_step + 1), dtype=np.float32)
    
    simu_path[:, 0] = S
    
    for i in range(num_simu):
        for j in range(num_step):
            simu_path[i, j + 1] = S * np.exp(cumu_shocks[i, j])
    
    return simu_path

###
@njit(fastmath=True, cache=True)
def _autocallable(
    simu_path, 
    S_0,
    u_prices, 
    l_price, 
    K_price, 
    T, 
    T_p, 
    matu,
    rf, 
    Coupon, 
    Rebate, 
    knock_in, 
    cumu_kots
    ) -> float:

    '''
    蒙特卡洛法定价的核心函数, 通过@njit加速运算
    '''

    num_paths, num_days = simu_path.shape
    cumu_kots_len = len(cumu_kots)
    
    payoff = np.zeros(num_paths)
    
    for p in range(num_paths):
        path = simu_path[p]
        knock_out = False
        first_kot_idx = -1
        
        for i in range(cumu_kots_len):
            t = cumu_kots[i]
            if t >= num_days:
                break
            if path[t] >= u_prices[i]:
                knock_out = True
                first_kot_idx = i
                break
        
        if knock_out: # 敲出
            t_kot = cumu_kots[first_kot_idx]
            payoff[p] = Coupon * (T_p + t_kot) / 252. * np.exp(-rf * t_kot / 252.)
        
        else:
            if not knock_in:
                for price in path:
                    if price <= l_price:
                        knock_in = True
                        break
            
            if knock_in: # 敲入
                final_price = path[-1]
                payoff[p] = np.minimum((final_price - K_price) / S_0 * np.exp(-rf * T / 252.), 0.)
            else: # 未敲出也未敲入
                payoff[p] = Rebate * matu / 252. * np.exp(-rf * T / 252.)
    
    return payoff.mean() + 1

###       
class Autocallable():
    def __init__(
            self, 
            u_ratios: np.ndarray, 
            l_ratio: float, 
            k_ratio: float, 
            Coupon: float, 
            Rebate: float,  
            matu: int,
            rf: float,
            kots_0: list, 
            notional: int, 
        ) -> None:

        '''
        创建单雪球类
        '''

        assert sum(kots_0) >= matu, '敲出日天数总和应大于等于期权久期'
        assert len(kots_0) == len(u_ratios), '敲出日天数应等于敲出价格比率'
        self.num_simu = 1024
        self.matu= matu
        self.u_ratios = u_ratios
        self.l_ratio = l_ratio
        self.k_ratio = k_ratio
        self.Coupon = Coupon
        self.Rebate = Rebate
        self.matu = matu 
        self.rf = rf 
        self.kots_0 = kots_0
        self.notional = notional

        self.random_shocks = gen_Sobol_Normal_Shocks(
                num_simu=self.num_simu, 
                matu=matu, 
                seed=0
            )
        
        self._kots_vec = gen_KotsVec(kots_0)
    
    def set_Init_Params(
            self,
            S_0: float
        ) -> None: 

        '''
        设置单雪球初始固定参数
        '''

        self.S_0 = S_0 
        self.u_prices = self.u_ratios * S_0 
        self.l_price = self.l_ratio * S_0 
        self.k_price = self.k_ratio * S_0
        self.kots_vec = self._kots_vec.copy()
        
    def set_Var_Params(
            self, 
            S: float,
            mu: float,
            sigma: float, 
            T: int,
            knock_in: bool
        ) -> None:

        '''
        设置单雪球变动参数
        '''

        self.S = S
        self.mu = mu
        self.sigma = sigma
        self.cumu_kots = np.array(self.kots_vec.pop(0)).cumsum()
        self.u_prices = self.u_prices[-len(self.cumu_kots):] # 确保敲出价格和敲出日个数对齐
        self.T = T 
        self.knock_in = knock_in
    
    def gen_Simu_Path(
            self, 
        ) -> np.ndarray:

        '''
        生成模拟路径
        '''

        S = np.array(self.S, dtype=np.float32)

        dt = 1 / 252
        drift = np.array((self.mu - 0.5 * self.sigma**2) * dt, dtype=np.float32)
        vol = np.array(self.sigma * np.sqrt(dt), dtype=np.float32)
        
        return _gen_Simu_Path(
            S, 
            self.num_simu, 
            self.T, 
            self.random_shocks, 
            drift, 
            vol
        )

    def _Autocallable(self, simu_path: np.ndarray) -> float:

        '''
        类核心函数: 蒙特卡洛法定价
        '''
        
        return _autocallable(
            simu_path, 
            self.S_0,
            self.u_prices, 
            self.l_price,
            self.k_price, 
            self.T, 
            self.matu - self.T, 
            self.matu,
            self.rf, 
            self.Coupon, 
            self.Rebate, 
            self.knock_in, 
            self.cumu_kots
        )
 
    def get_Valuation(
            self,
        ) -> float:

        '''
        获取该雪球现价
        '''

        simu_path = self.gen_Simu_Path()
        price = self._Autocallable(simu_path)

        return price
        
    def delta(
            self,
            precision: float = 0.01,
        ) -> float:

        '''
        获取该雪球delta
        '''

        ds = precision * self.S
        temp_S = self.S

        self.S = temp_S + ds
        price_1 = self.get_Valuation()

        self.S = temp_S - ds
        price_2 = self.get_Valuation()

        delta = (price_1 - price_2) / 2 / ds

        self.S = temp_S

        return delta