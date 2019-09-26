# ib2Excel
Script to stream TWS option data to Excel sheet live
sheet_version: live_example3

Prerequisites:
TWS or TWS gateway, TWS API installation, Python >3.6, ib_insync library

Setup:
1) Have TWS running, API enabled, port set. 
2) Have your Excel workbook opened
3) Open setup.py insert API port and workbook name
4) Setup chain variables in setup.py to limit data to desired extent
5) Setup update intervals for openpositions and full chain data
5) run ib2excel.py - it takes about 1-2 minutes to setup before starting to stream data / then about 1min to stream the first full chain data to DATA sheet / then will repeat updating OPENPOS
6) closing with CTRL+C will disconnect from IB API and shut down properly.



Possible Roadmap:
- link to sql
- add functionality to dump streamed data to sql in certain intervals (15mins?)
- schedule streaming to open market hours
- make importing trades easier using ib.fills
