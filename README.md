# Trality Multicoin Porftfolio Balancer

This is a bot that creates weighted buys and sells (take profits) relative to the strength of signals.
The signal strategy is based upon RSI morphology (the peaks and valleys at RSI turnarounds) along with
general RSI trend, and also comparing and weighting two periods in Bollinger Bands.

This is not a traditional open/close position, double walls, etc. trading bot - it is instead a 
portfolio optimizer that automatically takes some profits when selling signals are strong, and buys
when buy signals are strong. The stronger the signals, the larger the amounts.

The bot also makes use of 'trailing orders' to maximize good sell/buy prices.

All parameters, trailing parameters and limits can be set globally (as default) and also, optionally, 
can be set individually for any or each portfolio pair (overrides default).

REV 5.5
- Corrected a small but important error in code :D



