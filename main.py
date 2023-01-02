import os
from yodas import Menu


def main():
    # Find CSV files
    csvFiles = []
    for file in os.listdir():
        if file.endswith(".csv"):
            csvFiles.append(file)

    if len(csvFiles) > 1:
        fileSelector = Menu(csvFiles, title="Choose the CSV file you wish to convert")
        convertCSV(fileSelector.select())
    else:
        print("No files found, drop a CSV file in the directory " + os.getcwd())


def convertCSV(filePath):
    print(filePath)


if __name__ == '__main__':
    main()
