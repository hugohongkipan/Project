from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)  # __name__ 代表目前執行的模組
app.json.ensure_ascii = False  # 避免中文亂碼

DB_NAME = "membership.db"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register",  methods=["GET", "POST"])
def register():
    """
    處理用戶註冊邏輯，顯示註冊表單並接收輸入資訊。
    若資料不完整或用戶名已存在，顯示錯誤訊息。
    註冊成功後導向登入頁面。
    """
    # 提供表單，包含「用戶名」、「電子郵件」、「密碼」、「手機」、「出生年月日」輸入欄位，
    # 使用 POST 方法提交
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        phone = request.form.get("phone", "").strip()
        birthdate = request.form.get("birthdate", "").strip()

        # 用戶名、電子郵件或密碼是否為空，若為空，顯示錯誤頁面，
        # 提示「請輸入用戶名、電子郵件和密碼」
        if not username or not email or not password:
            return redirect(url_for("error", message="請輸入用戶名、電子郵件和密碼"))

        conn = connect_db()
        cursor = conn.cursor()

        # 用戶名是否已存在於資料庫中，若存在，顯示錯誤頁面，提示「用戶名已存在」
        cursor.execute("""SELECT username FROM members WHERE username = ?""",
                       (username, ))

        if cursor.fetchone() is None:
            # 將所有欄位資料儲存至 membership.db 的 members 表（iid 自動產生）
            # 並重定向至登入頁面
            cursor.execute("""
                           INSERT INTO members (username, email, password,
                           phone, birthdate) VALUES (?, ?, ?, ?, ?)
                           """, (username, email, password, phone, birthdate))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        else:
            conn.close()
            return redirect(url_for("error", message="用戶名已存在"))

    return render_template("register.html")


@app.route("/login",  methods=["GET", "POST"])
def login():
    """
    處理登入表單的提交，驗證電子郵件與密碼。
    若資料不符則顯示錯誤頁面。
    驗證成功則導向歡迎頁。
    """
    # 提供表單，包含「電子郵件」和「密碼」輸入欄位，使用 POST 方法提交
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # 電子郵件或密碼是否為空，若為空，顯示錯誤頁面，提示「請輸入電子郵件和密碼」
        if not email or not password:
            return redirect(url_for("error", message="請輸入電子郵件和密碼"))

        # 電子郵件和密碼是否與 members 表中的記錄匹配
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""SELECT username, email, password FROM members
                       WHERE email = ? and password = ?""",
                       (email, password))

        cf = cursor.fetchone()
        if cf is None:
            # 若不匹配，顯示錯誤頁面，提示「電子郵件或密碼錯誤」
            conn.close()
            return redirect(url_for("error", message="電子郵件或密碼錯誤"))
        else:
            username = cf[0]
            conn.close()
            return redirect(url_for("welcome", username=username))

    return render_template("login.html")


@app.route("/error")
def error():
    """
    顯示錯誤訊息頁面，從 query string 取得錯誤訊息內容。
    """
    message = request.args.get("message", "發生未知錯誤")
    return render_template("error.html", message=message)


# 渲染歡迎頁面，顯示「歡迎，用戶名}！」，
# 使用 `{{ username add_stars }為用戶名添加星號（例如admin顯示為★admin★`）
@app.template_filter("add_stars")
def add_stars(s):
    return f"歡迎，★{s}★！"


@app.route("/welcome")
def welcome():
    """
    顯示登入成功後的歡迎頁，並根據用戶名稱查詢其 iid
    """
    username = request.args.get("username")
    conn = connect_db()
    cursor = conn.cursor()
    username = request.args.get("username")

    cursor.execute("SELECT iid FROM members WHERE username = ?", (username,))
    cf = cursor.fetchone()[0]
    iid = int(cf)

    return render_template("welcome.html", username=username, iid=iid)


@app.route("/edit_profile/<int:iid>", methods=["GET", "POST"])
def edit_profile(iid):
    """
    編輯會員資料，GET 顯示原始資料，POST 儲存修改後的內容。
    """
    conn = connect_db()
    cursor = conn.cursor()

    if request.method == "GET":
        cursor.execute("""SELECT iid, username, email, phone, birthdate
                       FROM members WHERE iid = ?""", (iid,))
        member = cursor.fetchone()
        if member is None:
            return redirect(url_for("error", message="找不到該用戶"))
        return render_template("edit_profile.html", member=member)

    # 使用 POST 方法提交
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        phone = request.form.get("phone", "").strip()
        birthdate = request.form.get("birthdate", "").strip()

        # 電子郵件和密碼是否為空，若為空，顯示錯誤頁面，提示「請輸入電子郵件和密碼」
        if not email or not password:
            return redirect(url_for("error", message="請輸入電子郵件和密碼"))

        # 電子郵件是否已被其他用戶使用（不包括當前 iid），
        # 若已被使用，顯示錯誤頁面，提示「電子郵件已被使用」。
        cursor.execute("""SELECT email FROM members
                       WHERE email = ? AND iid != ?""", (email, iid))
        if cursor.fetchone() is not None:
            conn.close()
            return redirect(url_for("error", message="電子郵件已被使用"))

        # 若通過檢查，更新 members 表中對應 iid 的資料，並重定向至歡迎頁面
        cursor.execute("""
                       UPDATE members SET email = ?, password = ?,
                       phone = ?, birthdate = ? WHERE iid = ?
                       """, (email, password, phone, birthdate, iid))
        conn.commit()
        conn.close()
        return redirect(url_for("welcome", username=username))

    return render_template("edit_profile.html")


# 刪除會員
@app.route("/delete_user/<iid>")
def delete_user(iid):
    """
    根據 iid 刪除會員資料後導回首頁。
    """
    # 若用戶點擊「確認」，則向 /delete/<iid> 發送請求，
    # 刪除 members 表中對應 iid 的記錄，並重定向至首頁
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM members WHERE iid = ?", (iid,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


def connect_db() -> sqlite3.Connection:
    """
    建立並回傳與 SQLite 資料庫的連線物件

    Returns:
        sqlite3.Connection: 資料庫連線物件
    """
    conn = sqlite3.connect(DB_NAME)  # 連線資料庫
    conn.row_factory = sqlite3.Row  # 設置row_factory
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    初始化資料庫，建立所需的資料表與範例資料

    Args:
        conn (sqlite3.Connection): 資料庫連線物件
    """
    cursor = conn.cursor()  # 建立 cursor 物件
    try:
        # 建立範例資料表
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS members (
            iid INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            phone TEXT,
            birthdate TEXT
        );
        INSERT OR IGNORE INTO members (username, email, password,
                                       phone, birthdate)
        VALUES ('admin', 'admin@example.com', 'admin123',
                '0912345678', '1990-01-01');
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"=> 初始化資料表失敗：{e}")
        conn.rollback()


# 不要用__name__ == "__main__"，用flask run跑不進去，和啟動方式相關
with connect_db() as conn:
    init_db(conn)
