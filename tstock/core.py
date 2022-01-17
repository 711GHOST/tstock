import os
import random
import requests
import numpy as np
from .parse import *

def translate(x, l1, h1, l2, h2):
    """Translate from one range to another.
    
    Arguments:
        x (number) - number to translate in range 1.
        l1 (number) - lower bound of range 1.
        h1 (number) - upper bound of range 1.
        l2 (number) - lower bound of range 2.
        h2 (number) - upper bound of range 2.

    Returns:
        y (number) - x mapped to range 2.
    """
    return (((x - l1) / (h1 - l1)) * (h2 - l2)) + l2


def get_api_key():
    """Gets the API key from the environment variable ALPHAVANTAGE_API_KEY, raises an error if not found."""
    if not 'ALPHAVANTAGE_API_KEY' in list(os.environ.keys()):
        print("error: API key not detected! Follow these instructions to get your API Key working:\n" + \
        "- Make a free AlphaVantage API account at https://www.alphavantage.co/support/#api-key\n" + \
        "- After creating the account, you will see your free API key\n" + \
        "- Run \"export ALPHAVANTAGE_API_KEY=<your access key>\"." + \
        "You can make this permanent by adding this line to your .bashrc\n")
        exit(1)
    return os.environ['ALPHAVANTAGE_API_KEY']


def draw_graph():
    """Main tstock script body."""

    parser = get_args()
    parse_args_exit(parser)

    padX = 5  # TODO: make padX an option
    padY = 4
    intervals_back = 71
    verbose = False
    chart_only = False
    wisdom = False
    full = False
    maxY = 40
    interval = 'day'

    # Parse arguments
    args = parser.parse_args()
    ticker = args.ticker[0]
    if args.b:
        intervals_back = int(args.b)
        if intervals_back > 100:
            full = True
    if args.v:
        verbose = args.v
    if args.y:
        maxY = args.y
    if args.c:
        chart_only = args.c
    if args.w:
        wisdom = args.w
    if args.t:
        interval = args.t
    if args.padx:
        padX = args.padx
    if args.pady:
        padY = args.pady

    interval_to_api = {
        'day': 'TIME_SERIES_DAILY',
        'week': 'TIME_SERIES_WEEKLY',
        'month': 'TIME_SERIES_MONTHLY_ADJUSTED'
    }

    # HTTP GET API data
    apikey = get_api_key()
    request_url = f'https://www.alphavantage.co/query?function={interval_to_api[interval]}&symbol={ticker}&apikey={apikey}&outputsize={"full" if full else "compact"}'
    if verbose:
        print(
            f"Intervals Back: {intervals_back}\nTicker: {ticker}\nAPI Key: {apikey}\nRequest URL: {request_url}\nY height: {maxY}\nInterval: {interval}\n" + \
            f"Wisdom: {wisdom}\nChart only: {chart_only}"
        )

    r = requests.get(request_url).json()
    if 'Error Message' in list(r.keys()):
        print(f"error: The API returned the following error:\n{r}")
        exit(1)
    data = r[list(r.keys())[1]]

    # Parse API data
    candlesticks = []   
    for k, v in data.items():
        candlesticks.append(
            [float(v['1. open']), float(v['2. high']), float(v['3. low']), float(v['4. close']), -1])
        if interval == 'day' or interval == 'week':
            candlesticks[-1][4] = int(k[8:])
        elif interval == 'month':
            candlesticks[-1][4] = int(k[5:7])
        if len(candlesticks) == intervals_back:
            break

    candlesticks = list(reversed(candlesticks))
    maxX = len(candlesticks) + padX * 2 + 2

    # Create the chart
    chart = np.array([[" " for x in range(maxX)] for y in range(maxY)])
    column_colors = ["\x1b[0m" for x in range(maxX)]  # Stores ANSI escape sequences for printing color
    # Draw borders
    chart[0, :] = "─"
    chart[-1, :] = "─"
    chart[:, 0] = "│"
    chart[:, -1] = "│"
    chart[0, 0] = "┌"
    chart[0, -1] = "┐"
    chart[-1, 0] = "└"
    chart[-1, -1] = "┘"
    # Draw graph title, if there are there enough worth of data to contain it
    title = f"┤  {intervals_back} {interval.capitalize()} Stock Price for ${ticker.upper()}  ├"
    if maxX >= len(title) + 2:
        for i, c in enumerate(title):
            chart[0, i + 1] = c
    # Find all time high and all time low
    ath = 0
    atl = 99999999
    for c in candlesticks:
        if c[1] > ath:
            ath = c[1]
        if c[2] < atl:
            atl = c[2]
    # Draw candlesticks
    start_i = 1 + padX
    end_i = maxX - 1 - padX
    y_axis_low = padY
    y_axis_high = maxY - padY
    for i, c in enumerate(candlesticks):
        shifted_i = i + start_i
        # Stuff gets a little confusing here because the graph has to be y-inverted. "high" is referring to a high price, but needs to be flipped to a low index.
        translated_open = int(
            translate(c[0], atl, ath, y_axis_high, y_axis_low))
        translated_high = int(
            translate(c[1], atl, ath, y_axis_high, y_axis_low))
        translated_low = int(translate(c[2], atl, ath, y_axis_high,
                                       y_axis_low))
        translated_close = int(
            translate(c[3], atl, ath, y_axis_high, y_axis_low))
        # Draw high/low
        for y in range(translated_high, translated_low + 1):
            chart[y, shifted_i] = "|"
        # Draw open/close
        # Positive day, stock went up
        if c[0] < c[3]:
            column_colors[shifted_i] = "\x1b[32m"  # ANSI green
            tmp = translated_low
            translated_low = translated_high
            translated_high = tmp
            for y in range(translated_close, translated_open + 1):
                chart[y, shifted_i] = "█"
        # Negative day, stock went down
        else:
            column_colors[shifted_i] = "\x1b[31m"  # ANSI red
            for y in range(translated_open, translated_close + 1):
                chart[y, shifted_i] = "█"

    # Setup x-axis labels
    x_axis_labels = " " * (1 + padX)
    for i in range(start_i, end_i):
        shifted_i = i - start_i
        if (shifted_i) % 5 == 0:
            chart[-1, i] = "┼"
            if int(candlesticks[shifted_i][4]) >= 10:
                x_axis_labels += f"{candlesticks[shifted_i][4]}   "
            else:
                x_axis_labels += f"{int(candlesticks[shifted_i][4])}    "
    x_axis_labels += " " * (maxX - len(x_axis_labels))

    # Setup y-axis labels
    y_axis_labels = []
    margin = len("${:,.2f}".format(ath))
    for i in range(maxY):
        if i >= y_axis_low and i <= y_axis_high:
            shifted_i = y_axis_high - i
            if shifted_i % 4 == 0:
                chart[i, 0] = "┼"
                label = "${:,.2f}".format(
                    translate(shifted_i, y_axis_low, y_axis_high, atl, ath))
                y_axis_labels.append(" " * (margin - len(label)) + f"{label}")
            else:
                y_axis_labels.append(" " * margin)
        else:
            y_axis_labels.append(" " * margin)

    # Print out the chart
    for y, row in enumerate(chart):
        out = ""
        out += y_axis_labels[y]
        for x, char in enumerate(row):
            if y >= y_axis_low and y <= y_axis_high:
                out += column_colors[x]
            out += char
        print(out)
    # Print x axis labels
    print(y_axis_labels[0] + x_axis_labels)
    print()

    if not chart_only:
        #Print additional info
        print("Last price:\t${:,.2f}".format(candlesticks[-1][3]))
        print(f"% change:\t{round(100*(candlesticks[-1][3]-candlesticks[0][0])/candlesticks[-1][3],2)}%")
        if wisdom:
            if candlesticks[-1][3] > candlesticks[0][0]:
                print(random.choice([
                    f"${ticker.upper()} to the moon! 🚀🚀🚀",
                    "Apes alone weak, apes together strong 🦍🦍🦍",
                    f"${ticker.upper()} primary bull thesis: I like the stock."
                    "Stocks can only go down 100% but can go up infinite %. Stocks can literally only go up. Q.E.D.",
                ]))
            else:
                print(random.choice([
                    "Losses aren't real 'till you sell 💎🙌",
                    "Literally cannot go tits up 💎🙌",
                    "GUH.",
                    "Short squeeze any time now 💎🙌"
                ]))
        print()