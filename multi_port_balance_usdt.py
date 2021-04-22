import datetime

TITLE   = "MULTICOIN PORTFOLIO BALANCER - USDT"
VERSION = "VERSION 5.1"
AUTHOR  = "By @banshee70s @elerouxx in 2021-04-22"
DONATE  = ("TIP JAR WALLET:  \n" +  
           "ERC20 / BEP20:  0xA44dc8782d13f7728E7ec240D8dA99479d245c3C \n" +
           "BTC:            bc1q9vmhw452sy3vu3qsymgtd5zyxecqp6smy505x6 \n")
           
'''
MULTICOIN PORTFOLIO BALANCER - USDT

I'm not a position trading bot. 
I'm just a bot that buys low and sells high on every context and on up to 10 coins, 
helping you balance and your portfolio and optimize the value of your holdings.

I can start just with the quoted asset balance and I'll help you buy better and fill up your portfolio with
the desired HODL amounts. Or I can start buying and selling the assets already in your porftolio if you 
already hold these coins.

I use an algorithm to identify RSI valleys and peaks and also use Bollinger Bands
to calculate signal strength. I try to buy and sell weighted amounts according to the strength of the signal,
tweaked by your settings.

You can set default settings for all coins, and individual parameters for the coins you wish to be special.

You can set, for example:
- Percent of your total balance that you want to use as base value to buy and sell
- Minimum holding value or amount that you wish to have for each coin. I won't sell if below that.
- Tresholds and limits on how strong has the signal to be to create orders 
- Multipliers that increase or decrease buy and sell, so you can buy always more (1.1) and sell less (0.9)
- Trailing settings to try to hit the very top and bottom of the wicks :D
- and a lot more!

The default settings work better with a portfolio of up to $3000. You should increase BASE_INV Percentage for bigger balances.

Note that 'balance' and 'portfolio' refers to the value you have allocated ONLY on THESE 10 coins plus your liquidity! (Other coins in your account will be ignored)

If you feel like buying me a beer, look for the tip jar above :)

One more thing:
I'm not financial advisor ;)

'''

# MAIN PARAMETERS ENUMERATION AND DESCRIPTION (DON'T EDIT THIS. SET ALL PARAMETERS AFTER LINE 80)

#                     BASE_INV   B_ADD  S_ADD  B_MULT   S_MULT   B_RSI_TOL  B_BB_TOL  B_TOL  S_RSI_TOL   S_BB_TOL   S_TOL
# EXAMPLE PARAMS =  [  0.015,     0,      0,     1.1,    0.9,      0.5,     0.998,    0.6,    0.5,       1.002,     0.6]

# MAIN PARAMETERS DESCRIPTION AND ENUMERATION (DON'T EDIT)

# Base investment (unweighted) per order for this coin in Equity %
# Additional value or multiplier for orders (use example: sell less than buy with BUY_MULT = 1.1 and SELL_MULT  = 0.8
BASE_INV, BUY_ADD, SELL_ADD, BUY_MULT, SELL_MULT = [0,1,2,3,4]
# Signal Strength Tolerances for BUY and SELL (RSI, BB and Combined)
BUY_RSI_TOL, BUY_BB_TOL, BUY_TOL, SELL_RSI_TOL, SELL_BB_TOL, SELL_TOL = [5,6,7,8,9,10] 

# TRAILING PARAMETERS
#                      TR_PRICE_B  TR_PRICE_S  TR__STOP_B  TR_STOP_S  WICK_B  WICK_S   WICK_INV            
# EXAMPLE TRAILING  =  [ 0.97,    1.03,         0.03,      0.03,        0.97,   1.03,    0.012  ]

# Trailing Orders Trigger Price multipliers, and Trailing Stop % 
TR_PRICE_BUY, TR_PRICE_SELL, TR_STOP_BUY, TR_STOP_SELL = [0,1,2,3]
# [NOT ENABLED YET] Try Buy/Sell at the wicks: percent up or down for triggering trailing orders (zero = no buy) and investment value 
WICK_BUY, WICK_SELL, WICK_INV = [4,5,6]

# LIMITS
#                     MIN_HOLD_V  MAX_HOLD_V  MIN_HOLD_U  MAX_HOLD_U  MIN_BUY   MAX_BUY   MIN_SELL  MAX_SELL  MIN_SELL_PR    MAX_BUY_PR
# EXAMPLE LIMITS  =  [  50,         1000,        -1,          -1,         11,      100,      -11,      -100,      -1,            -1     ]

# Mininum and Maximum Hold Value (USD) or Units (coin units)
# - It will not buy or sell if below/above any of these limits (-1 = no limit)
MIN_HOLD_V, MAX_HOLD_V, MIN_HOLD_U, MAX_HOLD_U = [0,1,2,3]
# Minimum and Maximum order values regardless of signal strength (ex. MIN_BUY $11 to avoid MIN_NOTIONAL errors or MAX_BUY $300 to avoid excessive signal strenght)
MIN_BUY, MAX_BUY, MIN_SELL, MAX_SELL = [4,5,6,7]
# [NOT ENABLED YET] don't sell below or buy above these prices
MIN_SELL_PRICE, MAX_BUY_PRICE = [8,9]


# SETTINGS AND MAIN CODE ---------------------------------------------------------

# TRADING PAIRS (AT LEAST ONE SYMBOL PER GROUP)

SYMBOL_GROUP_1 = ["BTCUSDT","ETHUSDT","BNBUSDT","LINKUSDT","ATOMUSDT"]
SYMBOL_GROUP_2 = ["SOLUSDT","INJUSDT","VETUSDT","YFIUSDT","THETAUSDT"]

# INITIALIZATION 

def initialize(state):

    print("--------------------------------------------------------------------")
    print(TITLE + " / " + VERSION)
    print(AUTHOR)
    print(DONATE)
    print("--------------------------------------------------------------------")
         
    state.number_offset_trades = 0;
    state.bbres_last = {}
    state.orders = {}
    state.signals = {}
    state.fine_tuning = {}
    state.params = {}
    state.tr_params = {}
    state.limits = {}

    # QUOTE BALANCE HOLD (Keep liquidity reserve in quote coin. Don't spend when balance is below this amount)
    # Set this carefully, specially when trading with BTC or other crypto as quote asset, so you grant your desired holdings.
    state.min_liquidity_hold = 50

    # MAIN PARAMETERS (Edit default and/or create specific parameters for each pair)
    
    #                              BASE_INV   B_ADD  S_ADD  B_MULT   S_MULT   B_RSI_TOL  B_BB_TOL  B_TOL  S_RSI_TOL   S_BB_TOL   S_TOL
    state.params["DEFAULT"]  =    [  0.02,     0,      0,     1.1,    0.9,      0.5,     0.998,    0.6,    0.5,       1.002,     0.6]
    #state.params["BTCUSDT"]  =   [  0.02,     0,      0,     1.1,    0.9,      0.5,     0.998,    0.6,    0.5,       1.002,     0.6]

    # TRAILING PARAMETERS
    #                              TR_PR_B  TR_PR_S    TR_ST_B    TR_ST_S     WICK_U    WICK_D  WICK_INV
    state.tr_params["DEFAULT"] =   [ 0.02,    0.02,      0.01,     0.01,        0.97,   1.03,    0.012  ]
    #state.tr_params["BTCUSDT"] =  [ 0.02,    0.02,      0.01,     0.01,        0.97,   1.03,    0.012  ]
    
    # LIMITS 
    #                               MIN_HOLD_V  MAX_HOLD_V  MIN_HOLD_U MAX_HOLD_U MIN_BUY MAX_BUY   MIN_SELL MAX_SELL MIN_SELL_PR MAX_BUY_PR
    state.limits["DEFAULT"]  =     [  -1,         -1,          -1,       -1,      11,      150,      -11,      -150,      0,        0      ]

    state.limits["BTCUSDT"]  =     [  1500,       -1,        0.025,     -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["ETHUSDT"]  =     [  1000,       -1,        0.4,       -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["BNBUSDT"]  =     [  400,        -1,        0.7,       -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["LINKUSDT"]  =    [  150,        -1,        -1,        -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["ATOMUSDT"]  =    [  150,        -1,        -1,        -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["SOLUSDT"]  =     [  50,         -1,        -1,        -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["INJUSDT"]  =     [  50,         -1,        -1,        -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["VETUSDT"]  =     [  50,         -1,        -1,        -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["YFIUSDT"]  =     [  100,        -1,        -1,        -1,      11,      150,      -11,      -150,      0,         0      ]
    state.limits["THETAUSDT"]  =   [  50,         -1,        -1,        -1,      11,      150,      -11,      -150,      0,         0      ]
      




#  ------------------- BOT RUN  ----------------------------------


#   ------------- SCHEDULE GROUP 1 -------------------------------

@schedule(interval="1h", symbol=SYMBOL_GROUP_1, window_size = 200)
def process_group_1(state, data):
    portfolio = query_portfolio()
    print("Current Portfolio Value: "+str(query_portfolio_value()))

    try:
        for symbol_x in data.keys():
            handler_main(state, data[symbol_x])
    except TypeError:
        handler_main(state,data)

    if state.number_offset_trades < portfolio.number_of_offsetting_trades:
        
        pnl = query_portfolio_pnl()
        print("-------")
        print("Accumulated Pnl of Strategy: {}".format(pnl))
        
        offset_trades = portfolio.number_of_offsetting_trades
        number_winners = portfolio.number_of_winning_trades
        print("Number of winning trades {}/{}.".format(number_winners,offset_trades))
        print("Best trade Return : {:.2%}".format(portfolio.best_trade_return))
        print("Worst trade Return : {:.2%}".format(portfolio.worst_trade_return))
        print("Average Profit per Winning Trade : {:.2f}".format(portfolio.average_profit_per_winning_trade))
        print("Average Loss per Losing Trade : {:.2f}".format(portfolio.average_loss_per_losing_trade))
        # reset number offset trades
        state.number_offset_trades = portfolio.number_of_offsetting_trades



#   ------------- SCHEDULE GROUP 2 ------------------------------

@schedule(interval="1h", symbol=SYMBOL_GROUP_2, window_size = 200)
def process_group_2(state, data):
    portfolio = query_portfolio()

    try:
        for symbol_x in data.keys():
            handler_main(state, data[symbol_x])
    except TypeError:
        handler_main(state,data)

    if state.number_offset_trades < portfolio.number_of_offsetting_trades:
        
        pnl = query_portfolio_pnl()
        print("-------")
        print("Accumulated Pnl of Strategy: {}".format(pnl))
        
        offset_trades = portfolio.number_of_offsetting_trades
        number_winners = portfolio.number_of_winning_trades
        print("Number of winning trades {}/{}.".format(number_winners,offset_trades))
        print("Best trade Return : {:.2%}".format(portfolio.best_trade_return))
        print("Worst trade Return : {:.2%}".format(portfolio.worst_trade_return))
        print("Average Profit per Winning Trade : {:.2f}".format(portfolio.average_profit_per_winning_trade))
        print("Average Loss per Losing Trade : {:.2f}".format(portfolio.average_loss_per_losing_trade))
        # reset number offset trades
        state.number_offset_trades = portfolio.number_of_offsetting_trades


# --------------- MAIN HANDLER ---------------------------


def handler_main(state, data):
    symbol = data.symbol
    if symbol is None:
        return 

    try:
        params = state.params[symbol]
    except KeyError:
        params = state.params["DEFAULT"]
    try:
        tr_params = state.tr_params[symbol]
    except KeyError:
        tr_params = state.tr_params["DEFAULT"]
    try:
        limits = state.limits[symbol]
    except KeyError:
        limits = state.tr_params["DEFAULT"]
    

    # BOLLINGER BANDS 

    bb_period = 20
    bb_std_dev_mult = 2
    bbands = data.bbands(bb_period, bb_std_dev_mult)

    # on erroneus data return early (indicators are of NoneType)
    if bbands is None:
        return
    
    # get bbands
    bbands_middle = bbands["bbands_middle"][-1]
    bbands_lower =  bbands["bbands_lower"][-1]
    bbands_upper =  bbands["bbands_upper"][-1]
    
    # RSI PEAKS AND VALLEYS

    # get last 3 candles' RSI(14) 
    rsi3 = data.rsi(14)[0]
    rsi2 = data.rsi(14)[-1]
    rsi1 = data.rsi(14)[-2]

    # find average RSI in trend from RSI(180)
    rsi_avg = data.rsi(180)[-1] # use the middle (peak) rsi (best so far?)

    # on erronous data return early (indicators are of NoneType)
    if rsi1 is None or rsi2 is None or rsi3 is None or rsi_avg is None:
        return

    #old method
    #rsi_str = abs((rsi2 - rsi_avg) * 0.1)
    
    # calculate rsi strength from peak in RSI14 and distance to RSI180 (trend average) 
    rsi_mid = (rsi1+rsi2+rsi3)/3
    rsi_str = abs((rsi_mid - rsi_avg) * 0.1) 

    # BASE INVESTMENT (% OF EQUITY)

    # get portfolio (NOTE: includes only balances of the trading coins in this bot)
    port = query_portfolio()
    port_value = query_portfolio_value()

    buy_value  = float(port_value) * params[BASE_INV]
    sell_value = float(port_value) * params[BASE_INV] * -1
    
    # get current asset price and balance
    current_price = data.close_last
    asset = symbol_to_asset(data.symbol)
    asset_balance = query_balance(asset)
    asset_total_units = asset_balance.free + asset_balance.locked
    asset_total_value = float(asset_total_units) * current_price
    available_liquidity = port.excess_liquidity_quoted 

    # Don't spend below minimum hold of quote asset
    low_liquidity = available_liquidity < state.min_liquidity_hold
     
     # Calculate max and min allowed holdings in units and usd value
    buy_out_of_range = False
    if limits[MAX_HOLD_U] is not -1 and asset_total_units > limits[MAX_HOLD_U]:
        buy_out_of_range = True 
    if limits[MAX_HOLD_V] is not -1 and asset_total_value > limits[MAX_HOLD_V]:
        buy_out_of_range = True 

    sell_out_of_range = False
    if limits[MIN_HOLD_U] is not -1 and asset_total_units < limits[MIN_HOLD_U]:
        sell_out_of_range = True 
    if limits[MIN_HOLD_V] is not -1 and asset_total_value < limits[MIN_HOLD_V]:
        sell_out_of_range = True

    # Main signal conditions for BUY

    if rsi2 < rsi_avg - 3 and rsi2 < rsi1 and rsi2 < rsi3 and rsi_str > params[BUY_RSI_TOL] and current_price * params[BUY_BB_TOL] < bbands_lower:
        # BUY RSI SIGNAL

        #calculate strength of bbands breakout (exponential ^ 10)
        bbands_str = (float(bbands_lower)/current_price) ** 10
        buy_str = bbands_str * rsi_str

        print("+",
              "BUY SIGNAL: " + data.symbol + "   STRENGTH: " + str(buy_str) + "   ( RSI STR: " + str(rsi_str) + "    BB STR: " + str(bbands_str) + " ) ",
              "....RSI: " + str(rsi2) + " RSI AVG: " + str(rsi_avg))

        if buy_str > params[BUY_TOL] and not buy_out_of_range and not low_liquidity:
            # add weight and user modifications, up to maximum allowed
            buy_value = min(buy_value * buy_str * params[BUY_MULT] + params[BUY_ADD], limits[MAX_BUY])
            # set to minimum if value is below minimum
            buy_value = max(buy_value, limits[MIN_BUY])

            if buy_value > 22:
                # split in two orders with different trailing settings
                print("......(SPLIT ORDERS)")
                order_trailing_iftouched_value(symbol=data.symbol, value=buy_value*0.5, 
                    trailing_percent = tr_params[TR_STOP_BUY], 
                    stop_price = float(current_price * (1+tr_params[TR_PRICE_BUY])))
                # more tight trailing (almost market?)
                order_trailing_iftouched_value(symbol=data.symbol, value=buy_value*0.5, 
                    trailing_percent = 0.002, 
                    stop_price = float(current_price * 0.995))
            else:
                # Trailing Buy Order
                order_trailing_iftouched_value(symbol=data.symbol, value=buy_value, 
                    trailing_percent = tr_params[TR_STOP_BUY], 
                    stop_price = float(current_price * (1-tr_params[TR_PRICE_BUY])))

            # Log
            print(".....Asset Balance:   " + str(asset_total_units) + " " + asset + " (~ " + str(asset_total_value)+" USD)")
            print(".....Current Price:   " + str(current_price),
                  ".....Trailing Buy:    " + str(buy_value) + " Trailing %: " + str(tr_params[TR_STOP_BUY]) + " Trigger Price: "+ str(float(current_price * (1- tr_params[TR_PRICE_BUY]))))    
        elif buy_out_of_range:
            print(".....Asset Balance:   "+ str(asset_total_units) + " " + asset + " (~ " + str(asset_total_value)+" USD)",
                  ".....x    NO BUY: ASSET ABOVE MAXIMUM HOLD")
        elif low_liquidity:
            print(".....Available Liquidity: " + str(available_liquidity) +
                "\n.....x    NO BUY: LOW LIQUIDITY" )
        else:
            print(".....x    NO BUY (WEAK SIGNAL)")

        print(".")

    # Main signal conditions for SELL

    elif rsi2 > rsi_avg + 3 and rsi2 > rsi1 and rsi2 > rsi3 and rsi_str > params[BUY_RSI_TOL] and current_price * params[SELL_BB_TOL] > bbands_upper:
        #SELL RSI SIGNAL

        #calculate strength of bbands breakout (exponential ^ 10)
        bbands_str = (current_price/float(bbands_upper)) ** 10
        sell_str = bbands_str * rsi_str

        print("-",
              "SELL SIGNAL: " + data.symbol + "   STRENGTH: " + str(sell_str) + "   ( RSI STR: " + str(rsi_str) + "    BB STR: " + str(bbands_str) + " ) ",
              "......RSI: " + str(rsi2) + " RSI AVG: " + str(rsi_avg))
              
        if sell_str > params[SELL_TOL] and not sell_out_of_range:
            # add weight and user modifications, up to maximum allowed
            sell_value = max(sell_value * sell_str * params[SELL_MULT] + params[SELL_ADD], limits[MAX_SELL])
            # set to minimum if value is below minimum
            sell_value = min(sell_value, limits[MIN_SELL])

            if sell_value > 22:
                print("......(SPLIT ORDERS)")
                # split in two orders with different trailing settings
                order_trailing_iftouched_value(symbol=data.symbol, value=sell_value*0.5, 
                    trailing_percent = tr_params[TR_STOP_SELL], 
                    stop_price = float(current_price * (1+tr_params[TR_PRICE_SELL])))
                # more tight trailing (almost market?)
                order_trailing_iftouched_value(symbol=data.symbol, value=sell_value*0.5, 
                    trailing_percent = 0.002, 
                    stop_price = float(current_price * 1.005))
            else:
                # Trailing Sell Order
                order_trailing_iftouched_value(symbol=data.symbol, value=sell_value, 
                    trailing_percent = tr_params[TR_STOP_SELL], 
                    stop_price = float(current_price * (1+tr_params[TR_PRICE_SELL])))

            # Log
            print("......Asset Balance:   "+ str(asset_total_units) + " "+ asset + " (~ " + str(asset_total_value)+" USD)",
                  "......Current Price:   " + str(current_price),
                  "......Trailing Sell:   " + str(sell_value) + " Trailing %: " + str(tr_params[TR_STOP_SELL]) + " Trigger Price: "+ str(float(current_price * (1+tr_params[TR_PRICE_SELL]))))      
        elif sell_out_of_range:
            print("......Asset Balance:   "+ str(asset_total_units) + " " + asset + " (~ " + str(asset_total_value)+" USD)")
            print("......x    NO SELL: ASSET BELOW MINIMUM HOLD")
        else:
            print("......x    NO SELL: WEAK SIGNAL")

        print(".")

    # ORDER TIMEOUT -----------------------

    orders = query_open_orders()
    hour = 3600
    current_time = get_timestamp() * 0.001
    timeout = 48

    for order in orders:
        # cancel old pending orders by x*hour
        order_time = order.created_time * 0.001
    
        # Cancel pending orders older than (timeout)
        if order.status is OrderStatus.Pending and current_time - order_time > timeout*hour:
            print("x           Cancelling Order: " + order.symbol,
                  "......       Order Time:       " + str(datetime.datetime.fromtimestamp(order_time)),
                  "......       Current Time:     " + str(datetime.datetime.fromtimestamp(current_time)),
                  "......       Order Age in H:   " + str((current_time - order_time)/3600))
            cancel_order(order.id)
