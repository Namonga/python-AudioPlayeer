import sys, os, re, json
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QObject, pyqtSlot, QPoint
from PyQt6.QtWebChannel import QWebChannel
from logic import LogicHandler

SVG_FILENAME, S, DEBUG = "new_testlayout.svg", 6.5, False

class Bridge(QObject):
    def __init__(self, w):
        super().__init__()
        self.w = w
        self.h = LogicHandler(w)

    @pyqtSlot(str)
    def log(self, d):
        if DEBUG: print(f"DEBUG: {d}")
        self.h.handle_click(d)

    @pyqtSlot(int, int)
    def start_drag(self, x, y): self.w.d_pos = QPoint(x, y)
    
    @pyqtSlot()
    def stop_drag(self): self.w.d_pos = None
    
    @pyqtSlot(int, int)
    def move_window(self, x, y):
        if self.w.d_pos:
            p = QPoint(x, y)
            self.w.move(self.w.pos() + p - self.w.d_pos)
            self.w.d_pos = p

class TransparentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.d_pos = None
        self.scale = S
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.browser = QWebEngineView(self)
        self.browser.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.setCentralWidget(self.browser)

        path = os.path.join(os.path.dirname(__file__), SVG_FILENAME)
        svg_content = open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""
        self.wb = float((re.search(r'width="([\d\.]+)"', svg_content) or [0, "100"])[1])
        self.hb = float((re.search(r'height="([\d\.]+)"', svg_content) or [0, "100"])[1])
        
        self.update_window_size()

        self.channel, self.bridge = QWebChannel(), Bridge(self)
        self.channel.registerObject("pyapi", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        
        self.browser.setHtml(self.get_html(svg_content))

    def get_html(self, svg):
        return f"""
        <!DOCTYPE html><html><head><style>
            html, body {{ margin: 0; overflow: hidden; background: transparent; width: 100%; height: 100%; user-select: none; }}
            #c {{ transform: scale({self.scale}); transform-origin: 0 0; width: {self.wb}px; height: {self.hb}px; transition: 0.2s; }}
            [show_on] {{ visibility: hidden; }}
            [transparent="true"] {{ pointer-events: none; }}
            [draggable="true"] {{ cursor: move; }}
            .debug-act:not([fill="none"]) {{ fill: red !important; }}
            .debug-act:not([stroke="none"]) {{ stroke: red !important; }}
            text.debug-act {{ fill: red !important; }}
        </style></head><body><div id="c">{svg}</div>
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script><script>
            let api, drag = !1, last;
            new QWebChannel(qt.webChannelTransport, c => {{ api = c.objects.pyapi; updateUI("event_pause"); }});
            window.updateUI = ev => document.querySelectorAll('[show_on]').forEach(el => 
                el.style.visibility = el.getAttribute('show_on') === ev ? 'visible' : 'hidden');
            document.onmousedown = e => {{ 
                if(e.target.getAttribute('draggable')=='true') {{ drag=!0; api.start_drag(e.screenX, e.screenY); }} 
            }};
            document.onmousemove = e => drag && api.move_window(e.screenX, e.screenY);
            document.onmouseup = () => {{ drag=!1; api.stop_drag(); }};
            document.onclick = e => {{
                let t = e.target;
                if (t.tagName == 'svg' || drag) return;
                if ({str(DEBUG).lower()}) {{
                    if (last) last.classList.remove('debug-act');
                    t.classList.add('debug-act'); last = t;
                }}
                let a = {{tag: t.tagName}}; 
                [...t.attributes].forEach(x => {{ if(x.name!='class') a[x.name] = x.value }});
                api.log(JSON.stringify(a));
            }};
        </script></body></html>"""

    def update_window_size(self):
        self.resize(int(self.wb * self.scale), int(self.hb * self.scale))

    def change_scale(self, delta):
        self.scale = max(1.0, self.scale + delta)
        self.update_window_size()
        self.browser.page().runJavaScript(f"document.getElementById('c').style.transform = 'scale({self.scale})';")

    def update_ui_state(self, ev): 
        self.browser.page().runJavaScript(f"updateUI('{ev}')")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseOpenGLES)
    w = TransparentWindow()
    w.show()
    sys.exit(app.exec())