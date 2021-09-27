# Trality Multicoin Accumulator

*NOTE: This is a complete rewrite of the original "Multicoin Portfolio Balancer", which is now deprecated.*

This is not a traditional enter/exit position algorithm. It's better intended to try to buy dips and sell tops while swinging HODLings on a portfolio.
The algorithm detects RSI 'turnarounds' beyond user defined buy/sell RSI zones, as well as bollinger breakouts on custom lower/upper bollinger bands that can be contracted/expanded and raised/lowered by user parameters. Both the custom Bollinger bands and the RSI buy/sell zones are plotted in Trality charts for easy visualization in either backtests and real time trading, as you can see in the image below

![image](https://user-images.githubusercontent.com/80478409/134986298-5b2623d9-1e79-4a7d-b4a8-18d819177cbb.png)
The backtest and realtime results are quite good, however the bot must be used with care. Using it on a short timeframe (below 1h) can show impressive gains on a volatile bull market, but will probably buy too much on the way down to the dip when in a bear market. Crypto trading is very risky and backward results are NEVER proof of future gains. Please understand the risks before running this code on a real exchange.

Comments and contributions are welcome. Have fun!
