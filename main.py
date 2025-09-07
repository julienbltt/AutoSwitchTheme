from configparser import ConfigParser
from pathlib import Path
from requests import get
from datetime import datetime
from json import dump as json_dump, load as json_load
from time import sleep
import schedule
from os import getenv, system
import logging
from logging.handlers import TimedRotatingFileHandler
import pystray
from PIL import Image, ImageDraw
import threading


APPDATA_PATH = Path(getenv("APPDATA")) / "AutoSwitchTheme"
APPDATA_PATH.mkdir(parents=True, exist_ok=True)


class Logger:
    def __init__(self, log_path: Path | None = None, debug: bool = False):
        self.log_path = log_path
        if self.log_path and not self.log_path.exists():
            self.log_path.mkdir(parents=True, exist_ok=True)
        self.debug = debug

    def _formatter(self) -> logging.Formatter:
        format = (
            "[%(asctime)s] "
            "%(levelname)-8s "
            "%(name)s:%(funcName)s:%(lineno)d "
            "- %(message)s"
        )
        return logging.Formatter(
            format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def setup_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        logger.propagate = False

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self._formatter())
        logger.addHandler(console_handler)

        # File Handler
        if not self.log_path:
            raise ValueError("log_path is required")
        file_handler = TimedRotatingFileHandler(self.log_path / f"{name}.log", when="midnight", backupCount=30)    
        file_handler.setFormatter(self._formatter())
        logger.addHandler(file_handler)

        return logger
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        return logging.getLogger(name)


logger = Logger(APPDATA_PATH / "logs", True).setup_logger("app")


class TrayApp:
    def __init__(self):
        self.icon = None
        self.theme_monitor = None
        self.sun_hours_monitor = None
        self.running = True

    def create_icon(self):
        """Create a simple icon for the tray"""
        # Create a 64x64 image with a sun/moon symbol
        size = (64, 64)
        image = Image.new('RGB', size, color=(0, 120, 215))  # Windows blue
        draw = ImageDraw.Draw(image)

        # Draw a simple sun/moon symbol
        draw.ellipse([16, 16, 48, 48], fill=(255, 255, 255), outline=(0, 0, 0), width=2)

        # Add rays for sun effect
        for i in range(8):
            angle = i * 45
            x1 = 32 + 25 * (angle % 90 - 45) / 45
            y1 = 32 + 25 * (angle // 90 * 2 - 1)
            x2 = 32 + 35 * (angle % 90 - 45) / 45
            y2 = 32 + 35 * (angle // 90 * 2 - 1)
            draw.line([x1, y1, x2, y2], fill=(255, 255, 0), width=2)

        return image

    def on_show_status(self, icon, item):
        """Show current status"""
        if self.theme_monitor and self.sun_hours_monitor:
            current_theme = self.theme_monitor.theme
            sun_hours = self.sun_hours_monitor.sun_hours
            logger.info(f"Current theme: {current_theme}")
            logger.info(f"Sun hours: {sun_hours}")

    def on_force_light(self, icon, item):
        """Force light theme"""
        if self.theme_monitor:
            self.theme_monitor.switch_to_light_theme()
            logger.info("Forced light theme")

    def on_force_dark(self, icon, item):
        """Force dark theme"""
        if self.theme_monitor:
            self.theme_monitor.switch_to_dark_theme()
            logger.info("Forced dark theme")

    def on_quit(self, icon, item):
        """Quit the application"""
        self.running = False
        logger.info("Application quit from tray")
        icon.stop()

    def setup_tray(self):
        """Setup the system tray icon and menu"""
        # Create the icon
        icon_image = self.create_icon()

        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem("Show Status", self.on_show_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Force Light Theme", self.on_force_light),
            pystray.MenuItem("Force Dark Theme", self.on_force_dark),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.on_quit)
        )

        # Create the icon
        self.icon = pystray.Icon(
            "AutoSwitchTheme",
            icon_image,
            "Auto Switch Theme",
            menu
        )

        return self.icon

    def run_tray(self):
        """Run the tray icon (blocking)"""
        self.icon.run()


class SunHoursMonitor:
    def __init__(self, api_token: str, insee: str):
        self.api_token = api_token
        self.insee = insee
        self.sun_hours = {
            "timestamp": None,
            "sunrise": None,
            "sunset": None,
        }

    def get_sun_hours(self):

        # Check if sun hours are cached
        cache_path = APPDATA_PATH / "sun_hours.json"
        if cache_path.exists():
            with cache_path.open("r") as f:
                file_data = json_load(f)
                if file_data["timestamp"] == datetime.today().strftime("%Y-%m-%d"):
                    logger.info("Sun hours fetched from cache")
                    self.sun_hours["timestamp"] = file_data["timestamp"]
                    self.sun_hours["sunrise"] = file_data["sunrise"][:5]
                    self.sun_hours["sunset"] = file_data["sunset"][:5]
        else:
            # Fetch sun hours from API
            url = f"https://api.meteo-concept.com/api/ephemeride/0?token={self.api_token}&insee={self.insee}"
            response = get(url)
            ephemeride = response.json()

            logger.info("Sun hours fetched from API")

            # Update sun hours
            self.sun_hours["timestamp"] = datetime.today().strftime("%Y-%m-%d")
            self.sun_hours["sunrise"] = ephemeride["ephemeride"]["sunrise"][:5]
            self.sun_hours["sunset"] = ephemeride["ephemeride"]["sunset"][:5]
            
            # Save sun hours to cache
            with cache_path.open("w") as f:
                file_data = self.sun_hours
                json_dump(file_data, f)

        logger.debug(f"Sun hours: {self.sun_hours}")
        return self.sun_hours

class ThemeMonitor:
    def __init__(self):
        self.theme = None

    def set_windows_theme(self, theme: str):
        """
        Change Windows theme in a simple and reliable way
        Args:
            theme: 'light' or 'dark'
        """
        try:
            if theme.lower() == "light":
                # Enable light theme
                system('reg add "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" /v AppsUseLightTheme /t REG_DWORD /d 1 /f >nul 2>&1')
                system('reg add "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" /v SystemUsesLightTheme /t REG_DWORD /d 1 /f >nul 2>&1')
            elif theme.lower() == "dark":
                # Enable dark theme
                system('reg add "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" /v AppsUseLightTheme /t REG_DWORD /d 0 /f >nul 2>&1')
                system('reg add "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" /v SystemUsesLightTheme /t REG_DWORD /d 0 /f >nul 2>&1')
            else:
                raise ValueError("Theme must be 'light' or 'dark'")

            logger.info(f"Theme changed to {theme}")

        except Exception as e:
            logger.error(f"Error changing theme: {e}")

    def switch_to_light_theme(self):
        if self.theme != "light":
            self.set_windows_theme("light")
            self.theme = "light"

    def switch_to_dark_theme(self):
        if self.theme != "dark":
            self.set_windows_theme("dark")
            self.theme = "dark"

def main_thread(tray_app: TrayApp):
    """Main application logic running in separate thread"""
    logger.info("Starting main application thread")

    # Load config
    config = ConfigParser()
    config.read(APPDATA_PATH / "config.ini")
    api_token = config.get("api", "token")
    insee = config.get("location", "insee", fallback="06088")

    # Initialize theme monitor
    theme_monitor = ThemeMonitor()

    # Initialize sun hours monitor
    sun_hours_monitor = SunHoursMonitor(api_token, insee)
    schedule.every().day.at("00:00").do(sun_hours_monitor.get_sun_hours)

    # Connect monitors to tray app
    tray_app.theme_monitor = theme_monitor
    tray_app.sun_hours_monitor = sun_hours_monitor

    # Get sun hours at startup
    sun_hours = sun_hours_monitor.get_sun_hours()
    logger.info(f"Sun hours data: {sun_hours}")

    # Run scheduler
    while tray_app.running:
        time_now = datetime.now()
        time_sunrise = datetime.strptime(sun_hours["timestamp"] + " " + sun_hours["sunrise"], "%Y-%m-%d %H:%M")
        time_sunset = datetime.strptime(sun_hours["timestamp"] + " " + sun_hours["sunset"], "%Y-%m-%d %H:%M")

        logger.debug("Checking theme")
        logger.debug("Current time: {}, Sunrise: {}, Sunset: {}".format(
                time_now,
                time_sunrise,
                time_sunset
            )
        )

        if(time_now >= time_sunrise and time_now < time_sunset):
            theme_monitor.switch_to_light_theme()
            logger.debug("Switching to light theme")
        else:
            theme_monitor.switch_to_dark_theme()
            logger.debug("Switching to dark theme")

        schedule.run_pending()
        sleep(60)

    logger.info("Main application thread stopped")


def main():
    """Main entry point - setup tray and start threads"""
    logger.info("AutoSwitchTheme starting...")

    # Create tray app
    tray_app = TrayApp()
    tray_icon = tray_app.setup_tray()

    # Start main logic in separate thread
    main_thread_obj = threading.Thread(
        target=main_thread,
        args=(tray_app,),
        daemon=True
    )
    main_thread_obj.start()

    # Run tray icon (blocking - this keeps the app running)
    logger.info("Application minimized to system tray")
    tray_app.run_tray()

    logger.info("Application stopped")

if __name__ == "__main__":
    raise SystemExit(main())