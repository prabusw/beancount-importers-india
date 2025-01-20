import os, sys

# beancount doesn't run from this directory
sys.path.append(os.path.dirname(__file__))

# importers located in the importers directory
from importers.icici import icici
# by changing the last 4 number of account, any account can be imported

CONFIG = [
    icici.IciciBankImporter('Assets:IciciBank:Prabu', '1585'),
    icici.IciciBankImporter('Assets:IciciBank:Kali', '7875'),
    icici.IciciBankImporter('Assets:IciciBank:jeeva', '3322'),
]
