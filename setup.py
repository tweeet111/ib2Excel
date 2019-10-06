# Setup variables for ib2Excel

# Insert TWS or TWS Gateway API port - see configurations
tws_port = 7496

# Setup relevant chains and strikes
min_dte=120       # chains below are not updated
max_dte=160       # chains above are not updated
strike_distance= 25 # only update strikes divisible by value (25, 10, 50)
upper_strike_range= 0.1   # only update strikes up  from current SPX spot (e.g. + 50%)
lower_strike_range= 0.5  # only update strikes  down from current SPX spot (e.g. -50% )

# update interval in seconds
wait_openpos = 0.1
wait_data = 300

# Excel workbook name
#workbook = 'Backtest_software_v0.069.xlsm'
workbook = "live_example5.xlsb"
stream2tab = "DATA" # "FM_FEED"