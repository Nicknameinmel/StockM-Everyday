import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# --- 1. 配置股票池 ---
# 自动映射 Yahoo 后缀
RAW_CODES = [
    '600285', '200429', '600096', '600887', '000895', 
    '002027', '601298', '600938', '601919', '600900', '002714'
]

def get_yahoo_symbol(code):
    if code.startswith('6'): return f"{code}.SS"
    if code.startswith('0') or code.startswith('3'): return f"{code}.SZ"
    if code.startswith('2'): return f"{code}.SZ" # B股深圳
    return code

MY_STOCKS = [get_yahoo_symbol(c) for c in RAW_CODES]

# 目标收益率列表
TARGET_YIELDS = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07]

def get_stock_data(symbol):
    try:
        print(f"正在获取: {symbol} ...")
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # --- 1. 基础数据 ---
        name = info.get('longName', info.get('shortName', symbol))
        
        # 价格与汇率处理
        price = info.get('regularMarketPrice', info.get('currentPrice'))
        currency = info.get('currency', 'CNY')
        
        # 简单汇率处理 (主要针对B股)
        exchange_rate = 1.0
        if currency == 'HKD':
            exchange_rate = 0.92 # 假设港币汇率
        elif currency == 'USD':
            exchange_rate = 7.2  # 假设美元汇率
            
        # 统一转为人民币计算
        price_cny = price * exchange_rate if price else 0
        
        mkt_cap = info.get('marketCap')
        # 如果市值是外币，也转人民币
        if mkt_cap and currency != 'CNY':
            mkt_cap = mkt_cap * exchange_rate

        shares = info.get('sharesOutstanding')
        
        # --- 2. 归母净利润 ---
        financials = ticker.financials
        latest_net_profit = None
        
        if not financials.empty:
            # 优先找归母净利润
            target_rows = ['Net Income Common Stockholders', 'Net Income']
            for row_name in target_rows:
                if row_name in financials.index:
                    # 取最近一期
                    latest_col = sorted(financials.columns, reverse=True)[0]
                    val = financials.loc[row_name, latest_col]
                    if pd.notna(val):
                        latest_net_profit = float(val)
                        break
        
        # --- 3. 分红比例 ---
        # 优先用 API 返回的 payoutRatio，如果没有则给个默认保守值或标记N/A
        avg_div_ratio = info.get('payoutRatio', None)
        
        # --- 4. 计算逻辑 ---
        # 核心公式: (净利润 * 0.8 * 分红率) / 市值
        predicted_yield = None
        
        if latest_net_profit and avg_div_ratio and mkt_cap:
            predicted_yield = (latest_net_profit * 0.8 * avg_div_ratio) / mkt_cap

        # 计算不同收益率下的预测股价
        # 预测股价 = (每股收益EPS * 0.8 * 分红率) / 目标收益率
        # 其中 EPS = 净利润 / 总股本
        eps = latest_net_profit / shares if (latest_net_profit and shares) else 0
        
        target_prices = {}
        for rate in TARGET_YIELDS:
            col_name = f"{int(rate*100)}%预测股价"
            if eps and avg_div_ratio:
                # 预测股价 (CNY)
                p = (eps * 0.8 * avg_div_ratio) / rate
                target_prices[col_name] = f"{p:.2f}"
            else:
                target_prices[col_name] = "N/A"

        # --- 5. 组装数据 ---
        data = {
            '股票代码': symbol.split('.')[0], # 去掉后缀显示
            '股票名称': name,
            '总市值(亿元)': f"{mkt_cap/1e8:.2f}" if mkt_cap else "N/A",
            '总股本(亿股)': f"{shares/1e8:.2f}" if shares else "N/A",
            '最近一年归母净利润(亿元)': f"{latest_net_profit/1e8:.2f}" if latest_net_profit else "N/A",
            '近5年平均分红比例': f"{avg_div_ratio*100:.2f}%" if avg_div_ratio is not None else "N/A",
            '股息穿透收益率预测(%)': f"{predicted_yield*100:.2f}%" if predicted_yield else "N/A",
            # 展开预测股价
            **target_prices,
            '当前股价': f"{price_cny:.2f}" if price_cny else "N/A"
        }
        
        return data

    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None

def main():
    results = []
    print("开始获取数据...")
    
    for code in MY_STOCKS:
        data = get_stock_data(code)
        if data:
            results.append(data)
        time.sleep(1) # 防封

    if results:
        # 定义列顺序
        columns = [
            '股票代码', '股票名称', '总市值(亿元)', '总股本(亿股)', 
            '最近一年归母净利润(亿元)', '近5年平均分红比例', '股息穿透收益率预测(%)',
            '2%预测股价', '3%预测股价', '4%预测股价', 
            '5%预测股价', '6%预测股价', '7%预测股价', '当前股价'
        ]
        
        df = pd.DataFrame(results)
        # 确保列存在且顺序正确
        final_cols = [c for c in columns if c in df.columns]
        df = df[final_cols]
        
        filename = 'dividend_report.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"报告已生成: {filename}")
        print("="*50)
        print(df.to_string())
    else:
        print("未获取到数据")

if __name__ == "__main__":
    main()
