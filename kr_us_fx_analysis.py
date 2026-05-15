"""
한국-미국 주가 상대수익률이 KRW/USD 환율에 미치는 영향 검증

- 표본 기간: 2020-01-01 ~ 현재 (코로나 이후)
- 시차 정렬: 같은 날짜 (단순)
- 가설: KOSPI가 S&P 대비 강세 → 외국인 자금 유입 → KRW 강세 (KRW/USD 하락)
  → 따라서 β(spread → KRW/USD return) < 0 이면 가설 지지

필요 패키지:
pip install yfinance pandas numpy statsmodels matplotlib
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, grangercausalitytests
import matplotlib.pyplot as plt

# ----- 1. 데이터 수집 -----

START = "2020-01-01"

tickers = {
    "KOSPI":  "^KS11",
    "SP500":  "^GSPC",
    "KRWUSD": "KRW=X",   # 1 USD = X KRW. Frankfurter API 대체 가능
}

print("데이터 수집 중...")
prices = pd.DataFrame()
for name, t in tickers.items():
    df = yf.download(t, start=START, auto_adjust=True, progress=False)
    prices[name] = df["Close"].squeeze()

# 같은 날짜로 inner join (영업일 차이로 NaN 발생하는 행 제거)
prices = prices.dropna()
print(f"표본: {prices.index.min().date()} ~ {prices.index.max().date()}, "
      f"N={len(prices)} 거래일\n")

# ----- 2. 로그 일일 수익률 -----

ret = np.log(prices / prices.shift(1)).dropna()
ret["spread"] = ret["KOSPI"] - ret["SP500"]   # 한국 - 미국 상대 수익률

# ----- 3. 기술통계 & 정상성 검정 -----

print("=" * 60)
print("기술통계 (일일 수익률, %)")
print("=" * 60)
print((ret * 100).describe().round(3))

print("\n" + "=" * 60)
print("ADF 단위근 검정 (p < 0.05 면 정상)")
print("=" * 60)
for col in ["KOSPI", "SP500", "KRWUSD", "spread"]:
    stat, pval, *_ = adfuller(ret[col].dropna())
    flag = "✓ 정상" if pval < 0.05 else "✗ 비정상"
    print(f"  {col:8s}: ADF={stat:7.3f}, p={pval:.4f}  {flag}")

# ----- 4. 상관관계 -----

print("\n" + "=" * 60)
print("상관행렬")
print("=" * 60)
print(ret[["KOSPI", "SP500", "KRWUSD", "spread"]].corr().round(3))

# ----- 5. OLS 회귀 (HAC robust) -----

# KRW/USD 일일 수익률 ~ (KOSPI - S&P500) 일일 수익률
X = sm.add_constant(ret["spread"])
y = ret["KRWUSD"]
ols = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})

print("\n" + "=" * 60)
print("OLS: ΔKRW/USD ~ α + β·(KOSPI - S&P500),  HAC robust SE")
print("=" * 60)
print(ols.summary().tables[1])
beta = ols.params["spread"]
pval = ols.pvalues["spread"]
print(f"\n해석: spread 1%p 상승 시 KRW/USD 변화량 = {beta*100:.4f}%p")
print(f"      p-value = {pval:.4f}  → "
      f"{'유의함 (가설 지지)' if (beta < 0 and pval < 0.05) else '주의 필요'}")

# ----- 6. Granger 인과성 검정 -----

def granger(df, cause, effect, maxlag=5):
    print(f"\n[{cause} → {effect}]  H0: {cause}는 {effect}를 예측 못한다")
    g = grangercausalitytests(df[[effect, cause]].dropna(),
                              maxlag=maxlag, verbose=False)
    for lag in range(1, maxlag + 1):
        f, p, _, _ = g[lag][0]["ssr_ftest"]
        mark = "**" if p < 0.05 else "  "
        print(f"  Lag {lag}:  F={f:6.3f},  p={p:.4f} {mark}")

print("\n" + "=" * 60)
print("Granger 인과성 검정 (** = 5% 유의)")
print("=" * 60)
granger(ret, cause="spread", effect="KRWUSD")
granger(ret, cause="KRWUSD", effect="spread")

# ----- 7. 시각화 -----

fig, axes = plt.subplots(3, 1, figsize=(12, 11))

# (a) 정규화 주가
norm = prices[["KOSPI", "SP500"]].div(prices[["KOSPI", "SP500"]].iloc[0]) * 100
axes[0].plot(norm.index, norm["KOSPI"], label="KOSPI", linewidth=1.3)
axes[0].plot(norm.index, norm["SP500"], label="S&P 500", linewidth=1.3)
axes[0].set_title("주가지수 (시작일 = 100)")
axes[0].legend(); axes[0].grid(alpha=0.3)

# (b) 환율
axes[1].plot(prices.index, prices["KRWUSD"], color="darkred", linewidth=1.3)
axes[1].set_title("KRW/USD 환율 (1 USD 당 KRW)")
axes[1].grid(alpha=0.3)

# (c) 산점도
corr = ret["spread"].corr(ret["KRWUSD"])
axes[2].scatter(ret["spread"] * 100, ret["KRWUSD"] * 100,
                alpha=0.35, s=12, color="navy")
xs = np.linspace(ret["spread"].min(), ret["spread"].max(), 100)
axes[2].plot(xs * 100, (ols.params["const"] + beta * xs) * 100,
             color="orange", linewidth=2, label=f"OLS fit (β={beta:.3f})")
axes[2].axhline(0, color="gray", linewidth=0.5)
axes[2].axvline(0, color="gray", linewidth=0.5)
axes[2].set_xlabel("(KOSPI − S&P 500) 일일 로그 수익률 (%)")
axes[2].set_ylabel("KRW/USD 일일 로그 수익률 (%)")
axes[2].set_title(f"산점도 — 표본상관 = {corr:.3f}")
axes[2].legend(); axes[2].grid(alpha=0.3)

plt.tight_layout()
import os
os.makedirs("/mnt/user-data/outputs", exist_ok=True)
out_png = "/mnt/user-data/outputs/kr_us_fx_analysis.png"
plt.savefig(out_png, dpi=120, bbox_inches="tight")
print(f"\n그래프 저장: {out_png}")
