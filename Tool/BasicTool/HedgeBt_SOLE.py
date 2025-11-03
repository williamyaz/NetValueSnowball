# 标准库
from datetime import timedelta
from os.path import abspath, dirname
import sys
sys.path.append(dirname(__file__))

# 第三方库
import numpy as np
import pandas as pd
from tqdm import tqdm

# 个人库
from Option import Autocallable

###
class HedgeBt_SOLE:
    def __init__(
            self, 
            start_date: str, 
            end_date: str, 
            file_path: str,
            udly: str, 
            hedge_ins: str, 
            optn: Autocallable, 
        ) -> None:

        '''
        创建单雪球回测类
        '''

        self.start_date = pd.Timestamp(start_date)      # 开始日期
        self.end_date = pd.Timestamp(end_date)          # 结束日期
        self.file_path = abspath(file_path)             # 数据文件位置
        self.udly = udly                                # 标的资产名称
        self.hedge_ins = hedge_ins                      # 对冲工具名称
        self.optn = optn                                # 期权对象
        assert ((self.end_date - self.start_date).days/365) > (optn.matu/252), "起始日期到结束日期长度应大于等于期权久期"
    
        # 待赋值属性
        self.udly_data = pd.DataFrame()         # 标的资产数据
        self.hedge_ins_data = pd.DataFrame()    # 对冲工具数据
        self.mkt_data = pd.DataFrame()          # 市场数据
        self.optn_data = pd.DataFrame()         # 期权数据
        self.hedge_data = pd.DataFrame()        # 对冲盈亏
        self.stats_data = pd.DataFrame()
        self.indicators = pd.Series()           # 统计指标
        
    def get_Udly_Data(
            self, 
        ) -> pd.DataFrame:

        '''
        加载并处理标的资产数据
        '''

        # 加载数据
        data = pd.read_excel(self.file_path, sheet_name = self.udly)
        assert {'Date', 'close'}.issubset(data.columns), "列名必须包含'Date'和'close'"

        # 处理Date格式
        data['Date'] = pd.to_datetime(data['Date'])
        data.sort_values(by='Date', inplace=True)
        data.set_index("Date", drop = True, inplace=True)

        # 为计算波动率，向前扩展数据
        data = data.loc[(self.start_date - timedelta(days=365)): self.end_date]
        
        # 计算收益率和波动率
        temp_data = data[data['close'] != 0].copy()
        temp_data['ret'] = temp_data['close'] / temp_data['close'].shift(1) - 1
        temp_data['sigma_20d'] = temp_data['ret'].rolling(window=63).std()*np.sqrt(252) # 计算(63d)波动率
        temp_data['sigma'] = temp_data['sigma_20d'].rolling(window=21).mean() # 21日(63d)平均波动率

        # 合并波动率数据
        data.loc[temp_data.index, 'sigma'] = temp_data['sigma']
        udly_data = data.loc[self.start_date: self.end_date, ['close','sigma']] 
        udly_data.fillna(0, inplace=True)
        self.udly_data = udly_data
        
        return udly_data
        
    def get_Hedge_Data(
            self, 
        ) -> pd.DataFrame:

        '''
        加载并处理对冲工具数据
        '''

        # 加载数据
        data = pd.read_excel(self.file_path, sheet_name = self.hedge_ins)
        assert {'Date', 'rmq', 'f1_close', 'f2_close', 'expiry_date'}.issubset(data.columns), "列名必须包含'Date', 'rmq', 'f1_close', 'f2_close'和'expiry_date'"
        
        # 处理Date格式
        data['Date'] = pd.to_datetime(data['Date'])
        data.sort_values(by='Date', inplace=True)
        data.set_index("Date", drop = True, inplace=True)

        # 均匀化rmq
        data['rmq'] = data['rmq'].rolling(window=21).mean()

        # 根据范围提取数据
        hedge_ins_data = data[self.start_date: self.end_date].copy()
        hedge_ins_data.fillna(0, inplace=True)
        self.hedge_ins_data = hedge_ins_data

        return self.hedge_ins_data
        
    def get_Mkt_Data(
            self
        ) -> pd.DataFrame:

        '''
        整合市场数据
        '''

        # 合并标的资产和对冲工具数据
        data = self.udly_data.copy()
        data[['rmq','f1_close','f2_close','expiry_date']] = self.hedge_ins_data.loc[data.index][['rmq','f1_close','f2_close','expiry_date']]
        
        # 处理到期日格式
        data['expiry_date'] = pd.to_datetime(data['expiry_date'])
        
        # 处理缺失值
        data.replace(0, np.nan, inplace=True)
        data.ffill(inplace=True)
        
        # 整理数据格式
        data['Date'] = pd.to_datetime(data.index)
        data.reset_index(drop=True, inplace=True)     
        mkt_data = data[['Date','close','sigma','rmq','f1_close','f2_close','expiry_date']]
        self.mkt_data = mkt_data

        return mkt_data

    def get_Optn_Data(
            self,
            precision: float = 0.01
        ) -> pd.DataFrame:

        '''
        计算单雪球的期权价格和delta
        '''

        # 单雪球的初始参数
        optn = self.optn
        S_0: float = self.mkt_data.loc[0, 'close']      # 初始标的价格 # type: ignore
        optn.set_Init_Params(S_0)
        
        # 准备期权数据
        optn_data = self.mkt_data.copy().iloc[:optn.matu+1]
        optn_data['S_0'] = S_0
        optn_data['K'] = optn.k_price
        optn_data['Up_Barrier_Price'] = optn.u_prices[0]
        optn_data['Down_Barrier_Price'] = optn.l_price

        # 归并敲出观察日向量并排序列
        optn_data['kots'] = self.optn._kots_vec[:len(optn_data)]
        optn_data = optn_data[
            [
                'Date', 
                'S_0', 
                'Up_Barrier_Price', 
                'K', 
                'Down_Barrier_Price', 
                'close', 
                'sigma', 
                'kots', 
                'rmq', 
                'f1_close', 
                'f2_close', 
                'expiry_date'
            ]
        ]
        
        # 计算期权价格和Delta
        optn_data['optn_price'] = 0.
        optn_data['delta'] = 0.
        knock_in = False
        
        dl = len(optn_data)
        pbar = tqdm(total=dl, desc='optn处理进度: ', ncols=95, file=sys.stdout)

        for (i, row) in enumerate(optn_data.itertuples()):
            # 获取当前参数
            S = getattr(row, 'close', 0.) 
            sigma = getattr(row, 'sigma', 0.) 
            kots = getattr(row, 'kots', [])
            rmq = getattr(row, 'rmq', 0.)
            
            # 计算剩余期限
            T = optn.matu - i

            # 检查是否敲入
            if (not knock_in) and (S <= optn.l_price):
                knock_in = True   

            # 计算option价格                                  
            optn.set_Var_Params(
                S, 
                rmq,
                sigma, 
                T, 
                knock_in
            )
            optn_price = optn.get_Valuation()
            optn_data.loc[i, 'optn_price'] = optn_price * optn.notional
            
            # 计算Delta
            optn_data.loc[i, 'delta'] = optn.delta(precision) * optn.notional

            pbar.update(1)

            # 若敲出, 截断
            if (kots[0] == 0) and (S >= optn.u_prices[0]):
                break

            # 若结束, 截断
            if T == 0:
                break

            pbar.update(dl - i - 1)

        optn_data['kots'] = optn_data['kots'].apply(lambda x: x[0])
        self.optn_data = optn_data.iloc[:i+1] # type: ignore

        return self.optn_data                     
        
    def calc_Hedge_Data(
            self, 
        ) -> pd.DataFrame:

        '''
        计算单雪球的对冲盈亏
        '''
        
        optn_data = self.optn_data
            
        # 计算对冲仓位和资金流
        data = optn_data[['Date','close','Down_Barrier_Price','Up_Barrier_Price','f1_close','f2_close','expiry_date','optn_price','delta', 'rmq', 'sigma']].copy()
        
        # 计算对冲仓位
        # data['hedge'] = -data['delta']
        data['hedge'] = -data['delta'] * np.exp((-data['rmq'])*(data['expiry_date'] - data['Date']).dt.days / 252)
        
        # 计算仓位变动和资金需求
        data['d_hedge'] = data['hedge'].diff(1)
        data.loc[0, 'd_hedge'] = 0  # 首日没有前期仓位
        data['d_hedge_cost'] = data['d_hedge'] * data['f1_close']
        
        # 处理换仓
        expiry_inds = data[data['Date'] == data['expiry_date']].index
        data.loc[expiry_inds, 'd_hedge_cost'] = (
            data.loc[expiry_inds, 'f2_close'] * data.loc[expiry_inds, 'hedge'] - 
            data.loc[expiry_inds, 'f1_close'] * data.shift(1).loc[expiry_inds, 'hedge']
        )
        
        # 计算买入金额
        optn_cost = self.optn.notional
        data['cost_daily'] = 0.
        # 首日买入 = 期权费 + 对冲仓位成本
        data.loc[0, 'cost_daily'] = (
            optn_cost + 
            data.loc[0, 'hedge'] * data.loc[0, 'f1_close']) # type: ignore
        # 非首日买入 = 对冲仓位变动的资金需求
        data.loc[1:, 'cost_daily'] = data.loc[1:, 'd_hedge_cost']
        # 累计买入
        data['cost'] = data['cost_daily'].cumsum()
        
        # 计算每日盈亏
        # 市值 = 期权市值 - 对冲仓位市值
        data['market_value'] = data['optn_price'] + data['f1_close'] * data['hedge']
        # 期货到期日使用远月合约计算市值
        data.loc[expiry_inds, 'market_value'] = data.loc[expiry_inds, 'optn_price'] + data.loc[expiry_inds, 'f2_close'] * data.loc[expiry_inds, 'hedge']
        # 净值 = 市值 - 累计净买入金额
        data['net_value'] = data['market_value'] - data['cost']
        
        # 计算期权费
        data['optn_profit'] = data['optn_price'] - optn_cost                        # 期权头寸盈亏
        data['optn_ret'] = data['optn_profit'] / optn_cost                          # 期权收益率
        
        # 计算净值
        data['portfolio_ret'] = data['net_value'] / optn_cost                       # 净值收益率
        
        # 计算对冲收益
        data['hedge_net_value'] = data['net_value'] - data['optn_profit']
        data['hedge_ret'] = data['hedge_net_value'] / optn_cost                     # 对冲收益率
        
        # 计算对冲误差指标
        expiry_inds = data[data['Date'] == data['expiry_date']].index
        v_1 = data['optn_price'].shift(1) + data['hedge'].shift(1)*data['f1_close'].shift(1)
        t = expiry_inds + 1
        mask = (t < len(v_1))
        v_1[t[mask]] = data['optn_price'][expiry_inds[mask]] + data['hedge'][expiry_inds[mask]] * data['f2_close'][expiry_inds[mask]]
        v_2 = data['optn_price'] + data['hedge'].shift(1)*data['f1_close']
        data['hedge_error'] = (v_2 - v_1)
        data.loc[0, 'hedge_error'] = 0.

        self.hedge_data = data

        return data
    
    def calc_Cost_Stats(
            self
        ) -> tuple[pd.DataFrame, pd.Series]:

        '''
        计算单雪球的成本和收益统计指标
        '''

        data = self.hedge_data

        # 最大对冲金额
        hedge_cost_mean = data['cost'].mean()       
        hedge_cost_max = data['cost'].max()
        
        # 计算期权指标
        optn_ret_end = data.loc[data.index[-1], 'optn_ret']                         # 最终期权收益率
        optn_ret_std = data['optn_ret'].std()                                       # 期权收益标准差
        
        # 计算净值指标
        portfolio_ret_end = data.loc[data.index[-1], 'portfolio_ret']               # 最终净收益率
        portfolio_ret_std = data['portfolio_ret'].std()                             # 净值收益标准差

        # 计算对冲收益指标
        hedge_ret_end = data.loc[data.index[-1], 'hedge_ret']                       # 最终对冲收益率
        hedge_ret_std = data['hedge_ret'].std()                                     # 对冲收益率标准差

        # 计算对冲误差
        hedge_error_mean = data['hedge_error'].abs().mean()
        hedge_error_max = data['hedge_error'].abs().max()
        
        # 汇总成本数据
        indicators = pd.Series({
            'Hedge_Cost_Mean': hedge_cost_mean,
            'Hedge_Cost_Max': hedge_cost_max,
            'Optn_Cost': self.optn.notional,
            'Optn_Ret_End': optn_ret_end,
            'Portfolio_Ret_End': portfolio_ret_end,
            'Hedge_Ret_End': hedge_ret_end,
            'Optn_Ret_Std': optn_ret_std,
            'Portfolio_Ret_Std': portfolio_ret_std,
            'Hedge_Ret_Std': hedge_ret_std,
            'hedge_error_mean': hedge_error_mean,
            'hedge_error_max': hedge_error_max
        })
        
        self.stats_data = data
        self.indicators = indicators

        return data, indicators