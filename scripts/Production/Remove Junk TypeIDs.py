import sqlite3
from loadConfig import load_config

global config
config = load_config()

db_path = config["dbPath"]

def main():
    data = list()
    with open("Junk typeIDs to remove from DB each update.txt", 'r', encoding='utf-8') as file:
        for line in file:
            data.append(line.strip().split('\t'))
    
    for line in data:
        line[0] = int(line[0])

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for line in data:
        query = f"delete from Items where typeID = {line[0]}"
        cursor.execute(query)
        conn.commit()

    print("all done")

    conn.close()

main()