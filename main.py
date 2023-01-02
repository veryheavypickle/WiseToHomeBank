import os
import pandas as pd
from yodas import Menu


def main():
    # Find CSV files
    csvFiles = []
    for file in os.listdir():
        if file.endswith(".csv"):
            csvFiles.append(file)

    if len(csvFiles) > 0:
        fileSelector = Menu(csvFiles, title="Choose the CSV file you wish to convert")
        convertCSV(fileSelector.select())
    else:
        print("No files found, drop a CSV file in the directory " + os.getcwd())


def convertCSV(filePath):
    # format from http://homebank.free.fr/help/misc-csvformat.html
    wiseDF = pd.read_csv(filePath)

    print(wiseDF.columns)

    homeBankDF = pd.DataFrame()

    homeBankDF["date"] = wiseDF["Date"].apply(lambda wiseDate: wiseDateConverter(wiseDate))
    homeBankDF["payment"] = wiseDF["TransferWise ID"].apply(lambda wiseID: wiseIDtoPaymentCode(wiseID))
    homeBankDF["info"] = wiseDF["Description"]
    homeBankDF["payee"] = wiseDF["Merchant"]  # TODO make case to use 'Merchant' or 'Payee Name'
    homeBankDF["memo"] = wiseDF["Description"]  # TODO expand with more info from different columns
    homeBankDF["amount"] = wiseDF["Amount"]
    homeBankDF["category"] = wiseDF["Currency"]  # As Wise doesn't provide a category
    homeBankDF["tags"] = wiseDF["Currency"]  # As idk what this is

    print(homeBankDF)

    homeBankDF.to_csv(path_or_buf="wise.csv", sep=";", index=False)


# Tools
def wiseDateConverter(wiseDate):
    wiseDate = wiseDate.split("-")
    wiseDate = [int(i) for i in wiseDate]
    return "{0}-{1}-{2}".format(wiseDate[1], wiseDate[0], wiseDate[2])


def wiseIDtoPaymentCode(wiseID):
    # There was NO documentation on what this meant until I found
    # https://answers.launchpad.net/homebank/+question/664165
    # Which says that the Payment codes are the same as the Dropdown menu in HomeBank itself
    # When adding a new transaction
    """
    HomeBank CSV payment column IDs

    0: None
    1: Credit Card
    2: Cheque
    3: Cash
    4: Bank Transfer
    5: ??? Internal Transfer?
    6: Debit Card - Not sure because docs only say that 5 means internal transfer but logically 5 is debit card
    7: Standing Order
    8: Electronic Payment
    9: Deposit
    10: FI Fee
    11: Direct Debit
    """
    # TODO Add BALANCE, OVERCHARGE_INCIDENTS and CARD_ORDER_CHECKOUT
    if wiseID.startswith("TRANSFER"):
        return 4
    elif wiseID.startswith("CARD"):
        return 6
    elif wiseID.startswith("DIRECT_DEBIT"):
        return 11
    return 0


if __name__ == '__main__':
    main()
