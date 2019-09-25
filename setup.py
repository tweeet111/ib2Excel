# Setup variables for ib2Excel

# Insert TWS or TWS Gateway API port - see configurations
tws_port = 7496

# Setup relevant chains and strikes
min_dte=50        # chains below are not updated
max_dte=220       # chains above are not updated
strike_distance= 25 # only update strikes divisible by value (25, 10, 50)
strike_range= 0.4   # only update strikes up or down from current SPX spot (e.g. -50% to + 50%)

# update interval in seconds
wait_openpos = 1
wait_data = 120

# Excel workbook name
#workbook = 'Backtest_software_v0.069.xlsm'
workbook = "live_example2.xlsb"
stream2tab = "DATA" # "FM_FEED"