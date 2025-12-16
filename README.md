# 花費記錄系統（Expense Tracker）

本專案提供兩個功能：
1. 輸入花費資料
2. 依分類產生圓餅圖

---

## 安裝方式

* 如果需要顯示圓餅圖，請先安裝 matplotlib：

`pip install matplotlib`

* 請確認專案中有 `data` 資料夾，花費資料會存入：

`data/expenses.csv`

---

## 使用方式

### 1. 執行輸入花費程式

`python src/input.py`

程式會讓你輸入：
- 日期（YYYY-MM-DD，Enter 可使用今日）
- 金額
- 分類
- 備註（可留空）

輸入的資料會自動寫入 `expenses.csv`。

---

### 2. 執行花費分類圓餅圖

`python src/visualize.py`


此程式會讀取 `data/expenses.csv`，並依分類顯示圓餅圖。

---

## 範例資料格式（expenses.csv）

`2025-03-14,120,食物,午餐`
`2025-03-14,30,交通,搭公車`
`2025-03-15,300,娛樂,看電影`