import csv
from datetime import datetime

DATA_FILE = "data/expenses.csv"   # 給 B 組員讀的檔案

def add_expense():
    print("\n========================")
    print("===== 新增花費項目 =====")
    print("========================\n")

    # 日期輸入
    while True:
        date = input("請輸入日期 (YYYY-MM-DD)，或按 Enter 使用今天日期： ").strip()

        if date == "":
            date = datetime.today().strftime("%Y-%m-%d")
            break

        try:
            datetime.strptime(date, "%Y-%m-%d")
            break
        except ValueError:
            print("❌ 日期格式錯誤，請重新輸入！")

    # 金額
    while True:
        amount = input("請輸入金額： ").strip()
        try:
            amount = float(amount)
            break
        except ValueError:
            print("❌ 金額必須是數字！")

    # 分類
    category = input("請輸入分類（如 食物、交通、娛樂…）： ").strip()
    if category == "":
        category = "其他"

    # 備註（可留空）
    notes = input("備註（可留空）： ").strip()

    # 寫入 CSV
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([date, amount, category, notes])

    print("========================")
    print("✅ 新增成功！")
    print(f"已新增花費： {date} | {amount} 元 | {category} | 備註：{notes if notes else '（無）'}\n")


def main():
    print("========================")
    print("=== 歡迎來到理財幫手 ===")
    print("========================\n")

    while True:
        command = input("按 Enter 新增花費，或輸入 q 離開： ").strip().lower()
        if command == "q" or command == "Q":
            print("很高興能服務到你，歡迎再次使用理財幫手！")
            break
        add_expense()


if __name__ == "__main__":
    main()
