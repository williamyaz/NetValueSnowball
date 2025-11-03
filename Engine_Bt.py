# 标准库
from os.path import dirname, join
import sys
import time
sys.path.append(dirname(__file__))

# 第三方库
import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# 个人库
from Tool.HedgeBt_C import HedgeBt_C
from Tool.HedgeBt_R import HedgeBt_R 
from Tool.HedgeBt_S import HedgeBt_S
from Tool.BasicTool.Option import Autocallable

###
class Engine_Bt():
    def __init__(
            self, 
            start_date: str, 
            end_date: str, 
            file_path: str,
            udly: str, 
            hedge_ins: str, 
            u_ratios: list | np.ndarray, 
            l_ratio: float, 
            k_ratio: float, 
            Coupon: float, 
            Rebate: float,  
            matu: int,
            rf: float,
            kots_0: list | np.ndarray, 
            notional: int, 
            engine_name: str
        ) -> None:

        '''
        雪球回测引擎\n
        engine_name应该为c, r, s中的一个, 不区分大小写
        '''

        engine_name = engine_name.lower()
        match engine_name:
            case 'c':
                self.bt_class = HedgeBt_C
                self.engine_name = '连续雪球'
            case 'r':
                self.bt_class = HedgeBt_R
                self.engine_name = '滚动雪球'
            case 's':
                self.bt_class = HedgeBt_S
                self.engine_name = '单雪球'
            case _:
                raise NameError('engine_name应该为c, r, s中的一个, 不区分大小写')
        optn = Autocallable(
                np.array(u_ratios), 
                l_ratio, 
                k_ratio, 
                Coupon, 
                Rebate, 
                matu, 
                rf, 
                list(kots_0), 
                notional
            )
        self.bt = self.bt_class(
                start_date, 
                end_date, 
                file_path, 
                udly, 
                hedge_ins, 
                optn
            )
    
    def Go_(self):

        '''
        回测引擎主函数
        '''

        t_0 = time.time()
        print('\n'+50*'*'+'\n')

        bt = self.bt

        print(f'运行{self.engine_name}...\n')

        print('start <getUdlyData>...')
        self.udly_data = bt.get_Udly_Data()
        print('<udly_data> Received.\n')

        print('start <getHedgeData>...')
        self.hedge_ins_data = bt.get_Hedge_Data()
        print('<hedge_ins_data> Received.\n')

        print('start <getMktData>...')
        self.mkt_data = bt.get_Mkt_Data()
        print('<mkt_data> Received.\n')

        print('start <getOptnData>...')
        self.optn_data = bt.get_Optn_Data()
        self.optn_data.to_csv(join(dirname(__file__), 'Result\\optn_data.csv'))
        print('<optn_data> Received.\n')

        print('start <calcHedgeData>...')
        self.hedge_data = bt.calc_Hedge_Data()
        self.hedge_data.to_csv(join(dirname(__file__), 'Result\\hedge_data.csv'))
        print('<hedge_data> Received.\n')

        print('start <calcCostStats>...')
        self.stats_data, self.indicators = bt.calc_Cost_Stats()
        self.stats_data.to_csv(join(dirname(__file__), 'Result\\stats_data.csv'))
        print('<stats_data> Received.\n')

        print(f'共计运行时间: {time.time() - t_0:.3f} 秒\n')

        i = 0
        for k,v in self.indicators.items():
            print(f'{k:20}{v:20.4f}')
            i += 1
            if i % 3 == 0:
                print(50*'-')
        print('\n'+50*'*')

        # 绘制结果
        sns.set_theme(
            style='whitegrid',
            palette='colorblind',
        )

        _, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

        # -------------------- 子图一：收益对比 --------------------
        ax1 = axes[0]
        sns.lineplot(
            data=bt.stats_data,
            x='Date',
            y='optn_ret',
            label='optn_ret',
            ax=ax1,
            linewidth=1
        )
        sns.lineplot(
            data=bt.stats_data,
            x='Date',
            y='portfolio_ret',
            label='portfolio_ret',
            ax=ax1,
            linewidth=1
        )
        sns.lineplot(
            data=bt.stats_data,
            x='Date',
            y='hedge_ret',
            label='hedge_ret',
            ax=ax1,
            linewidth=1
        )
        ax1.axhline(y=0, color='red', linestyle='--', linewidth=1.5)
        ax1.legend(loc='upper left', frameon=True, framealpha=0.8)
        ax1.set_title('Optn Ret / Portfolio Ret / Hedge Ret', pad=15)
        ax1.set_ylabel('')

        # -------------------- 子图二：对冲误差 --------------------
        ax2 = axes[1]
        sns.lineplot(
            data=bt.stats_data,
            x='Date',
            y='hedge_error',
            label='hedge_error',
            ax=ax2,
            color='black',
            linewidth=1
        )
        ax2.axhline(y=0, color='red', linestyle='--', linewidth=1.5)
        ax2.legend(loc='upper left', frameon=True, framealpha=0.8)
        ax2.set_title('Hedge Error', pad=15)
        ax2.set_ylabel('')

        # -------------------- 子图三：收盘价 --------------------
        ax3 = axes[2]
        sns.lineplot(
            data=bt.mkt_data,
            x='Date',
            y='close',
            label='close',
            ax=ax3,
            linewidth=1
        )
        ax3.legend(loc='upper left', frameon=True, framealpha=0.8)
        ax3.set_title('close', pad=15)
        ax3.set_ylabel('')

        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        save_path = join(dirname(__file__), 'Result\\summary_fig.jpg')
        plt.savefig(save_path, dpi=800, bbox_inches='tight')
        plt.close()