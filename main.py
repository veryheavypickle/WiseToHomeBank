import os
import pandas as pd
from yodas import Menu, Yoda


def main():
    # Find CSV files
    csvFiles = []
    for file in os.listdir():
        if (file.endswith(".csv") or file.endswith(".xlsx")) and "processed.csv" not in file:
            csvFiles.append(file)

    fileSelector = Menu(csvFiles, title="Choose the CSV file you wish to convert")
    if len(csvFiles) > 1:
        processCSV(fileSelector.select())
    elif len(csvFiles) == 1:
        processCSV(csvFiles[0])
    else:
        print("No files found, drop a CSV file in the directory " + os.getcwd())


def processCSV(filePath):
    # format from http://homebank.free.fr/help/misc-csvformat.html
    yoda = Yoda("config")  # Load Config

    # supportedBanks = ["Wise", "BBVA"]
    # bank = Menu(supportedBanks, title="Select the bank").select()

    if filePath.endswith(".csv"):
        bank = "Wise"
        bankDF = pd.read_csv(filePath)
    else:
        bank = "BBVA"
        bankDF = pd.read_excel(filePath, header=4)

    extractCategoriesFromVendors(bankDF, yoda, bank)
    homeBankDF = extractDFInfo(bankDF, yoda, bank)

    homeBankDF.to_csv(path_or_buf="processed.csv", sep=";", index=False)


def extractCategoriesFromVendors(bankDF, yoda, bank):
    # https://whybudgeting.com/personal-budget-categories/

    # This will create a new yoda with a list of vendors removing duplicates
    if bank == "Wise":
        listOfVendors = [*set(list(bankDF["Merchant"]))]
    else:
        listOfVendors = []
        for row in bankDF.to_dict(orient="records"):
            if row["Concepto"] == "Bizum":
                vendor = "Bizum: " + row["Movimiento"]
            elif row["Concepto"] == "Transfer completed" or row["Concepto"] == "Salary payment":
                vendor = row["Movimiento"]
            else:
                vendor = row["Concepto"]
            listOfVendors.append(vendor)

    try:
        vendors = yoda.contents()["vendors"]
    except KeyError:
        vendors = {}
    total = len(listOfVendors)
    count = 0
    try:
        for vendor in listOfVendors:
            vendor = str(vendor)
            vendorLW = vendor.lower()
            if vendor in vendors:
                category = vendors[vendor]
            elif "taxi" in vendorLW:
                category = "Transportation:Taxi Fares"
            elif "mercadona" in vendorLW or "toogoodtogo.e" in vendorLW:
                category = "Food:Groceries"
            elif "nyx*" in vendorLW:
                category = "Food:Eating Out"
            elif "ebay" in vendorLW or "aliexpress" in vendorLW:
                category = "Personal:Online Shopping"
            elif "airbnb" in vendorLW:
                category = "Entertainment:Accommodation"
            elif vendorLW == "nan":
                category = "Miscellaneous"
            else:
                category = input("\nInput a category in format 'category:subcategory' for\n({0}/{1}){2}: ".format(count, total, vendor))
            vendors[vendor] = category
            count += 1
    except KeyboardInterrupt:
        yoda.write({"vendors": vendors})
        exit(0)
    yoda.write({"vendors": vendors})


def extractDFInfo(bankDF, yoda, bank):
    bankAsDict = bankDF.to_dict(orient="records")

    homeBankDF = pd.DataFrame()

    if bank == "Wise":
        homeBankDF["date"] = bankDF["Date"].apply(lambda wiseDate: wiseDateConverter(wiseDate))
    else:
        homeBankDF["date"] = bankDF["F.Valor"].apply(lambda date: bbvaDateConverter(date))

    payments = []
    payees = []
    categories = []

    if bank == "Wise":
        for tx in bankAsDict:
            paymentCode = extractWisePaymentCode(tx["TransferWise ID"], tx["Description"], float(tx["Amount"]))
            merchant = extractMerchant(tx["Payee Name"], tx["Payer Name"], tx["Merchant"])
            category = extractCategory(merchant, yoda, paymentCode)

            payments.append(paymentCode)
            payees.append(merchant)
            categories.append(category)
    else:
        for tx in bankAsDict:
            paymentCode = extractBBVAPaymentCode(tx["Movimiento"], tx["Concepto"], float(tx["Importe"]))
            merchant = tx["Concepto"]
            category = extractCategory(merchant, yoda, paymentCode)

            payments.append(paymentCode)
            payees.append(merchant)
            categories.append(category)

    homeBankDF["payment"] = payments
    homeBankDF["payee"] = payees
    homeBankDF["category"] = categories

    if bank == "Wise":
        homeBankDF["info"] = bankDF["Payee Account Number"].apply(lambda IBAN: getIBAN(IBAN))
        homeBankDF["memo"] = bankDF["Description"]  # TODO expand with more info from different columns
        homeBankDF["amount"] = bankDF["Amount"]
        homeBankDF["tags"] = bankDF["Currency"]
    else:
        homeBankDF["info"] = bankDF["Movimiento"]
        homeBankDF["memo"] = bankDF["Observaciones"]
        homeBankDF["amount"] = bankDF["Importe"]
        homeBankDF["tags"] = bankDF["Divisa"]

    return homeBankDF


# Tools
def wiseDateConverter(wiseDate):
    wiseDate = wiseDate.split("-")
    wiseDate = [int(i) for i in wiseDate]
    return "{0}-{1}-{2}".format(wiseDate[1], wiseDate[0], wiseDate[2])


def bbvaDateConverter(timestamp):
    return "{0}-{1}-{2}".format(timestamp.month, timestamp.day, timestamp.year)


def getIBAN(iban):
    if type(iban) is str:
        return "IBAN: " + iban
    return ""


def extractMerchant(payee, payer, merchant):
    if type(merchant) is not float and type(payee) is float and type(payer) is float:
        return merchant
    elif type(payee) is not float:
        return payee
    elif type(payer) is not float:
        return payer
    return ""


def extractCategory(merchant, yoda, paymentCode):
    vendors = yoda.contents()["vendors"]
    if merchant not in vendors and merchant != "" and merchant != "Bizum":
        # for case that it is income
        category = input("Input a category in format 'category:subcategory' for: {}: ".format(merchant))
        vendors[merchant] = category
        yoda.write({"vendors": vendors})
    elif merchant != "":
        category = vendors[merchant]
    elif paymentCode == 4 or paymentCode == 9:
        category = "Income:Conversions"
    elif paymentCode == 10:
        category = "Bills:Fees"
    else:
        category = "Miscellaneous"
    return category


# Payment Codes
"""
    HomeBank CSV payment column IDs

    0: None
    1: Credit Card
    2: Cheque
    3: Cash
    4: Bank Transfer
    5: Internal Transfer - Don't Use
    6: Debit Card
    7: Standing Order
    8: Electronic Payment
    9: Deposit
    10: FI Fee
    11: Direct Debit
"""


def extractWisePaymentCode(wiseID, description, amount):
    # There was NO documentation on what this meant until I found
    # https://answers.launchpad.net/homebank/+question/664165
    # Which says that the Payment codes are the same as the Dropdown menu in HomeBank itself
    # When adding a new transaction

    # This goes first because Wise Charges for: is for all types
    if "Wise Charges for: " in description or wiseID.startswith("OVERCHARGE_INCIDENTS"):
        return 10
    elif (wiseID.startswith("TRANSFER") or wiseID.startswith("BALANCE"))and amount < 0:
        # This will regard conversions from euros as bank transfers
        return 4
    elif wiseID.startswith("CARD"):
        return 6
    elif (wiseID.startswith("TRANSFER") or wiseID.startswith("BALANCE")) and amount > 0:
        # This will regard conversions to euros as bank deposits
        return 9
    elif wiseID.startswith("DIRECT_DEBIT"):
        return 11
    print(wiseID)
    return 0


def extractBBVAPaymentCode(movement, concept, amount):
    if movement.startswith("Enviado: ") and concept == "Bizum":
        return 4
    elif concept == "Transfer completed" and amount < 0:
        return 4
    elif movement == "Card payment":
        return 6
    elif movement == "Transfer received" and concept.startswith("Deposit- "):
        return 9
    elif movement.startswith("Recibido: ") and concept == "Bizum":
        return 9
    elif concept == "Salary payment":
        return 9
    print(movement)
    return 0


if __name__ == '__main__':
    main()
