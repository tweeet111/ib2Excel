from datetime import datetime as dt
import numpy as np
import pandas as pd
import xlwings as xw
from ib_insync import *
from ib_insync.util import isNan
import sys, signal
from setup import *
import time
from pythoncom import com_error
import nest_asyncio




def signal_handler(signal, frame):
	print("closing....")
	ib.disconnect()
	sys.exit(0)

def get_libor_func():
	print('retrieving Libor rates....')
	tables = pd.read_html("https://www.finanzen.net/zinsen/libor/usd")
	df_lib = tables[0]
	df_lib["Kurs"] = pd.to_numeric(df_lib["Kurs"]).div(1000000)
	df_lib.reset_index(inplace=True, drop=True)
	df_lib['Years'] = pd.Series([1 / 365, 7 / 365, 30 / 365, 60 / 365, 90 / 365, 180 / 365, 1],
								index=range(7)).round(3)
	# rfr_func = interp1d(df_lib['Years'], df_lib["Kurs"], fill_value="extrapolate" )

	# format df to fit export format
	df_lib = df_lib[['Name', 'Kurs']]
	df_lib = df_lib.pivot_table(columns='Name', index=None, values='Kurs', aggfunc='first') * 100

	cols = ["Date", "Libor USD Overnight", "Libor USD 1 Woche", "Libor USD 1 Monat", "Libor USD 2 Monate",
			"Libor USD 3 Monate", "Libor USD 6 Monate", "Libor USD 12 Monate"]

	df_lib['Date'] = dt.today().date().strftime('%d.%m.%y')
	df_lib = df_lib[cols]
	return df_lib

def conn_tws(client=np.random.randint(0, 10)):
	i = 0
	while ib.isConnected() == False and i < 20:
		try:
			print("connecting...")
			ib.connect('127.0.0.1', tws_port, clientId=client, timeout=None)  # tws 7496 gateway 4001 (see TWS settings)
			ib.sleep(1)
		except ConnectionRefusedError:
			ib.sleep(3)
			i += 1
	if ib.isConnected():
		print("Connection established")
	else:
		print("Timeout")

def get_tickers(min_dte=30, max_dte=250, strike_distance=25, upper_strike_range=0.2, lower_strike_range=0.5):
	print(30 * '-')
	print ('limit data with this setup: ')
	print('strike intervals: ' + str(strike_distance))
	print ('min dte: ' + str(min_dte))
	print('max dte: ' + str(max_dte))
	print('upper strike range: ' + str(upper_strike_range))
	print('lower strike range: ' + str(lower_strike_range))
	print(30*'-')

	print('getting SPX live...')
	ib.reqMarketDataType(marketDataType=2)
	spx = Index('SPX', 'CBOE')
	ib.qualifyContracts(spx)
	spx_ticker = ib.reqMktData(spx, '', False, False)

	timeout = time.time() + 3
	while spx_ticker.last != spx_ticker.last:
		ib.sleep(0.01)
		if time.time()>timeout:
			spxValue = spx_ticker.close
			break
	if isNan(spx_ticker.last):
		spxValue = spx_ticker.close
	else:
		spxValue = spx_ticker.last


	print(spxValue)

	print('getting chains...')
	chains = ib.reqSecDefOptParams(spx.symbol, '', spx.secType, spx.conId)
	chain_spx = next(c for c in chains if (c.tradingClass == 'SPX' and c.exchange == 'SMART'))
	chain_spxw = next(c for c in chains if (c.tradingClass == 'SPXW' and c.exchange == 'SMART'))
	ib.sleep(1)

	print('combining SPX/SPXW expirations...')
	strikes = [strike for strike in chain_spx.strikes
			   if strike % strike_distance == 0
			   and spxValue - lower_strike_range * spxValue < strike < spxValue + upper_strike_range * spxValue]

	expirations_spx = sorted(exp for exp in chain_spx.expirations)
	# print(expirations_spx)
	expirations_spxw = sorted(exp for exp in chain_spxw.expirations)
	# print (expirations_spxw)

	expirations = expirations_spx + expirations_spxw
	print(expirations)

	print('filtering for min and max dte...')

	dt_dates = [dt.strptime(date, '%Y%m%d') for date in expirations]
	dt_dates = [date for date in dt_dates
				if max_dte > (date - dt.today()).days > min_dte]
	expirations = [d.strftime('%Y%m%d') for d in dt_dates]
	print(expirations)

	# alle Chain Contracts
	print('finding contracts...')
	contracts = [Option('SPX', exp, strike, right, 'SMART')
				 for strike in strikes
				 # for tradingClass in ['SPX','SPXW']
				 for right in ['P', 'C']
				 for exp in expirations
				 ]

	startTime = dt.now()

	ib.qualifyContracts(*contracts)
	contracts = [c for c in contracts if c.conId]
	contracts = list(set(contracts))
	ib.qualifyContracts(*contracts)
	print('number of contracts: ' + str(len(contracts)))
	setupTime = dt.now() - startTime
	print('finished finding contracts in ' + str(setupTime) + 's')
	print('Startup finished!')
	return contracts, spx

def update_price(contracts, spx):

	now = dt.now()

	spx_ticker = ib.reqMktData(spx, '', False, False)
	timeout = time.time() + 3
	while spx_ticker.last != spx_ticker.last:
		ib.sleep(0.01)
		if time.time() > timeout:
			spxValue = spx_ticker.close
			break
	if isNan(spx_ticker.last):
		spxValue = spx_ticker.close
	else:
		spxValue = spx_ticker.last


	print('updating Data tab...')
	tickers = ib.reqTickers(*contracts)
	ib.sleep(3)

	df = pd.DataFrame(columns='STRIKE RIGHT EXPIRATION UNDLY bid ask'.split())

	df['STRIKE'] = [c.strike for c in contracts]
	df['RIGHT'] = [c.right for c in contracts]
	df['EXPIRATION'] = [c.lastTradeDateOrContractMonth for c in contracts]
	df['UNDLY'] = [c.symbol for c in contracts]
	contract2Row = {c: i for (i, c) in enumerate(contracts)}
	df['STRIKE'] = df['STRIKE'].astype(int)

	for t in tickers:
		row = contract2Row[t.contract]
		df.iloc[row, 4:] = (t.bid, t.ask)

	df['MID'] = (df['bid'] + df['ask']) / 2
	#df['OPTION_REF'] = df['SYMBOL'].str.ljust(6) + df.EXPIRATION
	df['OPTION_REF'] = [c.localSymbol for c in contracts]
	df['UNDLY_PRICE'] = spxValue
	df['TRADE_DT'] = now.strftime("%Y%m%d")
	df['TRADE_TIME'] = now.strftime("%H:%M:%S")

	print("Timestamp of latest ticker update: " + str(now.strftime("%H:%M:%S")))
	df_calls = df[df['RIGHT'] == 'C']
	df_puts = df[df['RIGHT'] == 'P']
	#df_puts = df_puts.rename(columns={'R_REF': 'PUT_REF'})

	#df_calls = df_calls[['STRIKE', 'OPTION_REF', 'MID']]
	#df_calls = df_calls.rename(columns={'mid': 'CALL_MID'})
	#df_calls = df_calls.rename(columns={'R_REF': 'CALL_REF'})

	#df_exp = df_puts.merge(df_calls, on=["EXPIRATION", "STRIKE"], how='left')
	df_exp = pd.concat([df_puts, df_calls], axis=0)
	df_exp['MID'] = pd.to_numeric(df_exp['MID'])
	#df_exp = df_exp.rename(columns={'mid': 'PUT_MID'})
	#df_exp = df_exp.rename(columns={'SYMBOL': 'UNDLY'})
	df_exp = df_exp.drop(['bid', 'ask'], axis=1)
	df_exp = df_exp.sort_values(['EXPIRATION', 'RIGHT', 'STRIKE', 'TRADE_DT', 'TRADE_TIME', ], ascending=False)
	df_exp.reset_index(drop=True, inplace=True)

	cols = ["TRADE_DT", "TRADE_TIME", "UNDLY", "UNDLY_PRICE", "EXPIRATION", "STRIKE", "RIGHT", "OPTION_REF", "MID"]
	df_exp = df_exp[cols]
	# df_exp = df_exp.query("CALL_MID>=0 & PUT_MID>=0" )  # delete negative prices bad data
	updateTime = dt.now() - now
	print('finished updating data tab in ' + str(updateTime) + 's')

	return df_exp

def start_streaming(contracts, spx):
	df = update_price(contracts, spx)
	sht1.range('A1:I1').expand('down').clear_contents()
	sht1.range('A1:I1').options(index=False).value = df

class OpenPos(object):
	def __init__(self, spx):
		print("setting up openpos class...")

		self.cons = [i for i in sht3.range('B2').expand('down').value if i!=0]
		self.contracts = [Contract('SPX', secType="OPT", localSymbol=opra, exchange='SMART')
					 for opra in self.cons]
		ib.qualifyContracts(*self.contracts)


		self.spx_ticker = ib.reqMktData(spx, '', False, False)
		self.open_tickers = [ib.reqMktData(c, '', False, False) for c in self.contracts]


	def update_ticks(self):
		timeout = time.time() + 2
		while self.spx_ticker.last != self.spx_ticker.last:
			ib.sleep(0.01)
			if time.time() > timeout:
				spxValue = self.spx_ticker.close
				break
		if isNan(self.spx_ticker.last):
			spxValue = self.spx_ticker.close
		else:
			spxValue = self.spx_ticker.last

		ib.sleep(0.5)

		# grab contracts from OPENPOS sheet
		cons = [i for i in sht3.range('B2').expand('down').value if i!=0]
		if cons == self.cons:
			print('updating ticks...')
			now = dt.now()
			df = pd.DataFrame(columns='localSymbol bid ask'.split())
			df['localSymbol'] = [c.localSymbol for c in self.contracts]
			contract2Row = {c: i for (i, c) in enumerate(self.contracts)}

			for t in self.open_tickers:
				row = contract2Row[t.contract]
				df.iloc[row, 1:] = (t.bid, t.ask)
			df = df[["bid", "ask"]]
			df['mid'] = (df['bid'] + df['ask']) / 2

			df['time'] = now.strftime("%H:%M:%S")
			df['date'] = now.strftime("%Y%m%d")
			df['SPX'] = spxValue

			print("Timestamp of latest openpos update: " + str(now.strftime("%H:%M:%S")))
			return df, self.open_tickers, self.cons
		else:
			self.cons = cons
			print('updating new ticks...')
			self.contracts = [Contract('SPX', secType="OPT", localSymbol=opra, exchange='SMART')
						 for opra in cons]
			ib.qualifyContracts(*self.contracts)
			ib.sleep(0.2)
			self.open_tickers = [ib.reqMktData(c, '', False, False) for c in self.contracts]
			ib.sleep(0.5)

			now = dt.now()
			df = pd.DataFrame(columns='localSymbol bid ask'.split())
			df['localSymbol'] = [c.localSymbol for c in self.contracts]
			contract2Row = {c: i for (i, c) in enumerate(self.contracts)}

			for t in self.open_tickers:
				row = contract2Row[t.contract]
				df.iloc[row, 1:] = (t.bid, t.ask)
			df = df[["bid", "ask"]]
			df['mid'] = (df['bid'] + df['ask']) / 2

			df['time'] = now.strftime("%H:%M:%S")
			df['date'] = now.strftime("%Y%m%d")
			df['SPX'] = spxValue
			print (df)

			print("Timestamp of latest openpos update: " + str(now.strftime("%H:%M:%S")))
			return df, self.open_tickers, self.cons

def get_option_portfolio():
	now = dt.now()
	portf = ib.portfolio()

	portfolio_options = [p.contract for p in portf if
						 p.contract.__class__.__name__ == 'Option' and p.contract.symbol == 'SPX']
	portfolio_opt_pos = [p.position for p in portf if
						 p.contract.__class__.__name__ == 'Option' and p.contract.symbol == 'SPX']
	#portfolio_opt_mid = [p.marketPrice for p in portf if
	#					 p.contract.__class__.__name__ == 'Option' and p.contract.symbol == 'SPX']

	# print(portfolio_options)

	df_portopts = util.df(portfolio_options)
	pos = pd.Series(portfolio_opt_pos)
	#mid = pd.Series(portfolio_opt_mid)
	df_portopts.drop(
		['secType', 'multiplier', 'exchange', 'primaryExchange', 'currency', 'tradingClass', 'includeExpired',
		 'secIdType', 'secId', 'comboLegsDescrip', 'comboLegs', 'deltaNeutralContract'], axis=1, inplace=True)
	df_portopts['POSITION'] = pos.values
	df_portopts = df_portopts.rename(columns={'localSymbol': 'OPTION_REF'})

	#### Detailed download of Portfolio Columns ---> not neccessary for crosscheck feature

	#df_portopts = df_portopts.rename(columns={'lastTradeDateOrContractMonth': 'EXPIRATION'})

	#df_portopts = df_portopts.rename(columns={'right': 'RIGHT'})
	#df_portopts = df_portopts.rename(columns={'strike': 'STRIKE'})

	#df_portopts['MID'] = mid.values
	#df_portopts['EXPIRATION'] = pd.to_datetime(df_portopts['EXPIRATION'])
	#df_portopts['DTE'] = (df_portopts['EXPIRATION'] - dt.today()).dt.days
	#df_portopts['EXPIRATION'] = df_portopts['EXPIRATION'].dt.strftime('%Y%m%d')

	#conIds = df_portopts['conId'].tolist()
	#contracts = [Contract(conId=id, exchange='SMART') for id in conIds]
	#ib.qualifyContracts(*contracts)
	#tickers = ib.reqTickers(*contracts)
	#ib.sleep(2)
	#try:
	#	vols = [t.modelGreeks.impliedVol for t in tickers]
	#	df_portopts['ibIV'] = vols
	#except:
	#	pass
	#try:
	#	deltas = [t.modelGreeks.delta for t in tickers]
	#	df_portopts['ibDelta'] = deltas
	#except:
	#	pass

	#df_portopts['TRADE_DT'] = now.strftime("%Y%m%d")
	#df_portopts['TRADE_TIME'] = now.strftime("%H:%M:%S")
	#cols = ["TRADE_DT", "TRADE_TIME", "EXPIRATION", "STRIKE", "RIGHT", "OPTION_REF", "MID", "POSITION"]
	cols = ["OPTION_REF", "POSITION"]
	df_portopts = df_portopts[cols]
	return df_portopts

def update_portfolio():
	print('Updating IB positions....')
	df = get_option_portfolio()
	while True: # run loop to prevent Excel error when interacting with sheet
		try:
			sht4.range('A1:I1').expand('right').clear_contents()
			sht4.range('A1:I1').options(index=True, expand='down').value = df
			break
		except com_error as reason:
			print (reason)
			continue
	print('finished updating IBOPENPOS tab....')

def start_ticks():
	df = op.update_ticks()[0]  # return only df (not self.opentickers and self.cons)
	while True: # run loop to prevent Excel error when interacting with sheet
		try:
			sht3.range('C1').options(index=False, expand='table').value = df
			break
		except com_error as reason:
			print (reason)
			continue


if __name__ == "__main__":
	nest_asyncio.apply()
	signal.signal(signal.SIGINT, signal_handler)

# create ib_insync IB() instance and connect to TWS
	ib = IB()
	ib.sleep(0.1)
	conn_tws()
	ib.sleep(0.1)
	ib.client.MaxRequests = 48
	ib.reqMarketDataType(marketDataType=2)

	df_lib = get_libor_func()
	print('Libor download finished')

	contracts, spx = get_tickers(min_dte, max_dte, strike_distance, upper_strike_range, lower_strike_range)
	print('connecting to Excel workbook...')
	wb = xw.Book(workbook)
	sht1 = wb.sheets[stream2tab]
	sht2 = wb.sheets['RFRATE']
	sht3 = wb.sheets['OPENPOS']
	sht4 = wb.sheets['IBOPENPOS']
	print('streaming Libor data to Excel...')
	sht2.range('c1').options(index=False).value = df_lib


	op = OpenPos(spx)

	print("starting data streaming...")
	while True:
		start_streaming(contracts, spx)
		end = time.time() + wait_data
		while time.time() < end:
			end2 = time.time() + wait_portfolio
			update_portfolio()
			while time.time() < end2:
				ib.sleep(wait_openpos)
				start_ticks()


