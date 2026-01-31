import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# --- 1. 在这里修改你的股票池 (必须带后缀: 上海.SS, 深圳.SZ) ---
MY_STOCKS = [
    '600519.SS',  # 贵州茅台
    '000858.SZ',  # 五粮液
    '600009.SS',  # 上海机场
    '600900.SS',  # 长江电力
    '000651.SZ'  # 格力电器
]


# --------------------------------------------------------

def get_stock_data(symbol):
    try:
        print(f"正在获取: {symbol} ...")
        ticker = yf.Ticker(symbol)

        # 获取基础信息 (可能会慢，加个重试或简单处理)
        info = ticker.info

        # 1. 基础数据
        name = info.get('longName', symbol)
        price = info.get('currentPrice', info.get('regularMarketPrice'))
        mkt_cap = info.get('marketCap')
        shares = info.get('sharesOutstanding')

        # 2. 财务数据 (Net Income)
        financials = ticker.financials
        latest_net_profit = None

        # 寻找净利润行
        net_income_row = None
        if not financials.empty:
            for key in ['Net Income', 'Net Income Common Stockholders']:
                if key in financials.index:
                    net_income_row = financials.loc[key]
                    break

        if net_income_row is not None:
            # 取最近一年的数据 (Yahoo列名是日期)
            latest_col = sorted(financials.columns, reverse=True)[0]
            latest_net_profit = net_income_row[latest_col]

        # 3. 分红数据
        div_history = ticker.dividends
        avg_div_ratio = None

        if not div_history.empty and latest_net_profit:
            # 计算每年的分红总额
            yearly_div = div_history.groupby(div_history.index.year).sum()
            current_year = datetime.now().year

            ratios = []
            for y in range(current_year - 4, current_year + 1):
                # 这里为了简化，假设净利润每年都取最近的近似值，或者需要更复杂的历史利润查询
                # 简单版：我们只计算最近一年的分红率作为参考，或者Yahoo有trailingAnnualDividendYield
                pass

                # 由于API限制，这里用 Yahoo 提供的 trailingAnnualDividendRate (过去一年分红)
            # 和 trailingPE 来倒推大致的分红意愿，或者直接使用 info 中的 dividendRate

            # 为了脚本稳定，我们采用简化策略：
            # 如果能拿到 info['payoutRatio'] (分红率)，直接用它
            payout_ratio = info.get('payoutRatio', None)
            if payout_ratio:
                avg_div_ratio = payout_ratio

        # 4. 预测计算
        predicted_yield = None
        if latest_net_profit and avg_div_ratio and mkt_cap:
            # 公式: (净利润 * 0.8 * 分红率) / 市值
            predicted_yield = (latest_net_profit * 0.8 * avg_div_ratio) / mkt_cap

        return {
            '代码': symbol,
            '名称': name,
            '现价': price,
            '分红率(Payout)': f"{avg_div_ratio * 100:.2f}%" if avg_div_ratio else "N/A",
            '预测穿透股息率': f"{predicted_yield * 100:.2f}%" if predicted_yield else "N/A",
            '市值(亿)': f"{mkt_cap / 1e8:.2f}" if mkt_cap else "0",
            '更新时间': datetime.now().strftime("%Y-%m-%d %H:%M")
        }

    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None


def main():
    results = []
    for code in MY_STOCKS:
        data = get_stock_data(code)
        if data:
            results.append(data)
        # 稍微停顿，防止请求过快
        time.sleep(1)

    # 保存结果
    if results:
        df = pd.DataFrame(results)
        filename = 'dividend_report.csv'
        # utf-8-sig 确保 Excel 打开中文不乱码
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"成功生成报告: {filename}")
        print(df)
    else:
        print("未获取到任何数据")


if __name__ == "__main__":
    main()