"""Pixel-Display Integration für dlna-tui.

Unterstützt kleine OLED-Displays (z.B. 0.66" 128x64, 0.96" 128x64, oder 64x64).
Über Umgebungsvariable DLNA_TUI_DISPLAY=1 aktivieren.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

# Optionale Abhängigkeit - wird nur bei Aktivierung importiert
_DISPLAY_ENABLED = os.environ.get("DLNA_TUI_DISPLAY", "").lower() in ("1", "true", "yes")
_DISPLAY_LIB_AVAILABLE = False
_DISPLAY_INSTANCE: Optional["PixelDisplay"] = None

try:
    if _DISPLAY_ENABLED:
        from luma.core.interface.serial import i2c
        from luma.core.render import canvas
        from luma.oled.device import ssd1306, ssd1325, ssd1331, sh1106

        _DISPLAY_LIB_AVAILABLE = True
except ImportError as e:
    log.warning("Pixel-Display deaktiviert: luma nicht installiert (%s)", e)


class PixelDisplay:
    """Abstraktion für kleines Pixel-Display.
    
    Unterstützt grundlegende Textausgabe und einfache Grafiken.
    Bei fehlender Hardware oder Bibliothek: Dummy-Implementierung.
    """
    
    def __init__(self):
        self.device = None
        self.width = 0
        self.height = 0
        
        if not _DISPLAY_ENABLED:
            log.info("Pixel-Display: Inaktiv (setze DLNA_TUI_DISPLAY=1 zum Aktivieren)")
            return
            
        if not _DISPLAY_LIB_AVAILABLE:
            log.error("Pixel-Display: luma nicht installiert")
            return
            
        try:
            # Standard-I2C auf Raspberry Pi
            serial = i2c(port=1, address=0x3C)
            self.device = ssd1306(serial, width=128, height=64)
            self.width = self.device.width
            self.height = self.device.height
            log.info("Pixel-Display: Initialisiert (%dx%d)", self.width, self.height)
        except Exception as exc:
            log.error("Pixel-Display: Initialisierung fehlgeschlagen: %s", exc)
            self.device = None

    def show_now_playing(self, title: str, artist: str, progress: float) -> None:
        """Zeigt aktuelle Wiedergabe.
        
        Args:
            title: Track-Titel (wird gekürzt)
            artist: Künstler (wird gekürzt)
            progress: Fortschritt 0.0..1.0
        """
        if not self.device:
            return

        # Text kürzen für kleine Displays
        max_title_len = self.width // 8  # ca. 8 Pixel pro Zeichen
        max_artist_len = max_title_len // 2

        short_title = (title[:max_title_len] + "..") if len(title) > max_title_len else title
        short_artist = (artist[:max_artist_len] + "..") if len(artist) > max_artist_len else artist

        try:
            with canvas(self.device) as draw:
                # Zeile 1: Titel
                draw.text((0, 0), short_title, fill="white")
                # Zeile 2: Künstler
                draw.text((0, 10), short_artist, fill="white")
                # Zeile 3: Fortschritt
                progress_text = f"{int(progress*100)}%"
                draw.text((0, 20), progress_text, fill="white")
        except Exception as exc:
            log.debug("Display Update fehlgeschlagen: %s", exc)

    def show_cover(self, image_data: bytes) -> None:
        """Zeigt kleines Cover (muss Device-Größe haben).
        
        Args:
            image_data: Rohdaten im Device-Format (mono)
        """
        if not self.device:
            return
        try:
            with canvas(self.device) as draw:
                # Einfaches Cover-Rechteck als Platzhalter
                # In der Praxis würde man hier das echte Cover skalieren
                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
        except Exception as exc:
            log.debug("Cover Display fehlgeschlagen: %s", exc)

    def clear(self) -> None:
        """Löscht das Display."""
        if not self.device:
            return
        try:
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, outline="white", fill="black")
        except Exception:
            pass

    def is_available(self) -> bool:
        """Ob ein funktionierendes Display zur Verfügung steht."""
        return bool(self.device)


# Globale Instanz
def get_display() -> Optional[PixelDisplay]:
    """Holt die globale Display-Instanz."""
    global _DISPLAY_INSTANCE
    if _DISPLAY_INSTANCE is None:
        _DISPLAY_INSTANCE = PixelDisplay()
    return _DISPLAY_INSTANCE