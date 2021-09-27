import datetime

TITLE   = "MULTICOIN ACCUMULATOR - USDT"
VERSION = "VERSION 0.1"
AUTHOR  = "Created by @elerouxx in 2021-06-20 | Last Update 2021-09-27"
DONATE  = ("TIP JAR WALLET:  \n" +  
           "ERC20 / BEP20:  0xA44dc8782d13f7728E7ec240D8dA99479d245c3C \n" +
           "BTC:            bc1q9vmhw452sy3vu3qsymgtd5zyxecqp6smy505x6 \n")
           
'''
MULTICOIN ACCUMULATOR - USDT

A Trality bot coded in Python. 
This is not a regular position trade bot. There's no Stop Loss or any other traditional risk management strategy.
It should only be used to try to 'buy the dip' and 'sell the top' on assets intended to hold and swing long term.

HIGHLIGHTS:
* The bot detects RSI turnarounds in user defined RSI zones, and custom Bollinger Band breakouts.
* RSI buy/sell zones and upper/lower bbands can be adjusted globally or individually for each asset.
* The bot calculates signal strength from both RSI and BB breakouts and tries to buy or sell more when the signal is stronger.
* Custom bollinger lines and RSI buy/sell zones will be ploted in Trality Symbol charts for easy visualization and refining.
* SPLIT ORDERS: The bot can split the signal in different orders. Each order has its own parameters.
    - For example, you can set 50% of the purchase to a limit order and 50% to a trailing order. 
    (Or two trailing orders with different parameters for comparison purposes.)
* Other parameters that can be set for each asset include:
    - Minimum and maximum values to hold in portfolio (don't sell or buy if beyond these limits)
    - Modifiers to tweak buy and sell volumes(for example, buy more and sell less to accumulate an asset)
    - Split order parameters (trailing, etc) also can be set up individually for each pair.

KNOWN ISSUES: 
* Since the code can split orders, it might create buy orders with no liquidity to fill, or sell orders with not enough asset to sell. 
  This can sometimes generate non working orders that should be ignored.
 
'''


# MAIN PARAMETERS ENUMERATION (DON'T EDIT)
INV_PERC, INV_VAL, BUY_ADD, SELL_ADD, BUY_MULT, SELL_MULT = [0,1,2,3,4,5]
BUY_RSI_TOL, BUY_BB_TOL, BUY_TOL, SELL_RSI_TOL, SELL_BB_TOL, SELL_TOL = [5,6,7,8,9,10] 
SPLIT, TRAIL, TR_PRICE_BUY, TR_PRICE_SELL, TR_STOP_BUY, TR_STOP_SELL = [0,1,2,3,4,5]
MIN_HOLD_V, MAX_HOLD_V, MIN_HOLD_A, MAX_HOLD_A = [0,1,2,3]
MIN_BUY, MAX_BUY, MIN_SELL, MAX_SELL = [4,5,6,7]
MAX_BUY_PRICE, MIN_SELL_PRICE = [8,9]
# signal parameter constants
BB_LEN,  LOW_MULT, LOW_ADD, UP_MULT, UP_ADD, BUY_RSI,  BUY_RSI_SHARP,  SELL_RSI,  SELL_RSI_SHARP = [0,1,2,3,4,5,6,7,8]
# order parameter constants
PERC, TYPE,  B_PRICE,  S_PRICE,  B_TR_PERC,  S_TR_PERC = [0,1,2,3,4,5]
MARKET, LIMIT, TRAIL = [0,1,2]
# human friendly parameter constants 
NO = -1

# ┌───────────────────────────────────────────────────────────────┐
# │        MAIN SETTINGS (TRADING PAIRS AND TIME FRAMES)          │
# └───────────────────────────────────────────────────────────────┘
# Trading Pairs divided in 2 schedules, since each supports up to 10 pairs.
# (Or you can use the same pairs with a different interval below) 
# MUST have at least one pair in each group

symbol_group_1 = ["BTCUSDT","ETHUSDT","ADAUSDT","DOTUSDT","SOLUSDT"]
symbol_group_2 = ["LUNAUSDT","NEARUSDT","FTTUSDT","AVAXUSDT","ATOMUSDT"]

# (quick override for fast test/refine)
# symbol_group_1 = ["BTCUSDT"]
# symbol_group_2 = ["LUNAUSDT"]

# Can use different intervals in each schedule/group (supported intervals: 1m 5m 15m 30m 1h 6h 12h 1d)
interval_1 = "6h"
interval_2 = "6h"

# Order timeout in hours
order_timeout = 24

# Window size for data retrieval (edit if getting errors when using very long indicator periods)
window_size_1 = 80
window_size_2 = 80

# ┌─────────────────────────────────────────────────────────┐
# │           INITIALIZATION AND PARAMETER SETUP            │
# └─────────────────────────────────────────────────────────┘

def initialize(state):

    log_message=("\n--------------------------------------------------------------------\n" +
        TITLE + " / " + VERSION + "\n" +
        AUTHOR + "\n" + DONATE +
        "\n--------------------------------------------------------------------\n\n")
         
    print(log_message)
    log(log_message,0)

    state.number_offset_trades = 0;
    state.bbres_last = {}
    state.orders = {}
    state.signals = {}
    state.fine_tuning = {}
    state.params = {}
    state.signal_params = {}
    state.tr_params = {}
    state.limits = {}
    state.order_params = {}
    state.hold_params = {}

    # Minimum Liquidity (Quote asset) to keep
    state.min_liquidity_hold = 100   # (Don't buy when Liquidity is below this value)
    state.min_notional = 11          # (Minimum operation in Binance- now unused)

    # MAIN PARAMETERS:
    # Set base investment, which will be adjusted according with signal weight.
    # INV_PERC is a % of equity (total allocation on these pairs + quote, ex. 10%)
    # INV_VAL is a fixed value in quote coin (ex. $100) - NOTE: if INV_VAL is set, it takes priority and INV_PERC is ignored. 
    # Set MULTiplier and ADD to your buy and sell, accordingly to your strategy, for example, if you want to buy more and sell less in order to accumulate.

    #                           ┌───────── investment base percent and modifiers ────────┐ 
    #                           INV_PERC  INV_VAL*  BUY_ADD  SELL_ADD  BUY_MULT  SELL_MULT  
    state.params["DEFAULT"]  =  [   2,      NO,        0,       0,      1.2,       0.8   ]
    state.params["BTCUSDT"]  =  [   3,      NO,        0,       0,      1.2,       0.6   ]

    # SIGNAL PARAMETERS:     
    # Bollinger Bands: set LEN, MULT (contract and expand) and ADD (raise or lower) to tweak lower and upper bands.
    # Breaking the bands on close will trigger BB buy or sell signals accordingly
    # RSI: set Buy maximum and Sell minimum RSI values. A RSI TURNAROUND (valley or peak) beyond these values will trigger a RSI signal.
    # RSI sharp: a higher value will require a more "pointy" RSI turnaround (i.e. a sharper 'V' in the RSI graph to trigger buy signal)

    #                                 ┌───── custom bollinger buy/sell bands ───┐   ┌────── rsi buy/sell zones and sharpness ──────────┐
    #                                  BB_LEN  LOW_MULT  LOW_ADD  UP_MULT  UP_ADD     BUY_RSI  BUY_RSI_SHARP  SELL_RSI  SELL_RSI_SHARP
    state.signal_params["DEFAULT"] =  [  40,     1.9,       2,      2,       3,         30,          0.5,         70,        0.5       ]
    state.signal_params["BTCUSDT"] =  [  40,     1.8,       2,      2,       3,         35,          0.3,         75,        0.3       ]
    

    # ORDER PARAMETERS:
    # Allows split orders with different types/parameters - for scaled buy/sell, or result comparison
    # PERC is percent of investment to buy/sell (ex. 50/50 splits the buy in half, 100/100 doubles the buy)
    # (TIP: you can set slightly different PERC (ex. 50 and 51) to be able to identify and compare the executed orders.
    # TYPE can be LIMIT, TRAIL. (*MARKET ORDERS NOT IMPLEMENTED YET) 
    # B_PRICE and S_PRICE are % values related to current price (i.e. '-2' sets order price to 2% BELOW current price).
    # B_TR_PERC and S_TR_PERC are percent values for trailing orders [positive 0-100]. Not used for other types.
     
    #                                 ┌────────────────────── order A ───────────────────┐   ┌─────────────────── order B ────────────────────────┐ ┌─── etc.
    #                                   PERC  TYPE  B_PRICE  S_PRICE  B_TR_PERC  S_TR_PERC    PERC   TYPE   B_PRICE  S_PRICE  B_TR_PERC  S_TR_PERC 
    state.order_params["DEFAULT"] =  [[ 50,   LIMIT,  0.05,   -0.05,       NO,       NO   ], [ 51,   TRAIL,   0.5,     -0.5,     1.5,       1.5    ] ]
    state.order_params["BTCUSDT"] =  [[ 50,   TRAIL,  0.05,   -0.05,        2,        2   ], [ 51,   TRAIL,   -0.5,     0.5,     2,           2    ] ]

    # HOLD PARAMETERS:
    # min and max values or amounts (whichever comes first) to hold for each asset. It won't sell below min or buy above max.
    # min and max buy/sell values despite signal strength. It will cap the order value to these limits.
    # min and max prices. It won't sell below or buy above specified prices.

    #                              ┌──── min and max val/amount to HODL ────────┐   ┌───────────  min and max buy/sell values and prices  ────────────┐
    #                              MIN_HOLD_V  MAX_HOLD_V  MIN_HOLD_A  MAX_HOLD_A   MIN_BUY  MAX_BUY  MIN_SELL  MAX_SELL  MAX_BUY_PRICE  MIN_SELL_PRICE
    state.hold_params["DEFAULT"] = [ NO,        NO,         NO,         NO,            11,    300,      11,      300,          NO,           NO        ]
    state.hold_params["BTCUSDT"] = [ NO,        NO,        0.01,        NO,            11,    300,      11,      300,        42000,         50000      ]


# ┌────────────────────────────────────────┐
# │               SCHEDULES                │
# └────────────────────────────────────────┘

# SCHEDULE GROUP 1

@schedule(interval=interval_1, symbol=symbol_group_1, window_size = window_size_1)
def process_group_1(state, data):
    portfolio = query_portfolio()
    available_liquidity = portfolio.excess_liquidity_quoted
    print("Current Portfolio Value: "+str(query_portfolio_value()) + " USD | Available Funds: "+ str(available_liquidity) + " USD") 
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
        all_balances = query_balances()
        for balance in all_balances:
            print("$"+balance.asset+" "+ str(balance.free+balance.locked))

#  SCHEDULE GROUP 2

@schedule(interval=interval_2, symbol=symbol_group_2, window_size = window_size_2)
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
        all_balances = query_balances()
        for balance in all_balances:
            print("$"+balance.asset+" "+ str(balance.free+balance.locked))



# ┌─────────────────────────────────────────────────┐
# │          MAIN HANDLE (Actual Bot Code)          │
# └─────────────────────────────────────────────────┘


def handler_main(state, data):
    symbol = data.symbol
    if symbol is None:
        return 

    try:
        params = state.params[symbol]
    except KeyError:
        params = state.params["DEFAULT"]
    try:
        signal_params = state.signal_params[symbol]
    except KeyError:
        signal_params = state.signal_params["DEFAULT"]
    try:
        order_params = state.order_params[symbol]
    except KeyError:
        order_params = state.order_params["DEFAULT"]
    try:
        hold_params = state.hold_params[symbol]
    except KeyError:
        hold_params = state.hold_params["DEFAULT"]
        

    # RSI 'TURNAROUND' signal calculation

    # get RSI of last 3 bars
    rsi3 = data.close.rsi(14)[0]
    rsi2 = data.close.rsi(14)[-1]
    rsi1 = data.close.rsi(14)[-2]

    # on erronous data return early (indicators are of NoneType)
    if rsi1 is None or rsi2 is None or rsi3 is None:
        return

    # rsi middle (50) set to a variable for later use. (find a movable center that helps working with divergences)
    # rsi_middle = 50

    # RSI signal: when last 3 bars rsi form a turnaround (V shape for buy, a 'peak' for sell)
    rsi_buy_signal = rsi2 <= signal_params[BUY_RSI] and rsi2 + signal_params[BUY_RSI_SHARP] < rsi1 and rsi2 + signal_params[BUY_RSI_SHARP] < rsi3
    rsi_sell_signal = rsi2 >= signal_params[SELL_RSI] and rsi2 - signal_params[SELL_RSI_SHARP] > rsi1 and rsi2 - signal_params[SELL_RSI_SHARP] > rsi3
    
    # RSI strength: how far beyond buy and sell rsi settings. 
    # Example: if RSI_BUY set to 30, signal weight would be 1.0 at RSI 30, 1.33 at RSI 20 and 2.0 (max) at RSI zero. This weight will be used to increase or decrease investment.
    rsi_buy_strength = 1 + (signal_params[BUY_RSI] - rsi2 ) / max(signal_params[BUY_RSI], 0.01)
    rsi_sell_strength = 1 + (rsi2 - signal_params[SELL_RSI]) / (100 - min(signal_params[SELL_RSI], 0.99))

    # some debug logs
    '''
    if rsi_buy_signal:
        print ("RSI BUY SIGNAL - rsi1: " + str(rsi1) + " rsi2: " + str(rsi2) + " rsi3: "+ str(rsi3))   
    if rsi_sell_signal:
        print ("RSI SELL SIGNAL - rsi1: " + str(rsi1) + " rsi2: " + str(rsi2) + " rsi3: "+ str(rsi3))
    '''


    # plot rsi and buy/sell zones 
    # Stragegy note: look for a formula to better detect divergences
    # - (probably some kind of inverse price oscillator in range 0-100 that adds/multiplies to the RSI would help testing this)
    with PlotScope.group("rsi", data.symbol):
        plot_line("buy rsi zone", signal_params[BUY_RSI])
        plot_line("sell rsi zone", signal_params[SELL_RSI])
        plot_line("rsi", rsi2)
        #plot_line("rsi_avg", rsi_avg)

    # CUSTOM BOLLINGER BAND signal calculation

    bbands_length = signal_params[BB_LEN]
    # separate multipliers for upper and lower band (lowering value shrinks/contracts the band)
    upper_band_mult = signal_params[UP_MULT]
    lower_band_mult = signal_params[LOW_MULT]
    # separate values to be added or substracted (raises and lowers the band)
    # (in % units, taking price as 100%, so this parameter can easily be used with all tokens)
    upper_band_add = signal_params[UP_ADD]  * data.close_last / 100   # ...already did
    lower_band_add = signal_params[LOW_ADD]  * data.close_last / 100    

    sma = data.close.sma(bbands_length)
    stddev   = data.close.stddev(bbands_length)
    
    if sma is None or stddev is None:
        return

    sma_value = sma["sma"][-1]
    stddev_value = stddev["stddev"][-1] 

    # apply user modifiers
    upper_band = (sma_value + (stddev_value * upper_band_mult) + upper_band_add)
    lower_band = (sma_value - (stddev_value * lower_band_mult) + lower_band_add)

    # calculate signals
    # (Calculate breakout on the average price of the candle CLOSE AND WICK)
    bbands_buy_signal = (data.close_last + data.low_last) / 2 < lower_band
    bbands_sell_signal = (data.close_last + data.high_last) / 2 >  upper_band
    # (bband signal strength will be calculated later in buy/sell order processing)

     # plot bands 
    with PlotScope.root(data.symbol):
        plot_line("Upper Band", upper_band)
        plot_line("MA", sma_value)
        plot_line("Lower Band", lower_band)

    # Plotting default bbands just for reference
    # bbands = data.bbands(20,2)


    # BASE INVESTMENT (% of equity for these pairs, or fixed value)

    # get portfolio (NOTE: includes only balances of the trading pairs in this bot plus the quote asset)
    port = query_portfolio()
    port_value = query_portfolio_value()

    if params[INV_VAL] is NO:
        buy_value  = float(port_value) * params[INV_PERC]/100
        sell_value = float(port_value) * params[INV_PERC]/100
    else:
        buy_value = params[INV_VAL]
        sell_value = params[INV_VAL]
    
    # get current asset price and balance
    current_price = data.close_last
    asset = symbol_to_asset(data.symbol)
    asset_balance = query_balance(asset)
    asset_total_units = asset_balance.free + asset_balance.locked
    asset_total_value = float(asset_total_units) * current_price
    available_liquidity = port.excess_liquidity_quoted 

    # Don't spend below minimum hold of quote asset
    low_liquidity = available_liquidity < state.min_liquidity_hold and state.min_liquidity_hold is not NO
   
     # Calculate max and min allowed holdings in units and usd value
    buy_out_of_range = False
    if hold_params[MAX_HOLD_A] is not NO and asset_total_units > hold_params[MAX_HOLD_A]:
        buy_out_of_range = True 
    if hold_params[MAX_HOLD_V] is not NO and asset_total_value > hold_params[MAX_HOLD_V]:
        buy_out_of_range = True

    sell_out_of_range = False
    if hold_params[MIN_HOLD_A] is not NO and asset_total_units < hold_params[MIN_HOLD_A]:
        sell_out_of_range = True 
    if hold_params[MIN_HOLD_V] is not NO and asset_total_value < hold_params[MIN_HOLD_V]:
        sell_out_of_range = True


    # BUY SIGNALS EXECUTION

    if rsi_buy_signal and bbands_buy_signal:
        # calculate strength of bbands breakout
        bbands_str = (float(lower_band)/current_price)
        # calculate overall signal strength
        buy_str = bbands_str * rsi_buy_strength

        print("+",
              "BUY SIGNAL: " + data.symbol + " STRENGTH: " + str(buy_str) 
              + "( RSI BUY STR: " + str(rsi_buy_strength) + " BB STR: " + str(bbands_str) + ")")

        if not buy_out_of_range and not low_liquidity:
            
            # add weight and user modifications
            buy_value = buy_value * buy_str * params[BUY_MULT] + params[BUY_ADD]

            # debug log for current asset balance/status 
            print(".....Asset Balance: " + str(asset_total_units) + " " + asset + " (~ " + str(asset_total_value)+" USD)" 
               + " Current Price: " + str(current_price))

            # loop thru the defined order parameters 2-dimensional array
            for order in order_params:
                # Skip if order disabled
                if order[PERC] <= 0:
                    continue
                # Calculate order volume and cap to min and max order values
                order_value = min(buy_value * order[PERC]/100, hold_params[MAX_BUY])
                order_value = max(order_value, hold_params[MIN_BUY])

                if order_value + state.min_liquidity_hold > available_liquidity:
                    print("order value (" + str(order_value) + ") will hit minimum liquidity (" + str(available_liquidity)+ ")  - NO BUY")
                    break

                if hold_params[MAX_BUY_PRICE] is not NO and current_price > hold_params[MAX_BUY_PRICE]:
                    print("current price higher than " + str(hold_params[MAX_BUY_PRICE]) + " - NO BUY")
                    break

                if order[TYPE] is TRAIL:
                    print("processing trailing order with parameters " + str(order))
                    # calculate trailing parameters 
                    stop_price = float(current_price * (1 + order[B_PRICE]/100))
                    trailing_percent = float(order[B_TR_PERC]/100)
                    # issue order and log
                    order_trailing_iftouched_value(symbol=data.symbol, value=order_value, trailing_percent=trailing_percent, stop_price=stop_price)
                    print(".....TRAILING BUY: " + str(order_value) + " Trailing %: " + str(trailing_percent) + " Trigger Price: "+ str(float(stop_price)))
                    
                elif order[TYPE] is LIMIT:
                    print("processing limit order with parameters " + str(order))
                    #calculate limit price
                    limit_price = float(current_price * (1 + order[B_PRICE]/100))
                    order_limit_value(symbol=data.symbol, value=order_value, limit_price=limit_price)
                    print("........LIMIT BUY: " + str(order_value) + " Limit Price: " + str(limit_price))

                elif order[TYPE] is MARKET: # not yet implemented 
                    print("process market order with parameters " + str(order) + " - MARKET ORDERS NOT SUPPORTED")
                else:
                    print("unsupported order type: " + str(order[TYPE]))
                
        elif buy_out_of_range:
            print(".....x    NO BUY: ASSET ABOVE MAXIMUM HOLD")
        elif low_liquidity:
            print(".....Available Liquidity: " + str(available_liquidity) +
                "\n.....x    NO BUY: LOW LIQUIDITY" )
        else:
            print(".....x    NO BUY (WEAK SIGNAL OR UNKNOWN REASON)")

        print(".")

    # SELL SIGNALS EXECUTION

    elif rsi_sell_signal and bbands_sell_signal:
        # calculate strength of bbands breakout 
        bbands_str = (current_price/float(upper_band))
        # calculate overall signal strength
        sell_str = bbands_str * rsi_sell_strength

        print("-",
              "SELL SIGNAL: " + data.symbol + "   STRENGTH: " + str(sell_str) 
              + "   ( RSI SELL STR: " + str(rsi_sell_strength) + "    BB STR: " + str(bbands_str) + " ) ") 
              
        if not sell_out_of_range:
            # add signal weight and user modifications
            sell_value = sell_value * sell_str * params[SELL_MULT] + params[SELL_ADD]

            # debug log for asset status
            print(".....Asset Balance: " + str(asset_total_units) + " " + asset + " (~ " + str(asset_total_value)+" USD)" 
               + " Current Price: " + str(current_price))

            # loop thru the defined order parameters 2-dimensional array
            for order in order_params:
                # Skip if order disabled
                if order[PERC] <= 0:
                    continue

                # Calculate order volume and cap to min and max order values
                order_value = min(sell_value * order[PERC]/100, hold_params[MAX_SELL])
                order_value = max(order_value, hold_params[MIN_SELL])

                if order_value > asset_total_value:
                    print("order value (" + str(order_value) + ") higher than current asset value (" + str(asset_total_value)+ ")  - NO SELL")
                    break

                if hold_params[MIN_SELL_PRICE] is not NO and current_price < hold_params[MIN_SELL_PRICE]:
                    print("current price lower than " + str(hold_params[MIN_SELL_PRICE]) + "- NO SELL")
                    break


                if order[TYPE] is TRAIL:
                    print("processing trailing order with parameters " + str(order))
                    # calculate trailing parameters 
                    stop_price = float(current_price * (1 + order[S_PRICE]/100))
                    trailing_percent = float(order[S_TR_PERC]/100)
                    # issue order and log
                    order_trailing_iftouched_value(symbol=data.symbol, value=order_value*-1, trailing_percent=trailing_percent, stop_price=stop_price)
                    print(".....TRAILING SELL: " + str(order_value*-1) + " Trailing %: " + str(trailing_percent) + " Trigger Price: "+ str(float(stop_price)))
                    
                elif order[TYPE] is LIMIT:
                    print("processing limit order with parameters " + str(order))
                    #calculate limit price
                    limit_price = float(current_price * (1 + order[S_PRICE]/100))
                    order_limit_value(symbol=data.symbol, value=order_value*-1, limit_price=limit_price)
                    print("........LIMIT SELL: " + str(order_value*-1) + " Limit Price: " + str(limit_price))

                elif order[TYPE] is MARKET: # not yet implemented 
                    print("process market order with parameters " + str(order) + " - MARKET ORDERS NOT SUPPORTED")
                else:
                    print("unsupported order type: " + str(order[TYPE]))

        elif sell_out_of_range:
            print("......x    NO SELL: ASSET BELOW MINIMUM HOLD")
        else:
            print("......x    NO SELL: WEAK SIGNAL OR UNKNOWN REASON")

        print(".")

    
    # ORDER TIMEOUT

    timeout = order_timeout

    orders = query_open_orders()
    hour = 3600
    current_time = get_timestamp() * 0.001     # (converted from milliseconds to seconds timestamp)
    

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
