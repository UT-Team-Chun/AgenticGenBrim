import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk


class RedirectOutputToText:
    """
    print()の出力をTextウィジェットにリダイレクトするクラス
    """

    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        """
        文字列をTextウィジェットに書き込む
        """
        current_time = time.strftime("%H:%M:%S")  # 現在時刻を時:分:秒の形式で取得
        message = f"[{current_time}] [INFO] {string}"
        # 各種タグの色を設定（情報、成功、警告、エラー）
        self.text_widget.tag_config("info", foreground="dodgerblue")
        self.text_widget.tag_config("success", foreground="green")
        self.text_widget.tag_config("warning", foreground="orange")
        self.text_widget.tag_config("error", foreground="red")
        # テキストウィジェットにメッセージを追加
        if "Starting the export." in string:
            message = f"[{current_time}] {string}"
            self.text_widget.insert(tk.END, message + "\n", "info")
        elif "Export completed." in string:
            message = f"[{current_time}] {string}"
            self.text_widget.insert(tk.END, message + "\n", "success")
        else:
            self.text_widget.insert(tk.END, string + "\n", "warning")

        self.text_widget.see(tk.END)  # Textウィジェットを最下部までスクロール

    def flush(self):
        """
        flush処理（この実装では不要）
        """
        pass  # flush処理は不要


class FileSelectorApp:
    """
    ファイル選択とIFCエクスポートを行うGUIアプリケーション
    ExcelファイルまたはJSONファイルから鋼橋のIFCモデルを生成する
    """

    def __init__(self, master):
        """
        アプリケーションの初期化
        Args:
            master: Tkinterのルートウィンドウ
        """
        self.master = master
        self.master.title("iEGI-IMG Export Girder IFC-ver 1.00 pub 20250616")

        # ウィンドウサイズの設定
        self.window_width = 800
        self.window_height = 500

        # ウィンドウを画面中央に配置するための座標計算
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        x = (screen_width // 2) - (self.window_width // 2)
        y = (screen_height // 2) - (self.window_height // 2) - 100
        master.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")

        # 背景画像の設定
        self.original_bg_image = Image.open(
            self.get_resource_path("background.png")
        )  # get_resource_path関数を使用してリソースパスを取得
        self.bg_image = self.original_bg_image.resize((self.window_width, self.window_height), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        # すべてのウィジェットを含むフレームの作成
        self.frame = tk.Frame(master)
        self.frame.pack(fill=tk.BOTH, expand=True)  # フレームがウィンドウ全体を埋めるように拡張

        # 背景画像を表示するラベル
        self.bg_label = tk.Label(self.frame, image=self.bg_photo)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)  # 背景画像を配置

        # ファイルパスを表示するラベル（枠付き）
        self.file_path_label = tk.Label(
            self.frame, text="No file selected.", bg="#A8A8A8", wraplength=290, relief="solid", borderwidth=1
        )
        self.file_path_label.grid(
            row=0, column=0, columnspan=2, pady=(12, 0), padx=(20, 100), sticky="ew"
        )  # ラベルを0行0列に配置し、横方向に拡張

        # Browseボタン
        self.browse_button = tk.Button(
            self.frame, text="Browse", command=self.browse_file, bg="#F0F0F0", width=8, height=1
        )
        self.browse_button.grid(row=0, column=1, padx=(0, 10), pady=(10, 0), sticky="e")  # Browseボタンを0行1列に配置

        # ExportボタンとCancelボタンを配置する行の設定
        self.frame.grid_rowconfigure(1, weight=1)  # 1行目の重みを設定

        # Exportボタン
        self.export_button = tk.Button(
            self.frame, text="Export", command=self.export_action, bg="#F0F0F0", width=10, height=2
        )
        self.export_button.grid(row=2, column=0, padx=(100, 0), pady=(0, 50), sticky="w")  # Exportボタンを2行0列に配置

        # Cancelボタン
        self.cancel_button = tk.Button(
            self.frame, text="Cancel", command=self.cancel_action, bg="#F0F0F0", width=10, height=2
        )
        self.cancel_button.grid(row=2, column=1, padx=(0, 100), pady=(0, 50), sticky="e")  # Cancelボタンを2行1列に配置

        # 経過時間を表示する時計ラベル（枠付き）
        self.clock_label = tk.Label(
            self.frame,
            text="00:00:00",
            width=8,
            height=1,
            relief="solid",
            borderwidth=1,
            bg="white",
            font=("Arial", 15),
        )
        self.clock_label.grid(
            row=1, column=0, columnspan=2, pady=(200, 0), padx=(100, 100), sticky="n"
        )  # 時計ラベルを1行に配置

        # メッセージを表示するTextウィジェットの設定
        self.output_text = tk.Text(
            self.frame, height=12, width=80, bg="black", fg="white", wrap="word", relief="solid", borderwidth=1
        )
        self.output_text.grid(
            row=1, column=0, columnspan=2, pady=(230, 10), padx=(100, 100), sticky="nsew"
        )  # Textウィジェットを1行に配置し、列方向に拡張

        # グリッドの列設定
        self.frame.grid_columnconfigure(0, weight=1)  # 0列目に重みを設定して拡張可能にする
        self.frame.grid_columnconfigure(1, weight=1)  # 1列目に重みを設定して拡張可能にする

        # 時間制御用の変数
        self.start_time = 0
        self.is_running = False

        # ウィンドウサイズ変更イベントをresize_background関数にリンク
        self.previous_size = (self.master.winfo_width(), self.master.winfo_height())
        self.master.bind("<Configure>", self.on_resize)

        # print()の出力をTextウィジェットにリダイレクト
        sys.stdout = RedirectOutputToText(self.output_text)

    def log_message(self, message, is_traceback=False, color=None):
        """
        メッセージをTextウィジェットにログ出力する
        Args:
            message: 出力するメッセージ
            is_traceback: トレースバックかどうか
            color: メッセージの色
        """
        self.output_text.configure(state=tk.NORMAL)  # Textウィジェットを編集可能にする
        if is_traceback and color:  # トレースバックで色指定がある場合
            self.output_text.tag_configure("traceback", foreground=color)  # タグの色を設定
            self.output_text.insert(tk.END, message, "traceback")  # 色付きタグでメッセージを挿入
        else:
            self.output_text.insert(tk.END, message)  # 通常のメッセージを挿入
        self.output_text.insert(tk.END, "\n")
        self.output_text.see(tk.END)  # 最下部までスクロール

    def on_resize(self, event):
        """
        ウィンドウサイズ変更時のイベントハンドラ
        """
        # ウィンドウサイズが変更されたか確認
        new_size = (self.master.winfo_width(), self.master.winfo_height())
        if new_size != self.previous_size:
            self.previous_size = new_size
            self.master.after(1, self.resize_background)  # パフォーマンス向上のため、リサイズを遅延実行

    def resize_background(self):
        """
        背景画像をウィンドウサイズに合わせてリサイズする
        """
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()

        resized_image = self.original_bg_image.resize((window_width, window_height), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized_image)
        self.bg_label.config(image=self.bg_photo)  # 背景画像を更新

    def browse_file(self):
        """
        ファイル選択ダイアログを開く
        """
        file_name = filedialog.askopenfilename()
        if file_name:
            self.file_path_label.config(text=file_name)
            print(f"Selected file: {file_name}")

    def export_action(self):
        """
        Exportボタンが押されたときの処理
        IFCエクスポート処理を開始する
        """
        file_path = self.file_path_label.cget("text")
        if file_path != "No file selected.":
            location, name_file = file_path.rsplit("/", 1)
            Location = location + "/"
            NameFile = name_file
            self.log_message("Starting export process...")
            # タイマーを開始
            self.is_running = True
            self.start_time = time.time()  # 開始時刻を記録
            threading.Thread(target=self.run_bridge, args=(Location, NameFile)).start()  # RunBridgeを別スレッドで実行
            self.update_clock()  # 時計を更新
            self.export_button.config(state=tk.NORMAL)
        else:
            messagebox.showwarning("Warning", "Please select a file first.")
            print("Warning: No file selected.")

    def run_bridge(self, Location, NameFile):
        """
        DefBridge.RunBridgeを実行してIFCモデルを生成する
        Args:
            Location: ファイルのディレクトリパス
            NameFile: ファイル名
        """
        self.export_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
        # RunBridgeを実行し、完了時にタイマーを停止
        from bridge_bim.core import DefBridge

        try:
            DefBridge.RunBridge(Location, NameFile)
            self.log_message(
                "Export completed successfully.", is_traceback=True, color="#32CD32"
            )  # メッセージの色を緑に変更
        except Exception:
            import traceback

            # 詳細なエラー情報を記録するため、トレースバックを取得
            tb_message = traceback.format_exc()  # トレースバックを取得
            # コマンドプロンプトにもエラーを出力
            print("=" * 60)
            print("エラーが発生しました:")
            print(tb_message)
            print("=" * 60)
            # GUIにもエラーを表示
            self.log_message("Detailed Error:", is_traceback=True, color="red")  # エラーメッセージを赤で表示
            self.log_message(tb_message, is_traceback=True, color="red")  # トレースバックを赤で表示
        finally:
            self.is_running = False
            self.export_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.NORMAL)

    def update_clock(self):
        """
        経過時間を更新し、時計の枠の色を変更する
        """
        if self.is_running:
            elapsed_time = time.time() - self.start_time  # 経過時間を計算
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            milliseconds = int((elapsed_time * 100) % 100)  # ミリ秒の下2桁を取得

            # 時間をmm:ss形式で表示
            self.clock_label.config(text=f"{minutes:02}:{seconds:02}:{milliseconds:02}")

            # 秒ごとに枠の色を変更
            border_colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FFA500", "#00FFFF"]
            current_color = border_colors[seconds % len(border_colors)]
            self.clock_label.config(highlightbackground=current_color, bg=current_color, highlightthickness=2)

            self.master.after(10, self.update_clock)  # 10ミリ秒後に再度更新

    def get_resource_path(self, relative_path):
        """
        リソースファイル（背景画像など）のパスを取得する
        EXE形式で実行されている場合は一時フォルダのパスを返す

        Args:
            relative_path: リソースファイルの相対パス

        Returns:
            リソースファイルの絶対パス
        """
        try:
            base_path = sys._MEIPASS  # EXE形式で実行されている場合の一時パス
        except AttributeError:
            base_path = os.path.dirname(os.path.abspath(__file__))  # 通常のスクリプト実行時のパス
        return os.path.join(base_path, relative_path)  # 完全なパスを返す

    def cancel_action(self):
        """
        Cancelボタンが押されたときの処理
        アプリケーションを終了する
        """
        self.master.quit()  # アプリケーションを終了


def resource_path(relative_path):
    """
    実行可能ファイルまたはソースコードから実行されている場合のファイルパスを取得する

    Args:
        relative_path: リソースファイルの相対パス

    Returns:
        リソースファイルの完全なパス
    """
    try:
        base_path = sys._MEIPASS  # EXE形式で実行されている場合
    except AttributeError:
        base_path = os.path.abspath(".")  # ソースコードから実行されている場合

    full_path = os.path.join(base_path, relative_path)
    return full_path


if __name__ == "__main__":
    """
    メインエントリーポイント
    GUIアプリケーションを起動する
    """
    root = tk.Tk()
    app = FileSelectorApp(root)
    # アイコン画像を読み込む
    icon_path = resource_path("icon.ico")
    icon = Image.open(icon_path)
    icon = ImageTk.PhotoImage(icon)

    # ウィンドウにアイコンを設定
    root.iconphoto(False, icon)

    root.mainloop()  # GUIイベントループを開始
