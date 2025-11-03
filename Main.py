# 标准库
import ctypes
import io
from math import floor
import tkinter as tk
from tkinter import ttk, filedialog
import sys
from threading import Lock
import os
import threading

ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 启用高DPI感知
user32 = ctypes.windll.user32
dpi = user32.GetDpiForSystem()
scale_factor = dpi / 96

# 第三方库
from PIL import Image

# 个人库
import Main_Bt

###
class TextRedirector(io.StringIO):
    
    '''
    该类将原本输入在终端的内容转移到界面里\n
    精准处理tqdm进度条, 只更新进度条行，避免误删前面内容
    '''

    def __init__(self, text_widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_widget = text_widget
        self.lock = Lock()
        self.progress_line_start = None  # 记录进度条行的起始位置
        self.is_progress_active = False  # 标记是否有活跃的进度条

    def write(self, string):
        self.lock.acquire()
        try:
            self.text_widget.configure(state="normal")

            if 'optn处理进度' in string:
                progress_content = string
                
                if self.is_progress_active and self.progress_line_start:
                    end_index = self.text_widget.index("end-1c")
                    self.text_widget.delete(self.progress_line_start, end_index)
                    self.text_widget.insert(self.progress_line_start, progress_content)
                else:
                    self.progress_line_start = self.text_widget.index("end-1c")
                    self.text_widget.insert(tk.END, progress_content)
                    self.is_progress_active = True
                
            else:
                if self.is_progress_active and '<optn_data> Received.' in string:
                    self.is_progress_active = False
                    self.progress_line_start = None
                
                self.text_widget.insert(tk.END, string)
            
            self.text_widget.see(tk.END)
            self.text_widget.configure(state="disabled")
        finally:
            self.lock.release()

    def flush(self):
        pass

class BtEngineGUI:
    def __init__(self, root):

        '''
        创建一个回测引擎类
        '''

        self.root = root
        self.root.title('\'NetValueSnowball\'回测引擎界面')
        length = floor(800 * scale_factor)
        width = floor(600 * scale_factor)
        self.root.geometry(f'{length}x{width}')
        self.root.resizable(False, False)
        
        # 从Config.py加载默认配置
        self.load_Config()
        
        # 创建界面组件
        self.create_Widgets()
        
    def load_Config(self):
        
        '''
        从Main_Bt.py加载参数
        '''

        self.start_date = Main_Bt.start_date
        self.end_date = Main_Bt.end_date
        self.file_path = Main_Bt.file_path
        self.udly = Main_Bt.udly
        self.hedge_ins = Main_Bt.hedge_ins
        self.u_ratios = Main_Bt.u_ratios
        self.l_ratio = Main_Bt.l_ratio
        self.k_ratio = Main_Bt.k_ratio
        self.Coupon = Main_Bt.Coupon
        self.Rebate = Main_Bt.Rebate
        self.matu = Main_Bt.matu
        self.rf = Main_Bt.rf
        self.kots_0 = Main_Bt.kots_0
        self.notional = Main_Bt.notional
        self.engine_name = Main_Bt.engine_name
    
    def create_Widgets(self):
        
        '''
        创建界面组件
        '''

        main_frame = ttk.Frame(self.root, padding='10')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tab_control = ttk.Notebook(main_frame)
        
        # 配置: 标签页
        tab = ttk.Frame(tab_control)
        tab_control.add(tab, text='配置')
        
        tab_control.pack(expand=1, fill='both')
        
        # 配置: 内容
        self.create_Tab(tab)
        
        # 底部按钮区域
        btn_frame = ttk.Frame(main_frame, padding='10')
        btn_frame.pack(fill=tk.X, pady=floor(5 * scale_factor))
        
        ttk.Button(btn_frame, text='浏览文件', command=self.browse_File).pack(side=tk.LEFT, padx=floor(2.5 * scale_factor))
        ttk.Button(btn_frame, text='重置', command=self.reset_Config).pack(side=tk.RIGHT, padx=floor(2.5 * scale_factor))
        ttk.Button(btn_frame, text='运行', command=self.run_).pack(side=tk.RIGHT, padx=floor(2.5 * scale_factor))
        
        # 状态标签
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(main_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=floor(2.5 * scale_factor))
    
    def create_Tab(self, parent):
        
        '''
        创建基本配置标签页内容
        '''

        frame = ttk.Frame(parent, padding='10')
        frame.pack(fill=tk.BOTH, expand=True)

        for i in range(6):
            frame.columnconfigure(i, weight=1)
        
        # 行计数器
        row = 0
        
        # 文件路径
        ttk.Label(frame, text='文件路径:').grid(row=row, column=0, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.file_path_var = tk.StringVar(value=self.file_path)
        ttk.Entry(frame, textvariable=self.file_path_var, width=floor(41 * scale_factor)).grid(row=row, column=1, columnspan=5, sticky=tk.EW, pady=floor(2.5 * scale_factor))
        row += 1
        
        # 开始日期
        ttk.Label(frame, text='开始日期:').grid(row=row, column=0, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.start_date_var = tk.StringVar(value=self.start_date)
        ttk.Entry(frame, textvariable=self.start_date_var, width=floor(10 * scale_factor)).grid(row=row, column=1, sticky=tk.W, pady=floor(2.5 * scale_factor))
        
        # 结束日期
        ttk.Label(frame, text='结束日期:').grid(row=row, column=2, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.end_date_var = tk.StringVar(value=self.end_date)
        ttk.Entry(frame, textvariable=self.end_date_var, width=floor(10 * scale_factor)).grid(row=row, column=3, sticky=tk.W, pady=floor(2.5 * scale_factor))

        # 引擎名称
        ttk.Label(frame, text='引擎名称:').grid(row=row, column=4, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.engine_name_var = tk.StringVar(value=self.engine_name)
        ttk.Combobox(frame, textvariable=self.engine_name_var, values=['c', 'r', 's'], width=floor(9.0 * scale_factor), state='readonly').grid(
            row=row, column=5, sticky=tk.W, pady=floor(2.5 * scale_factor))
        row += 1
        
        # 标的代码
        ttk.Label(frame, text='标的代码:').grid(row=row, column=0, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.udly_var = tk.StringVar(value=self.udly)
        ttk.Entry(frame, textvariable=self.udly_var, width=floor(10 * scale_factor)).grid(row=row, column=1, sticky=tk.W, pady=floor(2.5 * scale_factor))
        
        # 对冲工具
        ttk.Label(frame, text='对冲工具:').grid(row=row, column=2, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.hedge_ins_var = tk.StringVar(value=self.hedge_ins)
        ttk.Entry(frame, textvariable=self.hedge_ins_var, width=floor(10 * scale_factor)).grid(row=row, column=3, sticky=tk.W, pady=floor(2.5 * scale_factor))
        
        # 名义金额
        ttk.Label(frame, text='名义金额:').grid(row=row, column=4, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.notional_var = tk.StringVar(value=str(self.notional))
        ttk.Entry(frame, textvariable=self.notional_var, width=floor(10 * scale_factor)).grid(row=row, column=5, sticky=tk.W, pady=floor(2.5 * scale_factor))
        row += 1
        
        # 到期天数
        ttk.Label(frame, text='到期天数:').grid(row=row, column=0, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.matu_var = tk.StringVar(value=str(self.matu))
        ttk.Entry(frame, textvariable=self.matu_var, width=floor(10 * scale_factor)).grid(row=row, column=1, sticky=tk.W, pady=floor(2.5 * scale_factor))
        
        # 敲入比率
        ttk.Label(frame, text='敲入比率:').grid(row=row, column=2, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.l_ratio_var = tk.StringVar(value=str(self.l_ratio))
        ttk.Entry(frame, textvariable=self.l_ratio_var, width=floor(10 * scale_factor)).grid(row=row, column=3, sticky=tk.W, pady=floor(2.5 * scale_factor))
        
        # k比率
        ttk.Label(frame, text='k比率:').grid(row=row, column=4, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.k_ratio_var = tk.StringVar(value=str(self.k_ratio))
        ttk.Entry(frame, textvariable=self.k_ratio_var, width=floor(10 * scale_factor)).grid(row=row, column=5, sticky=tk.W, pady=floor(2.5 * scale_factor))
        row += 1
        
        # Coupon
        ttk.Label(frame, text='Coupon:').grid(row=row, column=0, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.Coupon_var = tk.StringVar(value=str(self.Coupon))
        ttk.Entry(frame, textvariable=self.Coupon_var, width=floor(10 * scale_factor)).grid(row=row, column=1, sticky=tk.W, pady=floor(2.5 * scale_factor))
        
        # Rebate
        ttk.Label(frame, text='Rebate:').grid(row=row, column=2, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.Rebate_var = tk.StringVar(value=str(self.Rebate))
        ttk.Entry(frame, textvariable=self.Rebate_var, width=floor(10 * scale_factor)).grid(row=row, column=3, sticky=tk.W, pady=floor(2.5 * scale_factor))
        
        # RF
        ttk.Label(frame, text='RF:').grid(row=row, column=4, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.rf_var = tk.StringVar(value=str(self.rf))
        ttk.Entry(frame, textvariable=self.rf_var, width=floor(10 * scale_factor)).grid(row=row, column=5, sticky=tk.W, pady=floor(2.5 * scale_factor))
        row += 1
        
        # 敲出日期
        ttk.Label(frame, text='敲出日期:').grid(row=row, column=0, sticky=tk.W, pady=floor(2.5 * scale_factor))
        ttk.Label(frame, text='支持Python原生语法和NumPy语法, 如:\n    [63] + 9 * [21]').grid(row=row, column=3, columnspan=3, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.kots_text = tk.Text(frame, height=3, width=floor(16 * scale_factor))
        self.kots_text.grid(row=row, rowspan=3, column=1, columnspan=2, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.kots_text.insert(tk.END, str(self.kots_0))
        row += 3
        
        # 敲出比率
        ttk.Label(frame, text='敲出比率:').grid(row=row, column=0, sticky=tk.W, pady=floor(2.5 * scale_factor))
        ttk.Label(frame, text='支持Python原生语法和NumPy语法, 如:\n    np.linspace(1.0, 0.8, 10)').grid(row=row, column=3, columnspan=3, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.u_ratios_text = tk.Text(frame, height=3, width=floor(16 * scale_factor))
        self.u_ratios_text.grid(row=row, rowspan=3, column=1, columnspan=2, sticky=tk.W, pady=floor(2.5 * scale_factor))
        self.u_ratios_text.insert(tk.END, str(self.u_ratios))
        row += 3

        # 终端输出显示区域
        ttk.Label(frame, text='终端输出:').grid(row=row, column=0, sticky=tk.NW, pady=floor(2.5 * scale_factor))
        
        # 创建带滚动条的文本框
        output_frame = ttk.Frame(frame)
        output_frame.grid(row=row, column=1, columnspan=5, sticky=tk.NSEW, pady=floor(2.5 * scale_factor))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # 垂直滚动条
        scrollbar = ttk.Scrollbar(output_frame)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        
        # 文本框
        self.output_text = tk.Text(output_frame, height=floor(10 * scale_factor), width=floor(49 * scale_factor), state="disabled", wrap=tk.WORD, yscrollcommand=scrollbar.set)
        self.output_text.grid(row=0, column=0, sticky=tk.NSEW)
        
        # 关联滚动条
        scrollbar.config(command=self.output_text.yview)
        
        # 重定向标准输出
        self.redirector = TextRedirector(self.output_text)
        sys.stdout = self.redirector
        
        row += 1
        frame.rowconfigure(row-1, weight=1)
    
    def browse_File(self):

        '''
        浏览并选择数据文件
        '''

        filename = filedialog.askopenfilename(
            title='选择数据文件',
            filetypes=[('Excel文件', '*.xlsx;*.xls'), ('所有文件', '*.*')]
        )
        if filename:
            self.file_path_var.set(filename)
    
    def reset_Config(self):

        '''
        重置配置为默认值
        '''

        self.load_Config()
        self.file_path_var.set(self.file_path)
        self.start_date_var.set(self.start_date)
        self.end_date_var.set(self.end_date)
        self.udly_var.set(self.udly)
        self.hedge_ins_var.set(self.hedge_ins)
        self.matu_var.set(str(self.matu))
        self.l_ratio_var.set(str(self.l_ratio))
        self.k_ratio_var.set(str(self.k_ratio))
        self.Coupon_var.set(str(self.Coupon))
        self.Rebate_var.set(str(self.Rebate))
        self.rf_var.set(str(self.rf))
        self.notional_var.set(str(self.notional))
        self.engine_name_var.set(self.engine_name)
        
        # 重置kots_0和u_ratios
        self.kots_text.delete(1.0, tk.END)
        self.kots_text.insert(tk.END, str(self.kots_0))
        self.u_ratios_text.delete(1.0, tk.END)
        self.u_ratios_text.insert(tk.END, str(self.u_ratios))
        
        # 清空输出区域
        self.output_text.configure(state="normal")
        self.output_text.delete(1.0, tk.END)
        self.output_text.configure(state="disabled")
        
        self.status_var.set('就绪')
    
    def parse_Expr(self, expr):

        '''
        解析输入指令
        '''

        return eval(expr.strip())
    
    def run_(self):

        '''
        运行引擎
        '''

        params = {
            'start_date': self.start_date_var.get(),
            'end_date': self.end_date_var.get(),
            'file_path': self.file_path_var.get(),
            'udly': self.udly_var.get(),
            'hedge_ins': self.hedge_ins_var.get(),
            'matu': int(self.matu_var.get()),
            'l_ratio': float(self.l_ratio_var.get()),
            'k_ratio': float(self.k_ratio_var.get()),
            'Coupon': float(self.Coupon_var.get()),
            'Rebate': float(self.Rebate_var.get()),
            'rf': float(self.rf_var.get()),
            'notional': int(self.notional_var.get()),
            'engine_name': self.engine_name_var.get()
        }
        
        # 解析 kots_0 & u_ratios
        kots_expr = self.kots_text.get(1.0, tk.END).strip()
        params['kots_0'] = self.parse_Expr(kots_expr)
        
        u_ratios_expr = self.u_ratios_text.get(1.0, tk.END).strip()
        params['u_ratios'] = self.parse_Expr(u_ratios_expr)
        
        # 显示运行中状态
        self.status_var.set('运行中...')
        self.root.update()
        
        threading.Thread(
            target=self._run_,
            args=(params,),
            daemon=True
        ).start()
    
    def _run_(self, params):

        '''
        子线程中执行引擎
        '''

        engine = Main_Bt.Engine_Bt(** params)
        engine.Go_()
        img_path = os.path.join(os.path.dirname(__file__), 'Result', 'summary_fig.jpg')
        img = Image.open(img_path)
        img.show()
        self.status_var.set('就绪')
        self.root.update()

if __name__ == '__main__':
    root = tk.Tk()
    root.option_add('*Font', 'SimSun 10')
    app = BtEngineGUI(root)
    root.mainloop()