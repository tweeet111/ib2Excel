# ib2Excel
Script to stream TWS option data to Excel sheet live

Prerequisites:
TWS or TWS gateway, TWS API installation, Python >3.6, ib_insync library

Setup:
1) Have TWS running, API enabled, port set. 
2) Have your Excel workbook opened
3) Open setup.py insert API port and workbook name
4) Setup chain variables in setup.py to limit data to desired extent
5) Setup update interval (0.1 will give fastest updates possible and will take 1-8 seconds 
   dependent from the number of subscripted chains and strikes)
5) run setup.py
6) closing with CTRL+C will disconnect from IB API and shut down properly.



Possible Roadmap:
- link to sql
- add functionality to dump streamed data to sql in certain intervals (15mins?)
- schedule streaming to open market hours
- ...
