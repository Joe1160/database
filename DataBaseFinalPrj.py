import sqlite3
import tkinter as tk
import tkinter.messagebox as msg
conn = sqlite3.connect('demo.db')  # 會自動建立 demo.db 檔案
cur = conn.cursor()
win = tk.Tk()
win.geometry('800x500+300+200')
win.resizable(0,0)
win.title("FinalPrj")
cur.execute("DROP TABLE IF EXISTS Idol")
cur.execute("DROP TABLE IF EXISTS Concert")
cur.execute('''
CREATE TABLE IF NOT EXISTS Idol (
    EID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    GroupName TEXT,
    Entertainment TEXT
)
''')
cur.execute('''
CREATE TABLE IF NOT EXISTS Concert (
    ConcertOrder INTEGER PRIMARY KEY AUTOINCREMENT,
    GroupName TEXT NOT NULL,
    City TEXT NOT NULL,
    ConcertDate TEXT NOT NULL,
    FOREIGN KEY (GroupName) REFERENCES Idol(GroupName)
)
''')
def remove_widgets_in_range(parent, x1, y1, x2, y2):
    for widget in parent.winfo_children():
        x = widget.winfo_x()
        y = widget.winfo_y()
        if x1 <= x <= x2 and y1 <= y <= y2:
            widget.destroy()

def AddIdol():
    remove_widgets_in_range(win, 152, 102, 800, 500)
    BeginWindow.config(text = "新增Idol", font = '微軟正黑體 15')
    AddName = tk.Label(text = "新Idol姓名 : ", font = '微軟正黑體 15')
    AddName.place(x = 180,y = 125)
    Entry_AddName = tk.Entry(width = 20)
    Entry_AddName.place(x = 300,y = 132)
    AddGroupName = tk.Label(text = "所在團體 : ", font = '微軟正黑體 15')
    AddGroupName.place(x = 180,y = 200)
    Entry_AddGroupName = tk.Entry(width = 20)
    Entry_AddGroupName.place(x = 300,y = 207)
    AddCompany = tk.Label(text = "所屬公司 : ", font = '微軟正黑體 15')
    AddCompany.place(x = 180,y = 275)
    Entry_AddCompany = tk.Entry(width = 20)
    Entry_AddCompany.place(x = 300,y = 282)
    
    def insert():
        name = Entry_AddName.get().strip()
        GroupName = Entry_AddGroupName.get().strip()
        company = Entry_AddCompany.get().strip()
        if name and GroupName and company:
            cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (name, GroupName, company))
            conn.commit()
            msg.showinfo(title = "成功新增")
            AddIdol()
        else:
            msg.showerror(title = "資料不能為空")
            AddIdol()

    Confirmbtn = tk.Button(text = "確認新增", font = '微軟正黑體 12', command = insert)
    Confirmbtn.place(x = 300,y = 350)    

def RemoveIdol():
    remove_widgets_in_range(win, 152, 102, 800, 500)
    BeginWindow.config(text = "刪除Idol", font = '微軟正黑體 15')
    DelName = tk.Label(text = "刪除對象(需填姓名) : ", font = '微軟正黑體 15')
    DelName.place(x = 180,y = 125)
    Entry_DelName = tk.Entry(width = 20)
    Entry_DelName.place(x = 182,y = 160)
    # DelEID = tk.Label(text = "刪除對象(Idol編號) : ", font = '微軟正黑體 15')
    # DelEID.place(x = 400,y = 125)
    # Entry_DelEID = tk.Entry(width = 20)
    # Entry_DelEID.place(x = 400,y = 160)

    def delete():
        name = Entry_DelName.get().strip()
        # eid = Entry_DelEID.get().strip()
        def carry():
            cur.execute("DELETE FROM Idol WHERE Name = ?", (name,))
            conn.commit()
            msg.showinfo(title = "成功刪除")
            RemoveIdol()
        if name:
            text_area = tk.Text(win, height=1, width=40, state=tk.NORMAL)
            text_area.place(x = 180, y = 315)
            Person = tk.Label(text = "是否刪除", font = '微軟正黑體 15')
            Person.place(x = 180, y = 280)
            cur.execute("SELECT * FROM Idol WHERE Name = ?", (name,))
            rows = cur.fetchall()
            Yes = tk.Button(text = "是", font = '微軟正黑體 12', command = carry)
            Yes.place(x = 180, y = 350)
            Yes = tk.Button(text = "否", font = '微軟正黑體 12', command = RemoveIdol)
            Yes.place(x = 250, y = 350)
            if len(rows) == 0:
                msg.showerror(title = "資料錯誤")
                RemoveIdol()
            for row in rows:
                text_area.config(state="normal")
                text_area.insert(tk.END, str(row))
                text_area.config(state="disabled")
                text_area.see(tk.END)
        else:
            msg.showerror(title = "資料不能為空")

    Confirmbtn = tk.Button(text = "送出對象", font = '微軟正黑體 12', command = delete)
    Confirmbtn.place(x = 180,y = 220)
    #eid_to_delete = 1
    #cur.execute("DELETE FROM Idol WHERE Name = ?", (eid_to_delete,))
    #conn.commit()

def SearchALL():
    remove_widgets_in_range(win, 152, 102, 800, 500)
    BeginWindow.config(text = "查看所有Idol", font = '微軟正黑體 15')
    text_area = tk.Text(win, height=25, width=65, state=tk.NORMAL)
    text_area.place(x = 180, y = 155)
    selectresult = tk.Label(text = "搜尋結果 : ", font = '微軟正黑體 12')
    selectresult.place(x = 180,y = 125)
    cur.execute("SELECT * FROM Idol")
    rows = cur.fetchall()
    for row in rows:
        text_area.config(state="normal")
        text_area.insert(tk.END, str(row) + '\n')
        text_area.config(state="disabled")
        text_area.see(tk.END)

def SearchData():
    remove_widgets_in_range(win, 152, 102, 800, 500)
    def SelectF():
        text_area = tk.Text(win, height=20, width=45, state=tk.NORMAL)
        text_area.place(x = 460, y = 155)
        selectresult = tk.Label(text = "搜尋結果 : ", font = '微軟正黑體 12')
        selectresult.place(x = 460, y = 125)
        # eid = Entry_Acord_to_EID.get().strip()
        name = Entry_Acord_to_Name.get().strip()
        GroupName = Entry_Acord_to_GroupName.get().strip()
        CompanyName = Entry_Acord_to_CompanyName.get().strip()

        query = "SELECT * FROM Idol WHERE 1=1"
        params = []

        # if eid:
        #     query += " AND EID = ?"
        #     params.append(eid)
        if name:
            query += " AND Name LIKE ?"
            params.append('%' + name + '%')  # 支援模糊搜尋
        if GroupName:
            query += " AND GroupName LIKE ?"
            params.append('%' + GroupName + '%')
        if CompanyName:
            query += " AND Entertainment LIKE ?"
            params.append('%' + CompanyName + '%')

        cur.execute(query, params)
        rows = cur.fetchall()
        if len(rows) == 0:
            msg.showerror(title = "無結果")
        for row in rows:
            text_area.config(state="normal")
            text_area.insert(tk.END, str(row) + '\n')
            text_area.config(state="disabled")
            text_area.see(tk.END)

    BeginWindow.config(text = "搜尋Idol", font = '微軟正黑體 15')
    # Acord_to_EID = tk.Label(text = "依編號搜尋 : ", font = '微軟正黑體 15')
    # Acord_to_EID.place(x = 180,y = 125)
    # Entry_Acord_to_EID = tk.Entry(width = 20)
    # Entry_Acord_to_EID.place(x = 300,y = 132)
    Acord_to_Name = tk.Label(text = "依名字搜尋 : ", font = '微軟正黑體 15')
    Acord_to_Name.place(x = 180,y = 125)
    Entry_Acord_to_Name = tk.Entry(width = 20)
    Entry_Acord_to_Name.place(x = 300,y = 132)
    Acord_to_GroupName = tk.Label(text = "依團體搜尋 : ", font = '微軟正黑體 15')
    Acord_to_GroupName.place(x = 180,y = 200)
    Entry_Acord_to_GroupName = tk.Entry(width = 20)
    Entry_Acord_to_GroupName.place(x = 300,y = 207)
    Acord_to_CompanyName = tk.Label(text = "依公司搜尋 : ", font = '微軟正黑體 15')
    Acord_to_CompanyName.place(x = 180,y = 275)
    Entry_Acord_to_CompanyName = tk.Entry(width = 20)
    Entry_Acord_to_CompanyName.place(x = 300,y = 282)
    Confirmbtn = tk.Button(text = "送出條件", font = '微軟正黑體 12', command = SelectF)
    Confirmbtn.place(x = 300,y = 350)
    
    # cur.execute("SELECT * FROM Idol")
    # rows = cur.fetchall()
    # for row in rows:  
    #     print(row)
    
def assignTaxt():
    remove_widgets_in_range(win, 152, 102, 800, 500)
    BeginWindow.config(text = "新增演唱會", font = '微軟正黑體 15')
    def AddConcert():
        groupName = Entry_Addtaxt.get().strip()
        city = Entry_AddCity.get().strip()
        date = Entry_AddDate.get().strip()
        if groupName or city or date:
            cur.execute("SELECT * FROM Idol WHERE GroupName = ?", (groupName,))
            result = cur.fetchone()
            if result:
                cur.execute("INSERT INTO Concert (GroupName, City, ConcertDate) VALUES (?, ?, ?)", (groupName, city, date))
                conn.commit()
                msg.showinfo(title = "成功新增")
                assignTaxt()
            else:
                msg.showwarning(title = "暫無該團體")
                assignTaxt()
        else:
            msg.showwarning(title = "資料不能為空")
            assignTaxt()
    Addtaxt = tk.Label(text = "指派對象(團體) : ", font = '微軟正黑體 15')
    Addtaxt.place(x = 180,y = 125)
    Entry_Addtaxt = tk.Entry(width = 20)
    Entry_Addtaxt.place(x = 330,y = 132)
    AddCity = tk.Label(text = "選擇城市 : ", font = '微軟正黑體 15')
    AddCity.place(x = 180,y = 200)
    Entry_AddCity = tk.Entry(width = 20)
    Entry_AddCity.place(x = 330,y = 207)
    AddDate = tk.Label(text = "選擇日期 : ", font = '微軟正黑體 15')
    AddDate.place(x = 180,y = 275)
    Entry_AddDate = tk.Entry(width = 20)
    Entry_AddDate.place(x = 330,y = 282)
    Confirmbtn = tk.Button(text = "確定新增場次", font = '微軟正黑體 12', command = AddConcert)
    Confirmbtn.place(x = 300,y = 350)

def SearchConcert():
    remove_widgets_in_range(win, 152, 102, 800, 500)
    BeginWindow.config(text = "查詢演唱會場次", font = '微軟正黑體 15')
    text_area = tk.Text(win, height=25, width=65, state=tk.NORMAL)
    text_area.place(x = 180, y = 155)
    selectresult = tk.Label(text = "搜尋結果 : ", font = '微軟正黑體 12')
    selectresult.place(x = 180,y = 125)
    cur.execute("SELECT * FROM Concert")
    rows = cur.fetchall()
    if len(rows) == 0:
        msg.showwarning(title = "目前暫無演唱會資訊")
    for row in rows:
        text_area.config(state="normal")
        text_area.insert(tk.END, str(row) + '\n')
        text_area.config(state="disabled")
        text_area.see(tk.END)

def closewindow():
    win.destroy()

L_Side = tk.Canvas(win, width=150, height=500, bg="gray")
L_Side.place(x = 0, y = 0)
T_Side = tk.Canvas(win, width=650, height=100, bg="skyblue")
T_Side.place(x = 152, y = 0)
functionlayer = tk.Label(text = "功能列表 : ", font = '微軟正黑體 15')
functionlayer.place(x = 30, y = 30)
BeginWindow = tk.Label(text = "首頁", font = '微軟正黑體 15')
BeginWindow.place(x = 200, y = 30)
findIdol = tk.Button(text = "搜尋Idol", font = '微軟正黑體 12', command = SearchData)
findIdol.place(x = 30, y = 70)
IncreaseIdol = tk.Button(text = "新增Idol", font = '微軟正黑體 12', command = AddIdol)
IncreaseIdol.place(x = 30, y = 110)
DecreaseIdol = tk.Button(text = "刪除Idol", font = '微軟正黑體 12', command = RemoveIdol)
DecreaseIdol.place(x = 30, y = 150)
findAllIdol = tk.Button(text = "查看所有Idol", font = '微軟正黑體 12', command = SearchALL)
findAllIdol.place(x = 30, y = 190)
assignIdol = tk.Button(text = "開演唱會", font = '微軟正黑體 12', command = assignTaxt)
assignIdol.place(x = 30, y = 230)
SalaryAdjust = tk.Button(text = "查詢演唱會", font = '微軟正黑體 12', command = SearchConcert)
SalaryAdjust.place(x = 30, y = 270)
exitbtn = tk.Button(text = "離開", font = '微軟正黑體 12', command = closewindow)
exitbtn.place(x = 30, y = 450)


Le_sserafim = ["Sakura", "Chaewon", "Yunjin", "Kazuha", "Eunchae"]
illit = ["Wonhee", "Minju", "Yunah", "Moka", "Iroha"]
NewJeans = ["Minji", "Hanni", "Danielle", "Haerin", "Hyein"]
MissA = ["Fei", "Jia", "Min", "Suzy"]
Twice = ["Nayeon", "Jihyo", "Jeongyeon", "Mina", "Sana", "Momo", "Dahyun", "Chaeyoung", "Tzuyu"]
Itzy = ["Yeji", "Chaeryeon", "Lia", "Ryujin", "Yuna"]
Nmixx = ["Haewon", "Lily", "Sullyoon", "Bae", "Jiwoo", "Kyujin"]
Blackpink = ["Rose", "Jisoo", "Jennie", "Lisa"]
BabyMonster = ["Rami", "Pharita", "Aheyon", "Asa", "Rora", "Ruka", "Chiquita"]
Gfriend = ["Sowon", "Yerin", "Eunha", "Yuju", "SinB", "Umji"]
GirlsGeneration = ["Taeyeon", "Sunny", "Tiffany", "Hyoyeon", "Yuri", "Sooyoung", "Yoona", "Seohyun"]
RedVelvet = ["Irene", "Seulgi", "Wendy", "Yeri", "Joy"]
aespa = ["Karina", "Winter", "Ningning", "Giselle"]
i_dle = ["Soyeon", "Miyeon", "Minnie", "Yuqi", "Shuhua"]
Kissoflife = ["Julie", "Natty", "Belle", "Hanuel"]
ive = ["Yujin", "Wonyoung", "Leeseo", "Liz", "Gaeul", "Rei"]
fromis_9 = ["Hayoung", "Jiwon", "Chaeyoung", "Nagyung", "Jiheon"]
Kep1er = ["Chaehyun", "Yujin", "Dayeon", "Hikaru", "Bahiyyih", "Youngeun", "Mashiro", "Yeseo"]
Meovv = ["Sooin", "Gawon", "Anna", "Narin", "Ella"]
Izna = ["Mai", "Jeemin", "Jiyoon", "Koko", "Sarang", "Jungeun", "Saebi"]
mask = ["Jojo", "Dora", "Nini"]


for l in Le_sserafim:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (l,"Le_sserafim","Hybe"))
for i in illit:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (i,"illit","Hybe"))
for n in NewJeans:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (n,"NewJeans","Hybe"))
for m in MissA:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (m,"MissA","Jyp"))
for t in Twice:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (t,"Twice","Jyp"))
for i in Itzy:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (i,"ITZY","Jyp"))
for n in Nmixx:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (n,"Nmixx","Jyp"))
for i in i_dle:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (i,"i_idle","Cube"))
for b in Blackpink:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (b,"Blackpink","YG"))
for bm in BabyMonster:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (bm,"BabyMonster","YG"))
for g in Gfriend:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (g,"Gfriend","YGPlus"))
for g in GirlsGeneration:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (g,"RedVelvet","SM"))
for r in RedVelvet:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (r,"RedVelvet","SM"))
for a in aespa:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (a,"aespa","SM"))
for k in Kissoflife:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (k,"Kissoflife","S2"))
for i in ive:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (i,"ive","starship"))
for f in fromis_9:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (f,"fromis_9","ASND"))
for m in Meovv:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (m,"Meovv","TheBlackLabel"))
for i in Izna:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (i,"Izna","CJ ENM & TheBlackLabel"))
for k in Kep1er:
    cur.execute("INSERT INTO Idol (Name, GroupName) VALUES (?, ?)", (k,"Kep1er"))
for m in mask:
    cur.execute("INSERT INTO Idol (Name, GroupName, Entertainment) VALUES (?, ?, ?)", (m,"mask","Mask_Offical"))

conn.commit()
win.mainloop()
cur.close()
conn.close()
