import argparse
import pandas as pd
from pathlib import Path
from collections import defaultdict


CUR_PATH = Path(__file__).resolve().parent

# these are all of the columns used in the table 1.4 spreadsheet. The pattern
# used for this list is (SOI_estimates variable name, col1, col2, col3, col4)
# each of those columns is needed because pandas will read the spreadsheet as
# a DataFrame with multiple column labels. If the IRS changes the format of
# the table 1.4 spreadsheet, this script will break and you'll need to update
# the columns in this list. You will also need to update this list if you add
# a new variable to the estimates.
TABLE14COLS = [
    (
        "SS_return",
        "Social security benefits",
        "Total [1]",
        "Unnamed: 67_level_2",
        "Number of\nreturns",
    ),
    ("INTS", "Taxable interest", "Unnamed: 8_level_1", "Unnamed: 8_level_2", "Amount"),
    (
        "DIVS",
        "Ordinary dividends",
        "Unnamed: 12_level_1",
        "Unnamed: 12_level_2",
        "Amount",
    ),
    ("SCHCI", "Business or profession", "Net\nincome", "Unnamed: 20_level_2", "Amount"),
    ("SCHCL", "Business or profession", "Net\nloss", "Unnamed: 22_level_2", "Amount"),
    (
        "CGNS",
        "Sales of capital assets reported on Form 1040, Schedule D [2]",
        "Taxable\nnet gain",
        "Unnamed: 26_level_2",
        "Amount",
    ),
    ("Pension", "Pensions and annuities", "Unnamed: 38_level_1", "Taxable", "Amount"),
    (
        "SCHEI",
        "Total rental and royalty",
        "Net\nincome",
        "Unnamed: 52_level_2",
        "Amount",
    ),
    (
        "SCHEI",
        "Partnership and S corporation",
        "Net\nincome",
        "Unnamed: 56_level_2",
        "Amount",
    ),
    ("SCHEI", "Estate and trust", "Net\nincome", "Unnamed: 60_level_2", "Amount"),
    ("SCHEL", "Total rental and royalty", "Net\nloss", "Unnamed: 54_level_2", "Amount"),
    (
        "SCHEL",
        "Partnership and S corporation",
        "Net\nloss",
        "Unnamed: 58_level_2",
        "Amount",
    ),
    ("SCHEL", "Estate and trust", "Net\nloss", "Unnamed: 62_level_2", "Amount"),
    ("SS", "Social security benefits", "Total [1]", "Unnamed: 70_level_2", "Amount"),
    (
        "UCOMP",
        "Unemployment compensation",
        "Unnamed: 68_level_1",
        "Unnamed: 68_level_2",
        "Amount",
    ),
]
# these lists are the indicies for the wage bins used to split up wage targetts
# in the SOI estimates.
PUFWAGES = [
    (2, 2),
    (3, 4),
    (5, 6),
    (7, 8),
    (9, 9),
    (10, 10),
    (11, 11),
    (12, 12),
    (13, 13),
    (14, 14),
    (15, 15),
    (17, 20),
]
CPSWAGES = [(2, 4), (5, 6), (7, 8), (9, 9), (10, 10), (11, 11), (12, 12), (13, 20)]


def update_soi(year, datapath, wage_indicies, file_):
    """
    Update SOI estimates for a given year by reading and parsing the given SOI
    spreadsheets

    Paramters
    ---------
    year: year of the estimates you're adding
    datapath: path to the necessary files from the SOI
    wage_indicies: the PUF and CPS estimates have different wage
    file_: "cps" or "puf"
    """
    single, married, hoh = table12(year, datapath)
    # dep_return = table23(year, datapath)
    dep_return = 0
    ipd = table21(year, datapath)
    nonwages, wages = table14(year, wage_indicies, datapath)
    values = [
        single,
        married,
        hoh,
        nonwages["SS_return"],
        dep_return,
        nonwages["INTS"],
        nonwages["DIVS"],
        nonwages["SCHCI"],
        nonwages["SCHCL"],
        nonwages["CGNS"],
        nonwages["Pension"],
        nonwages["SCHEI"],
        nonwages["SCHEL"],
        nonwages["SS"],
        nonwages["UCOMP"],
        ipd,
    ]
    if file_ == "cps":
        values = values[:-1]
    values += wages
    return values


def table12(year, datapath):
    """
    Extract the total returns from single, joint, and married filers from
    SOI table 1.2
    """

    def numfilers(data, col):
        nreturns = "Number\nof\nreturns"
        allreturns = "All returns, total"
        return data[col][nreturns].loc[allreturns].values[0].astype(int)

    file_ = f"{str(year)[-2:]:}in12ms.xls"
    print(file_)
    data = pd.read_excel(Path(datapath, file_), header=[2, 3, 4], index_col=0)
    single = numfilers(data, "Returns of single persons")
    col = "Returns of married persons filing jointly and returns of surviving spouses"
    married1 = numfilers(data, col)
    married2 = numfilers(data, "Returns of married persons filing separately")
    married = married1 + married2
    hoh = numfilers(data, "Returns of heads of households")
    return single, married, hoh


def table23(year, datapath):
    """
    Returns number of dependent exemption from SOI table 2.3
    """
    file_ = f"{str(year)[-2:]:}in23ar.xls"
    data = pd.read_excel(Path(datapath, file_), header=[2, 3, 4], index_col=0)
    col = "Exemptions for dependents"
    nexemp = "Number\nof\nexemptions"
    allreturns = "All returns, total"
    return data[col]["Total"][nexemp].loc[allreturns].astype(int)


def table21(year, datapath):
    """
    Return interest paid deduction amount from table 2.1
    Parameters
    ----------
    year: integer representing the year of the table
    datapath: path to the directory holding the SOI files
    """
    file_ = f"{str(year)}in21id.xls"
    data = pd.read_excel(Path(datapath, file_), header=[2, 3, 4, 5, 6], index_col=0)
    itemded = "Itemized deductions"
    ipd = "Interest paid deduction"
    un = "Unnamed: 89_level_3"
    if year == "2017":
        un = "Unnamed: 85_level_3"
    if year == "2019":
        un = "Unnamed: 91_level_3"
    allrets = "All returns, total"
    return data[itemded][ipd]["Total"][un]["Amount"].loc[allrets].astype(int)


def table14_nonwages(data, cols):
    """
    Extracts all needed data except wages from table 1.4
    Parameters
    ----------
    data: SOI data
    cols: See TABLE14COLS
    """
    values = defaultdict(int)
    if year == "18":
        print("recheck the value by hand")
        values = []
        return values
    for col in cols:
        val = data[col[1:]].loc["All returns, total"].astype(int)
        values[col[0]] += val
    return values


def table14_wages(data, indicies):
    """
    Return all of the wage totals
    Parameters
    ----------
    data: table 1.4 data
    indicies: See PUFWAGES and CPSWAGES
    """
    was = []
    assert len(data) == 21  # they sometimes change up the wage bins they use
    data = data["Salaries and wages"]["Unnamed: 6_level_1"]["Unnamed: 6_level_2"]
    for i, j in indicies:
        val = data.iloc[i : j + 1].sum()[0].astype(int)
        was.append(val)
    return was


def table14(year, wage_indicies, datapath):
    """
    Grabs everything from table 1.4 by calling the two other table 1.4
    functions.
    Parameters
    ----------
    year: year we're pulling the data for
    wage_indicies: see PUFWAGES and CPSWAGES
    datapath: path to directory where the SOI data is stored
    """
    data = pd.read_excel(
        Path(datapath, f"{str(year)[-2:]:}in14ar.xls"), header=[2, 3, 4, 5], index_col=0
    )
    data = data.iloc[:21]
    nonwages = table14_nonwages(data, TABLE14COLS)
    wages = table14_wages(data, wage_indicies)
    return nonwages, wages


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("year", help="Year of the update", type=str)
    parser.add_argument(
        "path", help="Path to a directory with all of the SOI files needed", type=str
    )
    args = parser.parse_args()
    year = args.year
    datapath = args.path

    puf_vals = update_soi(year, datapath, PUFWAGES, "puf")
    pufpath = Path(CUR_PATH, "SOI_estimates.csv")
    puf_soi = pd.read_csv(pufpath, index_col=0)
    puf_soi[year] = puf_vals
    cpspath = Path(CUR_PATH, "..", "cps_stage1", "SOI_estimates.csv")
    cps_soi = pd.read_csv(cpspath, index_col=0)
    cps_vals = update_soi(year, datapath, CPSWAGES, "cps")
    cps_soi[year] = cps_vals
    puf_soi.to_csv(pufpath)
    cps_soi.to_csv(cpspath)
