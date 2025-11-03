# 标准库
from os.path import dirname
import sys
sys.path.append(dirname(__file__))

# 第三方库
import numpy as np
import pandas as pd
from tqdm import tqdm

# 个人库
from BasicTool.HedgeBt_SOLE import HedgeBt_SOLE
from BasicTool.Option import Autocallable

###
class HedgeBt_R(HedgeBt_SOLE):
    def __init__(
            self, 
            start_date: str, 
            end_date: str, 
            file_path: str, 
            udly: str, 
            hedge_ins: str, 
            optn: Autocallable
        ) -> None:

        '''
        创建连续雪球回测类
        '''

        super().__init__(
            start_date, 
            end_date, 
            file_path, 
            udly, 
            hedge_ins, 
            optn
        )

    def get_Optn_Data(
            self,
            precision: float = 0.01
        ) -> pd.DataFrame:

        '''
        计算滚动雪球的各雪球的期权价格和delta
        '''

        optn = self.optn
        mkt_data = self.mkt_data
        optn_data = pd.DataFrame() # optn总表

        i = 0
        my_id = 1
        dl = len(mkt_data)
        pbar = tqdm(total=dl, desc='optn处理进度: ', ncols=95, file=sys.stdout)

        while i in mkt_data.index:
            data = mkt_data.iloc[i:i+optn.matu+1].copy()
            data.reset_index(drop=True, inplace=True)
            S_0: float = data.loc[0, 'close'] # type: ignore
            optn.set_Init_Params(S_0)

            data['ID'] = my_id
            data['S_0'] = S_0
            data['K'] = optn.k_price
            data['Up_Barrier_Price'] = optn.u_prices[0]
            data['Down_Barrier_Price'] = optn.l_price
            data['kots'] = self.optn._kots_vec[:len(data)]
            data = data[
                [
                    'ID',
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

            data['optn_price'] = 0.
            data['delta'] = 0.
            knock_in = False

            for (j, row) in enumerate(data.itertuples()):
                S = getattr(row, 'close', 0.) 
                sigma = getattr(row, 'sigma', 0.) 
                kots = getattr(row, 'kots', [])
                rmq = getattr(row, 'rmq', 0.)

                T = optn.matu - j

                if (not knock_in) and (S <= optn.l_price):
                    knock_in = True 
                
                optn.set_Var_Params(
                    S, 
                    rmq, 
                    sigma, 
                    T,
                    knock_in
                )
                data.loc[j, 'optn_price'] = optn.get_Valuation() * optn.notional
                data.loc[j, 'delta'] = optn.delta(precision) * optn.notional

                if (kots[0] == 0) and (S >= optn.u_prices[0]):
                    break 

                if T == 0:
                    break 
            
            data = data.iloc[:j+1] # type: ignore
            optn_data = pd.concat([optn_data, data], axis=0)
            i += (j+1) # type: ignore
            my_id += 1
            pbar.update(j+1) # type: ignore

        optn_data['kots'] = optn_data['kots'].apply(lambda x: x[0])
        self.optn_data = optn_data

        return optn_data
    
    def calc_Hedge_Data(
            self, 
        ) -> pd.DataFrame:

        '''
        计算滚动雪球的对冲盈亏
        '''

        optn_data = self.optn_data
            
        def process(group):
            # 计算对冲仓位和资金流
            data = group[['Date','close','Up_Barrier_Price', 'K', 'Down_Barrier_Price','f1_close','f2_close','expiry_date','optn_price','delta', 'rmq', 'sigma']].copy()
            
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

            return data

        self.hedge_data = optn_data.groupby('ID')[optn_data.columns].apply(process)
        
        return self.hedge_data # type: ignore

    def calc_Cost_Stats(
            self
        ) -> tuple[pd.DataFrame, pd.Series]:

        '''
        计算滚动雪球的成本和收益统计指标
        '''
        
        data = self.hedge_data.groupby('Date', as_index=True)[['cost', 'optn_ret', 'portfolio_ret', 'hedge_ret', 'hedge_error']].mean().reset_index()

        # 最大对冲金额
        hedge_cost_mean = data['cost'].mean()       
        hedge_cost_max = data['cost'].max()
        
        # 计算期权指标
        optn_ret_end = data.loc[data.index[-1], 'optn_ret']                             # 最终期权收益率
        optn_ret_std = data['optn_ret'].std()                                           # 期权收益标准差
        
        # 计算净值指标
        portfolio_ret_end = data.loc[data.index[-1], 'portfolio_ret']                   # 最终净收益率
        portfolio_ret_std = data['portfolio_ret'].std()                                 # 净值收益标准差

        # 计算对冲收益指标
        hedge_ret_end = data.loc[data.index[-1], 'hedge_ret']                           # 最终对冲收益率
        hedge_ret_std = data['hedge_ret'].std()                                         # 对冲收益率标准差

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