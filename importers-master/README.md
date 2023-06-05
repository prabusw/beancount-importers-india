# beancount-importer-zeodha


This is an importer for csv formatted tradebook from Indian stock broker Zerodha. Every decent broker in India, gives similar tradebook. 
So this importer can work almost for every broker who provides tradebook in csv format.

This importer zerodha.py is based almost entirely on the sample csv importer "utrade_csv.py" provided by the Beancount author Martin Blais.

The default csv formatted tradebook from Zerodha has the following fields: 
trade_date	tradingsymbol	exchange	segment	trade_type	quantity	price	order_id	trade_id	order_execution_time

For the importer to work, you need to manually add the following fields amount, fees either in Google sheets or Openoffice or other such spreadsheet software.

The formula for amount = quantity*price and for fees = amount*0.001 rounded to 2 decimal places. 

In openoffice,
formula for amount(column k) appears as =F2*G2, where columns F and G are quantity and price respectively.
forumla for fees(column L) appears as=round(k2*0.001,2).

With the above two changes done, make sure the csv file is named as zerodhayyyymmdd.csv format. For example, zerodha20200401.csv is a valid filename. 

This csv must be placed in Downloads folder at the root of beancount.

The script zerodha.py must be placed in the following folder importers\zerodha at the root of beancount. 

Refer to the folder structure presented at the bottom of this document with the above scripts in their respective folders. This structure 
is also available as a screengrab here https://github.com/prabusw/beancount-importer-zerodha/blob/master/folderstructure.png.

The configuration file is named as config.py and this can be in the same folder as the main beancount file i,e here my.beancount.

Importer for ICICIBank

If you have account with ICICI Bank, the importer script icici.py can be used. This script icici.py is heavily based on the script 
importers-chase.py hosted here  https://gist.github.com/mterwill/7fdcc573dc1aa158648aacd4e33786e8

The default transaction file downloaded in csv format from ICICI Bank website does not work as of now. Please follow the below steps:

How to prepare icicibank statement in xls for import as csv

* remove all sheets except original sheet with transaction data in it.
* remove logo
* removel left most column(empty)
* remove top few rows until the header row
* delete "S No.", "Transaction Date", "Cheque Number", and "Balance" columns
* make all withdrawl column entries as negative numbers by multiplying by (-1) into a new "tempAmount" column.
* use data autofilter to create filter on "Deposit Amount" for non-zero. Copy and paste the values Individually to "tempAmount" column. 
* copy all entries in "tempAmount" column to new "Amount" column with "paste special without formula" option.
* Ensure that all unnecessary temporary columns are removed retaining only three i.e.Value Date, Transaction Remarks and Amount
* Rename the column headings so that now the csv has the following column headings: "Posting Date", "Description", and "Amount"
* upload the csv/xls file to google sheets to change the date format as per yyyy-mm-dd. Then download it as csv.
* For the import script to work, the downloaded csv file must be named as icicixxxx.csv, where xxxx must match the entry in config.py file. 
* For eg. icici3722.csv is a valid name, for the config.py given here. This csv file must be placed in Downloads folder.
* The script icici.py needs to be placed in the folder importers\icici.

The original headers in the file downloaded from ICICBank has the following columns.
S No.	Value Date	Transaction Date	Cheque Number	Transaction Remarks	Withdrawal Amount (INR )	Deposit Amount (INR )	Balance (INR )

After following the above preperation steps, we are left with the following three columns only
Posting Date	Description	Amount

How to Extract data or import data from csv files 

The command(linux) to extract data in a format sutiable for beancount is given below. 

$bean-extract config.py Downloads

Depending on the number of matching csv files available in Downloads folder, the beancount formatted output will be displayed one by one. You can redirect it to new txt file and copy paste it later to my.beancount.To redirect

$bean-extract config.py Downloads > mytxn.txt


Sample two line input for zerodha.csv follows:
trade_date	tradingsymbol	exchange	segment	trade_type	quantity	price	order_id	trade_id	order_execution_time	amount	fees
2017-04-13	LIQUIDBEES	NSE	EQ	sell	30	999.99	1200000000772831	59283787	2017-04-13T09:54:26	29999.7	30
2017-04-13	INFY	NSE	EQ	buy	3	941.2	1100000000419606	26200755	2017-04-13T12:37:32	2823.6	2.82

The output of above command is given below
                               
2017-04-13 * "sell LIQUIDBEES with TradeRef 59283787" ^1200000000772831
  Assets:IN:Investment:Zerodha:LIQUIDBEES      -30 LIQUIDBEES {} @ 999.99 INR
  Expenses:Financial:Taxes:Zerodha              30 INR                       
  Assets:IN:Investment:Zerodha:Cash        29969.7 INR                       
  Income:IN:Investment:PnL:LIQUIDBEES                                        

2017-04-13 * "buy INFY with TradeRef 26200755" ^1100000000419606
  Assets:IN:Investment:Zerodha:INFY     3 INFY {941.2 INR}
  Expenses:Financial:Taxes:Zerodha   2.82 INR             
  Assets:IN:Investment:Zerodha:Cash          

Sample two line input for icici3722.csv follows:
Posting Date	Description	Amount
2019-04-01	MPS/SRI AUROBIN/201904011758/012476/	-249.22
2019-04-04	MCD REF SRI AUROBINDO UDYO DT 190401	1.87

The output of above command is given below

2019-04-01 * "MPS/Sri Aurobin/201904011758/012476/" ""
  Assets:IN:ICICIBank:Savings  -249.22 INR

2019-04-04 * "MCD Ref Sri Aurobindo Udyo Dt 190401" ""
  Assets:IN:ICICIBank:Savings  1.87 INR


Example folder structure:

├── config.py
├── documents
│   ├── Assets
│   │   └── IN
│   │       ├── ICICIBank
│   │       │   └── Savings
│   │       │       ├── Icici3722-fy2017-18.CSV
│   │       ── Zerodha
│   │           ├── tradebook_2017-04-01_to_2018-03-31.csv
│   ├── Expenses
│   │   
│   ├── Income
│   │   
│   └── Liabilities
├── Downloads
│   ├── icici3722.csv
│   ├── zerodha20170401.csv
│   
├── importers
│   ├── icici
│   │   ├── icici.py
│   │   ├── __init__.py
│   └── zerodha
│       ├── __init__.py
│       └── zerodha.py
├── my.beancount



