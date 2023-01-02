import os
import pandas as pd
from yodas import Menu


def main():
    # Find CSV files
    csvFiles = []
    for file in os.listdir():
        if file.endswith(".csv") and "wise.csv" not in file:
            csvFiles.append(file)

    if len(csvFiles) > 1:
        fileSelector = Menu(csvFiles, title="Choose the CSV file you wish to convert")
        convertCSV(fileSelector.select())
    elif len(csvFiles) == 1:
        convertCSV(csvFiles[0])
    else:
        print("No files found, drop a CSV file in the directory " + os.getcwd())


def convertCSV(filePath):
    # format from http://homebank.free.fr/help/misc-csvformat.html
    wiseDF = pd.read_csv(filePath)
    wiseAsDict = wiseDF.to_dict(orient="records")

    homeBankDF = pd.DataFrame()

    homeBankDF["date"] = wiseDF["Date"].apply(lambda wiseDate: wiseDateConverter(wiseDate))

    payments = []
    for tx in wiseAsDict:
        payments.append(extractPaymentCode(tx["TransferWise ID"], tx["Description"], float(tx["Amount"])))
    homeBankDF["payment"] = payments

    homeBankDF["info"] = wiseDF["Payee Account Number"].apply(lambda IBAN: getIBAN(IBAN))
    homeBankDF["payee"] = wiseDF["Merchant"]  # TODO make case to use 'Merchant' or 'Payee Name'
    homeBankDF["memo"] = wiseDF["Description"]  # TODO expand with more info from different columns
    homeBankDF["amount"] = wiseDF["Amount"]
    homeBankDF["category"] = wiseDF["Currency"]  # As Wise doesn't provide a category
    homeBankDF["tags"] = wiseDF["Currency"]  # As idk what this is

    # print(wiseAsDict)

    homeBankDF.to_csv(path_or_buf="wise.csv", sep=";", index=False)


# Tools
def wiseDateConverter(wiseDate):
    wiseDate = wiseDate.split("-")
    wiseDate = [int(i) for i in wiseDate]
    return "{0}-{1}-{2}".format(wiseDate[1], wiseDate[0], wiseDate[2])


def getIBAN(iban):
    if type(iban) is str:
        return "IBAN: " + iban
    return ""


def extractPaymentCode(wiseID, description, amount):
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
    5: Internal Transfer
    6: Debit Card
    7: Standing Order
    8: Electronic Payment
    9: Deposit
    10: FI Fee
    11: Direct Debit
    """
    # TODO Add BALANCE
    # This goes first because Wise Charges for: is for all types
    if "Wise Charges for: " in description or wiseID.startswith("OVERCHARGE_INCIDENTS"):
        return 10
    elif wiseID.startswith("TRANSFER") and amount < 0:
        return 4
    elif wiseID.startswith("BALANCE"):
        return 5
    elif wiseID.startswith("CARD"):
        return 6
    elif wiseID.startswith("TRANSFER") and amount > 0:
        return 9
    elif wiseID.startswith("DIRECT_DEBIT"):
        return 11
    print(wiseID)
    return 0


if __name__ == '__main__':
    main()
