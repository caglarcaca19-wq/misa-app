import flet as ft
import urllib.request
import json
import threading
import os
import datetime

API_KEY = "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"
URL = "https://openrouter.ai/api/v1/chat/completions"
CHATS_FILE = "ai_chats.json"

THEMES = {
    "Classic Light": {"bg": "#ffffff", "sidebar": "#f9f9f9", "text": "#2f2f2f", "muted": "#6e6e80", "border": "#e5e5e5", "bubble": "#f4f4f4", "input": "#f4f4f5", "accent": "#10a37f"},
}

class ChatManager:
    def __init__(self):
        self.chats = []
        self.current_chat_id = None
        self.load_chats()

    def load_chats(self):
        try:
            if os.path.exists(CHATS_FILE):
                with open(CHATS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.chats = data.get("chats", [])
                    self.current_chat_id = data.get("current_chat_id")
        except Exception:
            self.chats = []
            self.current_chat_id = None

    def save_chats(self):
        try:
            data = {"chats": self.chats, "current_chat_id": self.current_chat_id}
            with open(CHATS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def create_new_chat(self, title="Yeni Sohbet"):
        chat_id = str(int(datetime.datetime.now().timestamp()))
        new_chat = {"id": chat_id, "title": title, "messages": []}
        self.chats.insert(0, new_chat)
        self.current_chat_id = chat_id
        self.save_chats()
        return chat_id

    def delete_chat(self, chat_id):
        self.chats = [c for c in self.chats if c["id"] != chat_id]
        if self.chats:
            self.current_chat_id = self.chats[0]["id"]
        else:
            self.create_new_chat()
        self.save_chats()

    def get_current_chat(self):
        for chat in self.chats:
            if chat["id"] == self.current_chat_id:
                return chat
        if not self.chats:
            self.create_new_chat()
            return self.chats[0]
        self.current_chat_id = self.chats[0]["id"]
        return self.chats[0]

    def add_message(self, role, content):
        chat = self.get_current_chat()
        if chat:
            chat["messages"].append({"role": role, "content": content})
            self.save_chats()

def get_ai_response(messages):
    try:
        formatted_messages = [{"role": "system", "content": "Sen yardımsever ve doğrudan yanıt veren bir yapay zeka asistanısın."}]
        for m in messages[-12:]:
            formatted_messages.append({"role": m["role"], "content": m["content"]})
            
        payload = {
            "model": "deepseek/deepseek-r1",
            "messages": formatted_messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "FletAI"
        }
        req = urllib.request.Request(URL, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=50) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        return f"API Hatası ({e.code}): {error_body or e.reason}"
    except Exception as e:
        return f"Bağlantı Hatası: {str(e)}"

def main(page: ft.Page):
    page.title = "Ultimate AI Asistan"
    page.padding = 0
    page.window_maximized = True

    palette = THEMES["Classic Light"]
    page.bgcolor = palette["bg"]

    chat_mgr = ChatManager()
    if not chat_mgr.chats:
        chat_mgr.create_new_chat()

    def show_snack(text):
        try:
            snack = ft.SnackBar(ft.Text(text, color="#ffffff"), bgcolor=palette["accent"])
            page.overlay.append(snack)
            snack.open = True
            page.update()
        except Exception:
            pass

    chat_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
    chat_log = ft.ListView(expand=True, spacing=20, auto_scroll=True, padding=20)

    def update_chat_list():
        chat_list.controls.clear()
        for chat in chat_mgr.chats:
            is_active = chat["id"] == chat_mgr.current_chat_id
            chat_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=15, color=palette["muted"]),
                        ft.Text(chat["title"], size=13, color=palette["text"], overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=15,
                            icon_color=palette["muted"],
                            tooltip="Sohbeti Sil",
                            on_click=lambda e, cid=chat["id"]: [chat_mgr.delete_chat(cid), update_chat_list(), update_chat()]
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=8),
                    padding=8,
                    bgcolor=palette["border"] if is_active else None,
                    border_radius=6,
                    on_click=lambda e, cid=chat["id"]: [setattr(chat_mgr, 'current_chat_id', cid), update_chat_list(), update_chat()],
                    ink=True
                )
            )
        page.update()

    def send_message(e=None):
        user_msg = msg_input.value.strip()
        if not user_msg:
            return

        msg_input.value = ""
        msg_input.hint_text = "Mesajınızı yazın... (Enter ile gönder)"
        
        chat_mgr.add_message("user", user_msg)
        update_chat()
        
        curr_chat = chat_mgr.get_current_chat()
        if len(curr_chat["messages"]) == 1:
            curr_chat["title"] = user_msg[:30] if user_msg else "Yeni Sohbet"
            chat_mgr.save_chats()
            update_chat_list()
        
        page.update()
        
        def background_ai_call():
            try:
                response = get_ai_response(curr_chat["messages"])
                chat_mgr.add_message("assistant", response)
                update_chat()
            except Exception as ex:
                print(ex)

        threading.Thread(target=background_ai_call, daemon=True).start()

    msg_input = ft.TextField(
        hint_text="Mesajınızı yazın... (Enter ile gönder)",
        expand=True,
        border=ft.InputBorder.NONE,
        color=palette["text"],
        text_size=15,
        cursor_color=palette["text"],
        multiline=True,
        min_lines=1,
        max_lines=5,
        on_submit=send_message
    )

    def update_chat():
        chat_log.controls.clear()
        curr_chat = chat_mgr.get_current_chat()
        
        if not curr_chat["messages"]:
            chat_log.controls.append(
                ft.Column([
                    ft.Container(height=60),
                    ft.Row([
                        ft.Text("Merhaba! Bugün size nasıl yardımcı olabilirim?", size=24, weight=ft.FontWeight.BOLD, color=palette["text"])
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        else:
            for msg in curr_chat["messages"]:
                is_user = msg["role"] == "user"
                if is_user:
                    chat_log.controls.append(
                        ft.Row([
                            ft.Container(
                                content=ft.Text(msg["content"], color=palette["text"], size=15),
                                bgcolor=palette["bubble"],
                                padding=15,
                                border_radius=16,
                                width=680
                            )
                        ], alignment=ft.MainAxisAlignment.END)
                    )
                else:
                    chat_log.controls.append(
                        ft.Row([
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.Icon(ft.Icons.AUTO_AWESOME, size=16, color="#ffffff"),
                                        bgcolor=palette["accent"],
                                        padding=6,
                                        border_radius=12
                                    ),
                                    ft.Text(msg["content"], color=palette["text"], size=15, expand=True)
                                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START, spacing=12),
                                width=780,
                                padding=10
                            )
                        ], alignment=ft.MainAxisAlignment.START)
                    )
        page.update()

    sidebar = ft.Container(
        width=260,
        bgcolor=palette["sidebar"],
        padding=10,
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ADD, size=16, color=palette["text"]),
                        ft.Text("Yeni Sohbet", size=13, color=palette["text"], weight=ft.FontWeight.W_500)
                    ], spacing=8),
                    expand=True,
                    padding=10,
                    bgcolor=palette["bg"],
                    border_radius=8,
                    border=ft.Border.all(1, palette["border"]),
                    on_click=lambda e: [chat_mgr.create_new_chat(), update_chat_list(), update_chat()],
                    ink=True
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            ft.Text("Sohbet Geçmişi", size=11, color=palette["muted"], weight=ft.FontWeight.BOLD),
            ft.Container(content=chat_list, expand=True),
            ft.Divider(color=palette["border"], height=1),
            ft.Row([
                ft.Row([
                    ft.CircleAvatar(content=ft.Text("K", color="#ffffff"), bgcolor=palette["accent"], radius=14),
                    ft.Text("Kullanıcı", size=13, color=palette["text"], weight=ft.FontWeight.W_500)
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=4)
    )

    msg_input_container = ft.Container(
        content=ft.Column([
            msg_input,
            ft.Row([
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ATTACH_FILE, 
                        icon_size=20, 
                        icon_color=palette["muted"], 
                        tooltip="Dosya Ekle",
                        on_click=lambda e: show_snack("Dosya ekleme alanı")
                    ),
                    ft.IconButton(
                        icon=ft.Icons.MIC_NONE, 
                        icon_size=20, 
                        icon_color=palette["muted"], 
                        tooltip="Sesli Komut",
                        on_click=lambda e: show_snack("Sesli mod aktif")
                    ),
                ], spacing=0),
                ft.Container(
                    content=ft.Icon(ft.Icons.ARROW_UPWARD, size=16, color="#ffffff"),
                    bgcolor=palette["accent"],
                    padding=6,
                    border_radius=20,
                    on_click=send_message,
                    ink=True
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=5),
        bgcolor=palette["input"],
        padding=12,
        border_radius=16,
        border=ft.Border.all(1, palette["border"])
    )

    main_chat = ft.Container(
        expand=True,
        bgcolor=palette["bg"],
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Text("AI Asistan", size=16, weight=ft.FontWeight.BOLD, color=palette["text"]),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_SWEEP, 
                        icon_size=18, 
                        icon_color=palette["muted"],
                        tooltip="Geçmişi Temizle",
                        on_click=lambda e: [chat_mgr.chats.clear(), chat_mgr.create_new_chat(), update_chat_list(), update_chat(), show_snack("Geçmiş sıfırlandı.")]
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=12,
            ),
            chat_log,
            ft.Container(
                content=ft.Column([
                    msg_input_container,
                    ft.Text("Yapay zeka asistanı hata yapabilir.", size=11, color=palette["muted"], text_align=ft.TextAlign.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                padding=20,
                bgcolor=palette["bg"]
            )
        ], spacing=0)
    )

    update_chat_list()
    update_chat()
    page.add(ft.Row([sidebar, main_chat], expand=True, spacing=0))

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except Exception as ex:
        print(f"\n[HATA OLUŞTU]: {ex}")
    
    # CMD penceresinin aniden kapanmasını kesin olarak önler
    input("\nProgram sonlandı veya kapatıldı. Çıkmak için Enter tuşuna basın...")