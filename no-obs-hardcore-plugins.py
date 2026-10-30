#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
No-obs-hardcore-plugins — Gestionnaire de plugins & scripts pour OBS Studio.

Version 1.0
- Portable : Linux (Debian/Arch), macOS, Windows
- Configuration du répertoire d'importation (plugins + scripts)
- Liste des plugins/scripts disponibles avec bouton Installer
- Section "Plugins installés" avec date et bouton Supprimer
- Affiche le type d'installation OBS et l'affichage (X11/Wayland)

Dépendance unique : PySide6 (Qt6).
Requires: Python >= 3.9
Lancement : python3 no-obs-hardcore-plugins.py
"""
from __future__ import annotations

import getpass
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QScrollArea,
    QSplitter,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

if sys.version_info < (3, 9): sys.exit("Python 3.9+ requis")

# ─── Chemins OBS par plateforme ───────────────────────────────────────────────

OBS_PLUGIN_DIRS: dict[str, list[tuple[str, Path]]] = {
    "Linux": [
        ("Debian/Ubuntu (system)", Path("/usr/share/obs/obs-plugins/")),
        ("Debian/Ubuntu (lib64)", Path("/usr/lib/x86_64-linux-gnu/obs-plugins/")),
        ("Debian/Ubuntu (local)", Path("/usr/local/lib/x86_64-linux-gnu/obs-plugins/")),
        ("Arch (lib64)", Path("/usr/lib64/obs-plugins/")),
        ("Build/Git (config)", Path.home() / ".config" / "obs-studio" / "plugins"),
        ("Flatpak", Path.home() / ".var" / "app" / "com.obsproject.Studio" / "config" / "obs-studio" / "plugins"),
        ("AppImage", Path.home() / ".local" / "share" / "obs" / "obs-plugins"),
    ],
    "Windows": [
        ("Program Files (64)", Path("C:/Program Files/obs-studio/obs-plugins/")),
        ("Program Files (x86)", Path("C:/Program Files (x86)/obs-studio/obs-plugins/")),
        ("ProgramData", Path("C:/ProgramData/obs-studio/plugins/")),
        ("LOCALAPPDATA", Path(os.environ.get("LOCALAPPDATA", "C:/Users/Default/AppData/Local")) / "obs" / "obs-plugins"),
        ("APPDATA", Path(os.environ.get("APPDATA", "C:/Users/Default/AppData/Roaming")) / "obs" / "plugins"),
    ],
    "Darwin": [
        ("App Bundle", Path("/Applications/OBS.app/Contents/Resources/obs-plugins/")),
        ("Homebrew (Intel)", Path("/usr/local/lib/obs-plugins/")),
        ("Homebrew (ARM)", Path("/opt/homebrew/lib/obs-plugins/")),
        ("Application Support", Path.home() / "Library" / "Application Support" / "obs-studio" / "plugins"),
        ("Local lib", Path.home() / ".local" / "lib" / "obs-plugins"),
        ("Local share", Path.home() / ".local" / "share" / "obs" / "obs-plugins"),
    ],
}

PLUGIN_EXTENSIONS = {".lua", ".py", ".zip", ".tar.gz"}


# ─── Détections système ───────────────────────────────────────────────────────

def detect_obs_install() -> list[tuple[str, Path]]:
    """Retourne les répertoires OBS existants sur cette plateforme."""
    system = platform.system()
    if system == "Darwin":
        system = "Darwin"
    elif system == "Windows":
        system = "Windows"
    else:
        system = "Linux"
    detected = []
    for label, path in OBS_PLUGIN_DIRS.get(system, []):
        if path.is_dir():
            detected.append((label, path))
    return detected


def detect_display() -> str:
    """Détecte X11 ou Wayland."""
    return os.environ.get("XDG_SESSION_TYPE", "inconnu")


def default_import_dir() -> Path:
    """Répertoire d'importation par défaut."""
    if platform.system() == "Darwin":
        return Path.home() / "Downloads"
    # Détection locale FR
    if (Path.home() / "Téléchargements").is_dir():
        return Path.home() / "Téléchargements"
    return Path.home() / "Downloads"


def is_plugin_file(path: Path) -> bool:
    """Vérifie si un fichier est un plugin/script OBS."""
    if path.name.endswith(".tar.gz"):
        return True
    return path.suffix.lower() in {".lua", ".py", ".zip"}


# ─── Widget : Ligne plugin ────────────────────────────────────────────────────

class PluginRow(QWidget):
    """Une ligne dans la liste d'un plugin avec actions."""

    def __init__(self, filename: str, filepath: Path, size: int,
                 installed: bool = False, install_date: str = "",
                 on_install=None, on_delete=None):
        super().__init__()
        self.filepath = filepath
        self.on_install = on_install
        self.on_delete = on_delete

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)

        # Nom
        self.name_label = QLabel(filename)
        self.name_label.setFont(QFont("Monospace", 9))
        layout.addWidget(self.name_label)

        # Taille
        size_label = QLabel(f"({self._fmt_size(size)})")
        size_label.setStyleSheet("color: gray;")
        layout.addWidget(size_label)

        # Statut
        self.status_label = QLabel()
        if installed:
            self.status_label.setText(f"✓ Installé le {install_date}")
            self.status_label.setStyleSheet("color: #2e7d32;")
        else:
            self.status_label.setText("✗ Non installé")
            self.status_label.setStyleSheet("color: #c62828;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Bouton action
        if not installed and on_install:
            btn = QPushButton("Installer")
            btn.setMaximumWidth(90)
            btn.clicked.connect(lambda: self.on_install(self.filepath))
            layout.addWidget(btn)
        elif installed and on_delete:
            btn = QPushButton("Supprimer")
            btn.setMaximumWidth(90)
            btn.setStyleSheet("background-color: #ffebee; color: #c62828;")
            btn.clicked.connect(lambda: self.on_delete(self.filepath))
            layout.addWidget(btn)

        self.setLayout(layout)

    @staticmethod
    def _fmt_size(n: int) -> str:
        if n < 1024:
            return f"{n} o"
        if n < 1024 * 1024:
            return f"{n // 1024} Ko"
        return f"{n / (1024*1024):.1f} Mo"


# ─── Fenêtre principale ───────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("No-obs-hardcore-plugins v1.0")
        self.resize(900, 650)

        self.obs_dirs: list[tuple[str, Path]] = []
        self.import_dir: Path = default_import_dir()
        self.script_dir: Path = default_import_dir()
        self.same_script_dir: bool = True

        self._build_ui()
        self._detect_system()
        self._refresh_lists()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)

        # ── Section Système ──
        sys_frame = QFrame()
        sys_frame.setFrameShape(QFrame.StyledPanel)
        sys_layout = QVBoxLayout(sys_frame)
        sys_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_system = QLabel("")
        self.lbl_system.setStyleSheet("font-weight: bold;")
        sys_layout.addWidget(self.lbl_system)

        self.lbl_obs = QLabel("")
        sys_layout.addWidget(self.lbl_obs)

        self.lbl_display = QLabel("")
        sys_layout.addWidget(self.lbl_display)

        main_layout.addWidget(sys_frame)

        # ── Section Import ──
        import_frame = QFrame()
        import_frame.setFrameShape(QFrame.StyledPanel)
        import_layout = QVBoxLayout(import_frame)
        import_layout.setContentsMargins(8, 6, 8, 6)

        # Plugins import dir
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Répertoire plugins :"))
        self.edit_import = QLineEdit(str(self.import_dir))
        self.edit_import.setReadOnly(False)
        btn_browse = QPushButton("Parcourir…")
        btn_browse.setMaximumWidth(100)
        btn_browse.clicked.connect(self._browse_import)
        row1.addWidget(self.edit_import, 1)
        row1.addWidget(btn_browse)
        import_layout.addLayout(row1)

        # Same dir checkbox
        self.chk_same = QCheckBox("Même chemin pour les scripts")
        self.chk_same.setChecked(True)
        self.chk_same.toggled.connect(self._toggle_script_dir)
        import_layout.addWidget(self.chk_same)

        # Scripts import dir (hidden by default)
        self.row_scripts = QHBoxLayout()
        self.row_scripts.addWidget(QLabel("Répertoire scripts :"))
        self.edit_script = QLineEdit(str(self.script_dir))
        btn_browse_s = QPushButton("Parcourir…")
        btn_browse_s.setMaximumWidth(100)
        btn_browse_s.clicked.connect(self._browse_script)
        self.row_scripts.addWidget(self.edit_script, 1)
        self.row_scripts.addWidget(btn_browse_s)
        self.widget_script_row = QWidget()
        self.widget_script_row.setLayout(self.row_scripts)
        self.widget_script_row.hide()
        import_layout.addWidget(self.widget_script_row)

        btn_refresh = QPushButton("↻ Actualiser la liste")
        btn_refresh.setMaximumWidth(180)
        btn_refresh.clicked.connect(self._refresh_lists)
        import_layout.addWidget(btn_refresh)

        main_layout.addWidget(import_frame)

        # ── Section Plugins / Scripts (Splitter 2x2) ──
        splitter = QSplitter(Qt.Horizontal)

        # Colonne gauche : Plugins
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Plugins disponibles
        left_layout.addWidget(QLabel("<b>Plugins disponibles</b>"))
        self.lbl_path_plugins_avail = QLabel("")
        self.lbl_path_plugins_avail.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        left_layout.addWidget(self.lbl_path_plugins_avail)
        self.scroll_plugins_avail = QScrollArea()
        self.scroll_plugins_avail.setWidgetResizable(True)
        self.widget_plugins_avail = QWidget()
        self.layout_plugins_avail = QVBoxLayout(self.widget_plugins_avail)
        self.layout_plugins_avail.setContentsMargins(0, 0, 0, 0)
        self.scroll_plugins_avail.setWidget(self.widget_plugins_avail)
        left_layout.addWidget(self.scroll_plugins_avail, 1)

        # Plugins installés
        left_layout.addWidget(QLabel("<b>Plugins installés</b>"))
        self.lbl_path_plugins_inst = QLabel("")
        self.lbl_path_plugins_inst.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        left_layout.addWidget(self.lbl_path_plugins_inst)
        self.scroll_plugins_inst = QScrollArea()
        self.scroll_plugins_inst.setWidgetResizable(True)
        self.widget_plugins_inst = QWidget()
        self.layout_plugins_inst = QVBoxLayout(self.widget_plugins_inst)
        self.layout_plugins_inst.setContentsMargins(0, 0, 0, 0)
        self.scroll_plugins_inst.setWidget(self.widget_plugins_inst)
        left_layout.addWidget(self.scroll_plugins_inst, 1)

        splitter.addWidget(left_widget)

        # Colonne droite : Scripts
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Scripts disponibles
        right_layout.addWidget(QLabel("<b>Scripts disponibles</b>"))
        self.lbl_path_scripts_avail = QLabel("")
        self.lbl_path_scripts_avail.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        right_layout.addWidget(self.lbl_path_scripts_avail)
        self.scroll_scripts_avail = QScrollArea()
        self.scroll_scripts_avail.setWidgetResizable(True)
        self.widget_scripts_avail = QWidget()
        self.layout_scripts_avail = QVBoxLayout(self.widget_scripts_avail)
        self.layout_scripts_avail.setContentsMargins(0, 0, 0, 0)
        self.scroll_scripts_avail.setWidget(self.widget_scripts_avail)
        right_layout.addWidget(self.scroll_scripts_avail, 1)

        # Scripts installés
        right_layout.addWidget(QLabel("<b>Scripts installés</b>"))
        self.lbl_path_scripts_inst = QLabel("")
        self.lbl_path_scripts_inst.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        right_layout.addWidget(self.lbl_path_scripts_inst)
        self.scroll_scripts_inst = QScrollArea()
        self.scroll_scripts_inst.setWidgetResizable(True)
        self.widget_scripts_inst = QWidget()
        self.layout_scripts_inst = QVBoxLayout(self.widget_scripts_inst)
        self.layout_scripts_inst.setContentsMargins(0, 0, 0, 0)
        self.scroll_scripts_inst.setWidget(self.widget_scripts_inst)
        right_layout.addWidget(self.scroll_scripts_inst, 1)

        splitter.addWidget(right_widget)

        main_layout.addWidget(splitter, 1)

        # ── Barre bas : Exit ──
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_exit = QPushButton("Quitter")
        btn_exit.setMaximumWidth(100)
        btn_exit.clicked.connect(self.close)
        bottom.addWidget(btn_exit)
        main_layout.addLayout(bottom)

        self.setCentralWidget(central)

    # ── Détection système ────────────────────────────────────────────────────

    def _detect_system(self):
        username = getpass.getuser()
        sys_name = platform.system()
        self.lbl_system.setText(
            f"Système : {sys_name} {platform.release()} — Bienvenue {username}"
        )

        self.obs_dirs = detect_obs_install()
        if self.obs_dirs:
            labels = ", ".join(lbl for lbl, _ in self.obs_dirs)
            self.lbl_obs.setText(f"OBS détecté : {labels}")
        else:
            self.lbl_obs.setText("⚠ Aucun répertoire OBS détecté sur ce système.")
            self.lbl_obs.setStyleSheet("color: #c62828;")

        display = detect_display()
        self.lbl_display.setText(f"Affichage : {display}")

    # ── Navigation dossiers ──────────────────────────────────────────────────

    def _browse_import(self):
        d = QFileDialog.getExistingDirectory(self, "Choisir le répertoire plugins")
        if d:
            self.edit_import.setText(d)
            self.import_dir = Path(d)
            if self.chk_same.isChecked():
                self.edit_script.setText(d)
                self.script_dir = Path(d)
            self._refresh_lists()

    def _browse_script(self):
        d = QFileDialog.getExistingDirectory(self, "Choisir le répertoire scripts")
        if d:
            self.edit_script.setText(d)
            self.script_dir = Path(d)
            self._refresh_lists()

    def _toggle_script_dir(self, checked: bool):
        self.same_script_dir = checked
        self.widget_script_row.setVisible(not checked)
        if checked:
            self.edit_script.setText(self.edit_import.text())
            self.script_dir = Path(self.edit_import.text())
        self._refresh_lists()

    # ── Rafraîchissement des listes ─────────────────────────────────────────

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _refresh_lists(self):
        self.import_dir = Path(self.edit_import.text())
        if not self.chk_same.isChecked():
            self.script_dir = Path(self.edit_script.text())
        else:
            self.script_dir = self.import_dir

        obs_display = ", ".join(str(p) for _, p in self.obs_dirs if p.is_dir()) or "(aucun)"

        # ── Plugins disponibles ──
        self._clear_layout(self.layout_plugins_avail)
        self.lbl_path_plugins_avail.setText(str(self.import_dir))
        found = False
        if self.import_dir.is_dir():
            for f in sorted(self.import_dir.iterdir()):
                if not f.is_file() or not is_plugin_file(f) or f.suffix == ".py":
                    continue
                found = True
                installed = self._is_installed(f.name)
                row = PluginRow(f.name, f, f.stat().st_size, installed,
                                on_install=None if installed else self._install_plugin)
                self.layout_plugins_avail.addWidget(row)
        if not found:
            self._add_empty(self.layout_plugins_avail, "Aucun plugin trouvé.")

        # ── Scripts disponibles ──
        self._clear_layout(self.layout_scripts_avail)
        self.lbl_path_scripts_avail.setText(str(self.script_dir))
        found = False
        if self.script_dir.is_dir():
            for f in sorted(self.script_dir.iterdir()):
                if not f.is_file() or f.suffix != ".py":
                    continue
                found = True
                installed = self._is_installed(f.name)
                row = PluginRow(f.name, f, f.stat().st_size, installed,
                                on_install=None if installed else self._install_plugin)
                self.layout_scripts_avail.addWidget(row)
        if not found:
            self._add_empty(self.layout_scripts_avail, "Aucun script trouvé.")

        # ── Plugins installés ──
        self._clear_layout(self.layout_plugins_inst)
        self.lbl_path_plugins_inst.setText(obs_display)
        found = False
        for _, obs_dir in self.obs_dirs:
            if not obs_dir.is_dir():
                continue
            for f in sorted(obs_dir.rglob("*")):
                if not f.is_file() or not is_plugin_file(f) or f.suffix == ".py":
                    continue
                found = True
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                row = PluginRow(f.name, f, f.stat().st_size, True, mtime, on_delete=self._delete_plugin)
                self.layout_plugins_inst.addWidget(row)
        if not found:
            self._add_empty(self.layout_plugins_inst, "Aucun plugin installé.")

        # ── Scripts installés ──
        self._clear_layout(self.layout_scripts_inst)
        self.lbl_path_scripts_inst.setText(obs_display)
        found = False
        for _, obs_dir in self.obs_dirs:
            if not obs_dir.is_dir():
                continue
            for f in sorted(obs_dir.rglob("*")):
                if not f.is_file() or f.suffix != ".py":
                    continue
                found = True
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                row = PluginRow(f.name, f, f.stat().st_size, True, mtime, on_delete=self._delete_plugin)
                self.layout_scripts_inst.addWidget(row)
        if not found:
            self._add_empty(self.layout_scripts_inst, "Aucun script installé.")

    def _add_empty(self, layout, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: gray; padding: 8px;")
        layout.addWidget(lbl)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _is_installed(self, filename: str) -> bool:
        for _, obs_dir in self.obs_dirs:
            if (obs_dir / filename).exists():
                return True
        return False

    def _install_plugin(self, filepath: Path):
        if not self.obs_dirs:
            self.lbl_obs.setText("⚠ Impossible : aucun répertoire OBS détecté.")
            return
        target_dir = self.obs_dirs[0][1]
        try:
            shutil.copy2(filepath, target_dir / filepath.name)
            self._refresh_lists()
        except Exception as e:
            self.lbl_obs.setText(f"⚠ Erreur d'installation : {e}")

    def _delete_plugin(self, filepath: Path):
        try:
            filepath.unlink()
            self._refresh_lists()
        except Exception as e:
            self.lbl_obs.setText(f"⚠ Erreur de suppression : {e}")


# ─── Point d'entrée ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
