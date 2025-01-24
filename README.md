This repository has few Importers for [Beancount](https://github.com/beancount/beancount), a plain text accounting software.

The available importers are for:

 Indian Banks like
 - Icici Bank
 - SBI
 - KVB
 - IOB

Stock brokers like
- Zerodha - India
- E*Trade - US

## Folder Structure

In beangulp, the importers are called by an import_XXX.py which has
replaced the config.py files used earlier. The ledger is my.beancount.

![folder
structure](https://github.com/prabusw/beancount-importer-zerodha/blob/master/folderstructure.png)


## Importer for Banks

The importer script icici.py can be used to handle the csv formatted
file which can be generated by the xls2csv tool from catdoc package.

The original headers in the file downloaded from ICICBank has the
following columns.

```
S No.	Value Date	Transaction Date	Cheque Number	Transaction Remarks	Withdrawal Amount (INR )	Deposit Amount (INR )	Balance (INR )
```

When downloading SBI transaction statements, if xls is choosen, the
file will be in tsv format even though the file will get downloaded
with .xls extension. Use the tsv2csv.sh script in tools folder to
convert this to csv format.

Almost all the other bank importers like IOB and KVB work with the csv
file(s) downloaded from their respective bank website, without any
modification.

If the downloaded csv has the account number in it, then use it in
your importer config file.

## Importer for Brokers

### Zerodha
The importer for Indian stock broker Zerodha works with the csv
formatted tradebook downloaded from their website. Every decent
broker in India, gives similar tradebook.  So this importer can work
almost for every broker who provides tradebook in csv format.

As of Jan'2025 the csv formatted tradebook downloaded from Zerodha has
the following fields:

```
symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time
```
Just ensure that the csv file is named as zerodhaNNNNNNNN.csv
format. For example, zerodha20232024.csv is a valid filename.

### E*Trade
The csv formatted transaction statement downloaded from E*Trade
website can be used without any modifications using the given
importer. The TransactionType in importer code may need adjustments,
if rows are skipped.

## Using the Importers

The command to use this beangulp based importer to identify, extract
and archive is given below:

```
$./import_prabu.py [option] Downloads/
where option can be identify|extract|archive
```
Depending on the number of matching csv files available in Downloads
folder, the beancount formatted output will be displayed one by
one. You can redirect it to new txt file and copy paste it later to
my.beancount.
