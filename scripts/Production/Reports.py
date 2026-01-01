import os

def createDirectory(path):
    os.makedirs(path, exist_ok = True)

def createFile(fileName):
    os.makedirs
    file = open(f"{fileName}.txt", "w")
    file.close()
    file = open(f"{fileName}.txt", "a")
    return file

def appendFile(file, message):
    # file = open(f"{fileName}.txt", "a")
    file.write(message + " ")
    #file.close()
    
def newLine(file):
    # file = open(f"{fileName}.txt", "a")
    file.write("\n")
    #file.close()

def closeFile(file):
    file.close()


def mainloop():
    file = createFile("afile")
    appendFile(file, "text")
    newLine(file)
    appendFile(file, "text")
    closeFile(file)


mainloop()