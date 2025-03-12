Data API
The Drift Data API provides public access to various APIs that Drift uses, offering information about markets, contracts, and tokenomics. This API allows developers and users to retrieve data related to the Drift protocol.

mainnet-beta: https://data.api.drift.trade
devnet: https://master-data.drift.trade
See the Data API Playground for more information and to try the endpoints yourself.

Rate Limiting
To ensure fair usage and maintain system stability, the Drift Data API implements rate limiting. Users are restricted to a certain number of requests per minute. The exact limit may vary depending on the endpoint and overall system load. If you exceed the rate limit, you'll receive a 429 (Too Many Requests) response. It's recommended to implement exponential backoff in your applications to handle rate limiting gracefully.

Caching
The Drift Data API utilizes caching mechanisms to improve performance and reduce server load. Responses may be cached for a short period, typically ranging from a few seconds to a few minutes, depending on the endpoint and the nature of the data. While this ensures quick response times, it also means that there might be a slight delay in reflecting the most recent updates. Time-sensitive operations should account for this potential delay.

GET /contracts
Returns the contract information for each market. Contract information contains funding rate and open interest (oi).

Example: https://data.api.drift.trade/contracts

GET /fundingRates
Returns the last 30 days of funding rates by marketName or marketIndex.

import requests

def get_funding_rates(market_symbol='SOL-PERP'):
    url = f'https://data.api.drift.trade/fundingRates'
    params = {'marketName': market_symbol}

    response = requests.get(url, params=params)
    return response.json()['fundingRates']

# Example usage, print the funding rates for SOL-PERP
market_symbol = 'SOL-PERP'
rates = get_funding_rates(market_symbol)

print(f"Funding Rates for {market_symbol}:")
for rate in rates:
    funding_rate = float(rate['fundingRate']) / 1e9
    # ... any logic here, for example...
    print(f"Slot: {rate['slot']}, Funding Rate: {funding_rate:.9f}")

 The funding rate is returned as a string and needs to be divided by 1e9 to get the actual rate.
Parameter	Description	Optional	Values
marketName or marketIndex	The market name or index for the perp market	NO	
Example: https://data.api.drift.trade/fundingRates?marketName=SOL-PERP

Response
The response is a json object with a fundingRates array. Each funding rate entry contains the following fields:

Field	Type	Description
txSig	string	Transaction signature
slot	integer	Slot number
ts	string	Timestamp
recordId	string	Record identifier
marketIndex	integer	Market index
fundingRate	string	Funding rate (divide by 1e9 for actual rate)
cumulativeFundingRateLong	string	Cumulative funding rate for long positions
cumulativeFundingRateShort	string	Cumulative funding rate for short positions
oraclePriceTwap	string	Oracle price time-weighted average price
markPriceTwap	string	Mark price time-weighted average price
fundingRateLong	string	Funding rate for long positions
fundingRateShort	string	Funding rate for short positions
periodRevenue	string	Revenue for the period
baseAssetAmountWithAmm	string	Base asset amount with AMM
baseAssetAmountWithUnsettledLp	string	Base asset amount with unsettled LP
GET /DRIFT/
Returns the tokenomics information about the Drift token.

Parameter	Description	Optional	Values
q	Metrics related to the drift tokenomics	NO	circulating-supply,locked-supply,total-supply
Example: https://data.api.drift.trade/DRIFT?q=circulating-supply

GET /rateHistory
Returns the tokenomics information about the Drift token.

Parameter	Description	Optional	Values
marketIndex	The market index of the market to get	NO	
type	The metric returned. Default: deposit	YES	deposit,borrow,deposit_balance,borrow_balance
Example: https://data.api.drift.trade/rateHistory?marketIndex=0

Historical Data
Snapshots are collected by parsing on-chain transaction logs. For convience the below are parsed logs collected, stored as a CSV, and stored off-chain (~99% of records). Records are updated once per day.

Please share any transaction signatures or time ranges you believe might be missing in Drift Protocol Discord.

URL Prefix
mainnet-beta: https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH/

URL Suffix
Schema
recordType	url suffix
trades	user/${accountKey}/tradeRecords/${year}/${year}${month}${day}
market-trades	market/${marketSymbol}/tradeRecords/${year}/${year}${month}${day}
swaps	user/${accountKey}/swapRecords/${year}/${year}${month}${day}
funding-rates	market/${marketSymbol}/fundingRateRecords/${year}/${year}${month}${day}
funding-payments	user/${accountKey}/fundingPaymentRecords/${year}/${year}${month}${day}
deposits	user/${accountKey}/depositRecords/${year}/${year}${month}${day}
liquidations	user/${accountKey}/liquidationRecords/${year}/${year}${month}${day}
settle-pnl	user/${accountKey}/settlePnlRecords/${year}/${year}${month}${day}
lp	user/${accountKey}/lpRecord/${year}/${year}${month}${day}
insurance-fund	market/${marketSymbol}/insuranceFundRecords/${year}/${year}${month}${day}
insurance-fund-stake	authority/${authorityAccountKey}/insuranceFundStakeRecords/${year}/${year}${month}${day}
candle-history	candle-history/{year}/{marketKey}/{candleResolution}.csv
Variables
variable	description	example
accountKey	user sub account public key (not authority)	
authority	authority public key	
marketSymbol	market name. E.g. SOL-PERP for Solana PERP or SOL for Solana SPOT	SOL-PERP
year		2023
month		4
day	utc time	25
marketKey	The key for the market. Format: {marketType}_{marketIndex}	perp_0
candleResolution	Candle Resolution. See "Available Candle Resolutions" below	M
Available Candle Resolutions:
resolution	description
1	1 minute
15	15 minute
60	1 hr
240	4 hr
D	1 day
W	1 week
Example: Trades for market
import requests


URL_PREFIX = 'https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH'

market_symbol = 'SOL-PERP'
year = '2024'
month = '01'
day = '01'

# Method 1: using pandas (this is the easiest and fastest way)
import pandas as pd
df = pd.read_csv(f'{URL_PREFIX}/market/{market_symbol}/tradeRecords/{year}/{year}{month}{day}')
print(df)

# Method 2: using csv reader
import csv
from io import StringIO

response = requests.get(f'{URL_PREFIX}/market/{market_symbol}/tradeRecords/{year}/{year}{month}{day}')
response.raise_for_status()

csv_data = StringIO(response.text)
reader = csv.reader(csv_data)
for row in reader:
    print(row)

Get historical trades on SOL-PERP for a given date (ex. 2024-01-01): https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH/market/SOL-PERP/tradeRecords/2024/20240101

Example: Trades for date range
import requests
import csv
from io import StringIO
from datetime import date, timedelta
import pandas as pd

URL_PREFIX = 'https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH'

# Method 1: using pandas
def get_trades_for_range_pandas(account_key, start_date, end_date):
    all_trades = []
    current_date = start_date
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        day = current_date.day
        url = f"{URL_PREFIX}/user/{account_key}/tradeRecords/{year}/{year}{month:02}{day:02}"

        try:
            df = pd.read_csv(url)
            all_trades.append(df)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {current_date}: {e}")
        except pd.errors.EmptyDataError:
            print(f"No data available for {current_date}")

        current_date += timedelta(days=1)

    if all_trades:
        return pd.concat(all_trades, ignore_index=True)
    else:
        return pd.DataFrame()

# Method 2: using csv reader
def get_trades_for_range_csv(account_key, start_date, end_date):
    all_trades = []
    current_date = start_date
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        day = current_date.day
        url = f"{URL_PREFIX}/user/{account_key}/tradeRecords/{year}/{year}{month:02}{day:02}"
        response = requests.get(url)
        response.raise_for_status()

        csv_data = StringIO(response.text)
        reader = csv.reader(csv_data)
        for row in reader:
            all_trades.append(row)

        current_date += timedelta(days=1)

    return all_trades


# Example usage
account_key = "<Some Account Key>"
start_date = date(2024, 1, 24)
end_date = date(2024, 1, 26)

trades = get_trades_for_range(account_key, start_date, end_date)
Note: To speed this up, you could download the data in parallel (Promise.all or asyncio).

We can write a script to download all the data, one by one, for a given account in a given date range.

Records Columns
Below are definitions of the columns in each record type.

trades
variable	description	example
accountKey	user sub account public key (not authority)	
funding-rates
note: 'rate' is in quote per base, to allow for async settlement

variable	description	example
fundingRate	the quote asset amount (precision=1e6) per base asset amount (precision=1e9)	
to convert to the rates seen on the ui, use the following formula: (funding_rate / BASE_PRECISION) / (oracle_twap / QUOTE_PRECISION) * 100

import requests

outcsv = requests.get('https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH/user/FrEFAwxdrzHxgc7S4cuFfsfLmcg8pfbxnkCQW83euyCS/tradeRecords/2023/20230201')'
