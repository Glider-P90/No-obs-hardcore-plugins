
import sys, os, platform, pwd


from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QCheckBox,
    QLabel,
    QProgressBar,
    QToolButton,
)
from PySide6.QtGui import QIcon, QPixmap

from PySide6.QtCore import Qt, QSize, QPointF, QDir, QObject, Signal, Slot

class Buffer:

    def __init__(self, main:QVBoxLayout):
        self.main = main
        self.icones: list[QWidget] = []

    def load(self):
        for icone in self.icones:
            self.main.addWidget(icone)

class Icones(Buffer):
    
    def __init__(self, main:QVBoxLayout):
        super().__init__(main)
        
    def append(self, label="", path=Path(), posX=0, posY=0, width=0, height=0):
        widget = QWidget()
        icone = QLabel()
        pixmap = QPixmap(path)
        icone.setToolTip(label)
        icone.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        widget.setLayout(QVBoxLayout())
        widget.layout().addWidget(icone)
        widget.setGeometry(200, 300, 64, 64)
        self.icones.append(widget)

class PluginTool(QWidget):

#    plugin_installed: list[] = ["switch.lua", "turcmuch.lua", "monzip.py",]
#    plugin_available: list[] = ["switch.lua", "turcmuch.lua", "monzip.py", "entest.lua", "micro.py",]

    def __init__(self):
        super().__init__(self)
        
    
class MenuItem(QPushButton):
    
    def __init__(self, index:int, label:str, path_obs:Path, path_plugins_available=Path.home() / "Downloads"):
        super().__init__(label)
        self.index = index
        self.clicked.connect(self.activate_page)
        self.path_obs = path_obs
        self.path_plugins_available = path_plugins_available
        self.path_plugins_installed = ""
        if self.path_plugins_installed == "":
            self.path_plugins_installed = path_plugins_available
        
        
    def activate_page(self):
        self.listPluginsDir(self.sender().path_obs)
        self.listPluginsDir(self.sender().path_plugins_available)
        self.listPluginsDir(self.sender().path_obs)
        
    def listPluginsDir(self, path:Path):
        dir = QDir(path);
        dir.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
        dir.setNameFilters(["*"])
        fileList = dir.entryList()
        for string in fileList:
            print("file:",string)
        print("TERMINATED")
        
class NoobPlugins(QMainWindow):
    
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OBS Plugins Manager 1.0")
        self.resize(800, 600)
        self.main = QVBoxLayout()
        self.plugins_installed = QVBoxLayout()
        self.plugins_available = QVBoxLayout()
        self.icones = Icones(self.main)
        self.username = pwd.getpwuid(os.getuid())[0]
        self.obs_plugins: dict[str, list[str, Path]] = {
            "Linux": [
                [ "Official Debian Package Archive:", Path("/usr/share/obs/obs-plugins/")],
                [ "Debian: ",   Path("/usr/lib/x86_64-linux-gnu/obs-plugins/")],
                [ "Debian: ",   Path("/usr/local/lib/x86_64-linux-gnu/obs-plugins/")],
                [ "Arch: ",     Path("/usr/lib64/obs-plugins/")],
                [ "Git: ",      Path.home() / "/.config/obs-studio/plugins/"],
                [ "Flatpak: ",  Path.home() / "/.var/app/com.obsproject.Studio/config/obs-studio/plugins/"],
                [ "AppImage: ", Path.home() / "/.local/share/obs/obs-plugins/"],
            ],
            "Windows": [
                [ "system_64: ",  Path(f"C:/Program Files/obs-studio/obs-plugins/bit")],
                [ "system_32: ",  Path(f"C:/Program Files (x86)/obs-studio/obs-plugins")],
                [ "user_local: ", Path(f"C:/ProgramData/obs-studio/plugins")],
                [ "user_local: ", Path(f"%LOCALAPPDATA%/obs/obs-plugins")],
                [ "appdata: ",    Path(f"%APPDATA%/obs/plugins")],
            ],
            "Macos": [
                [ "Mac-app_bundle: ", Path("/Applications/OBS.app/Contents/Resources/obs-plugins/")],
                [ "Mac-brew_intel: ", Path("/usr/local/lib/obs-plugins/")],
                [ "Mac-brew_arm: ",   Path("/opt/homebrew/lib/obs-plugins/")],
                [ "Mac-3: ",          Path(r"~/Library/Application Support/obs-studio/plugins")],
                [ "Mac-4: ",          Path(r"~/.local/lib/obs-plugins/")],
                [ "Mac-5: ",          Path(r"~/.local/share/obs/obs-plugins/")],
            ],
        }

        self.status: dict[str, list[str , Path]] = {
            "alert":  [ "Attentions",   Path.home() / "Pictures/icone/no_obs-plugins/status-red-alert.png" ],
            "red":    [ "Non installé", Path.home() / "Pictures/icone/no_obs-plugins/status-red-not.png" ],
            "orange": [ "Cassé",        Path.home() / "Pictures/icone/no_obs-plugins/status-orange-not.png" ],
            "blue":   [ "En attente",   Path.home() / "Pictures/icone/no_obs-plugins/status-blue-check.png" ],
            "green":  [ "Installé",     Path.home() / "Pictures/icone/no_obs-plugins/status-green-check.png" ],
        }

        for status in self.status.values():
            self.icones.append(status[0], str(status[1]))

        widget_welcome = QLabel()
        widget_welcome.setText("<u><strong>Système détecté "+platform.system()+":</strong></u> Bienvenue "+self.username+"!")
        self.main.addWidget(widget_welcome)
        self.installDetection()

    def installDetection(self):
        items:list[str,Path]  = list()
        
        label = QLabel("Type d'installation:")
        self.main.addWidget(label)
        for os_key in self.obs_plugins.keys():
            if os_key == platform.system():
                for type_install, path_to_plugin in self.obs_plugins[os_key]:
                    if path_to_plugin.is_dir():
                        items.append([type_install, path_to_plugin])

        self.menu_repo_type: list[MenuItem] = []
        for label, path in items:
            self.menu_repo_type.append(MenuItem(len(self.menu_repo_type), label, path))

    def setPage(self) -> QWidget:
        widget_page = QWidget()
        page_layout = QVBoxLayout()
        page_layout.addWidget(QLabel("toto.lua"))
        page_layout.addWidget(QLabel("toasdto.lua"))
        page_layout.addWidget(QLabel("XXXXo.lua"))
        page_layout.addWidget(QLabel("qwertyo.lua"))
        page_layout.addWidget(QLabel("pagetoto.lua"))
        page_layout.addWidget(QLabel("swipetoto.lua"))
        page_layout.addWidget(QLabel("INFOtoto.lua"))
        widget_page.setLayout(page_layout)
        return widget_page
        
        
    def display(self):
        central_widget = QWidget()
        for btn in self.menu_repo_type:
            self.main.addWidget(btn)
        central_widget.setLayout(self.main)
        self.setCentralWidget(central_widget)        
        self.show()
        
app = QApplication(sys.argv)
window = NoobPlugins()
window.display()
app.exec()
