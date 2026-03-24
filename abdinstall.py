#!/usr/bin/env python3
import subprocess
import platform
import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path


class ADBAutoInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.adb_path = None

    def check_adb(self):
        """Sprawdza czy adb jest dostępne w PATH"""
        # return False
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ ADB jest już zainstalowane:")
                print(f"   {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
        return False

    def find_adb_in_common_locations(self):
        """Szuka adb w typowych lokalizacjach"""
        common_paths = []

        if self.system == 'windows':
            common_paths = [
                r'C:\Users\{}\AppData\Local\Android\Sdk\platform-tools\adb.exe'.format(os.getenv('USERNAME')),
                r'C:\Program Files\Android\platform-tools\adb.exe',
                r'C:\Android\platform-tools\adb.exe',
                r'C:\adb\adb.exe',
            ]
        elif self.system == 'linux':
            common_paths = [
                '/usr/bin/adb',
                '/usr/local/bin/adb',
                '/opt/android-sdk/platform-tools/adb',
                os.path.expanduser('~/Android/Sdk/platform-tools/adb'),
            ]
        elif self.system == 'darwin':  # macOS
            common_paths = [
                '/usr/local/bin/adb',
                '/opt/homebrew/bin/adb',
                '/usr/bin/adb',
                os.path.expanduser('~/Library/Android/sdk/platform-tools/adb'),
            ]

        for path in common_paths:
            if os.path.isfile(path):
                print(f"🔍 Znaleziono ADB w: {path}")
                self.adb_path = path
                # Dodaj do PATH tymczasowo
                os.environ['PATH'] = os.path.dirname(path) + os.pathsep + os.environ['PATH']
                return True
        return False

    def install_adb(self):
        """Instaluje ADB automatycznie"""
        print(f"📥 ADB nie znaleziono. Rozpoczynam instalację dla {self.system}...")

        if self.system == 'windows':
            return self._install_windows()
        elif self.system == 'linux':
            return self._install_linux()
        elif self.system == 'darwin':
            return self._install_macos()
        else:
            print(f"❌ Nieobsługiwany system: {self.system}")
            return False

    def _install_windows(self):
        """Instalacja ADB na Windows"""
        try:
            # Pobierz najnowszy SDK Platform Tools
            url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
            zip_path = os.path.join(os.getenv('TEMP'), 'platform-tools.zip')
            extract_path = r'C:\adb'

            print("⬇️ Pobieranie Android SDK Platform Tools...")
            urllib.request.urlretrieve(url, zip_path)
            print("✅ Pobrano")

            # Wypakuj
            print("📦 Wypakowywanie...")
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)
            os.makedirs(extract_path, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            # Znajdź adb.exe
            adb_exe = os.path.join(extract_path, 'platform-tools', 'adb.exe')
            if os.path.exists(adb_exe):
                self.adb_path = adb_exe
                # Dodaj do PATH użytkownika (trwale)
                self._add_to_windows_path(os.path.dirname(adb_exe))
                # Dodaj tymczasowo do bieżącej sesji
                os.environ['PATH'] = os.path.dirname(adb_exe) + os.pathsep + os.environ['PATH']
                print(f"✅ ADB zainstalowane w: {adb_exe}")
                return True

        except Exception as e:
            print(f"❌ Błąd instalacji: {e}")
            return False

    def _install_linux(self):
        """Instalacja ADB na Linux"""
        try:
            print("🔧 Próba instalacji przez menedżer pakietów...")

            # Sprawdź dostępne menedżery pakietów
            if shutil.which('apt'):
                cmd = ['sudo', 'apt', 'update', '&&', 'sudo', 'apt', 'install', '-y', 'adb']
            elif shutil.which('yum'):
                cmd = ['sudo', 'yum', 'install', '-y', 'android-tools']
            elif shutil.which('pacman'):  # <-- POPRAWKA: brakowało zamykającego nawiasu
                cmd = ['sudo', 'pacman', '-S', '--noconfirm', 'android-tools']
            elif shutil.which('dnf'):
                cmd = ['sudo', 'dnf', 'install', '-y', 'android-tools']
            else:
                # Ręczna instalacja
                return self._install_linux_manual()

            result = subprocess.run(' '.join(cmd), shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ ADB zainstalowane przez menedżer pakietów")
                return True
            else:
                return self._install_linux_manual()

        except Exception as e:
            print(f"❌ Błąd instalacji: {e}")
            return self._install_linux_manual()

    def _install_linux_manual(self):
        """Ręczna instalacja ADB na Linux"""
        try:
            url = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
            zip_path = '/tmp/platform-tools.zip'
            extract_path = os.path.expanduser('~/android-platform-tools')

            print("⬇️ Pobieranie Android SDK Platform Tools...")
            urllib.request.urlretrieve(url, zip_path)

            print("📦 Wypakowywanie...")
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)

            subprocess.run(['unzip', '-q', zip_path, '-d', extract_path], check=True)

            adb_path = os.path.join(extract_path, 'platform-tools', 'adb')
            os.chmod(adb_path, 0o755)

            # Dodaj do ~/.bashrc
            bashrc = os.path.expanduser('~/.bashrc')
            with open(bashrc, 'a') as f:
                f.write(f'\nexport PATH="$PATH:{os.path.dirname(adb_path)}"\n')

            os.environ['PATH'] = os.path.dirname(adb_path) + os.pathsep + os.environ['PATH']
            self.adb_path = adb_path
            print(f"✅ ADB zainstalowane w: {adb_path}")
            print("📝 Ścieżka dodana do ~/.bashrc (wymagany restart terminala dla trwałego efektu)")
            return True

        except Exception as e:
            print(f"❌ Błąd ręcznej instalacji: {e}")
            return False

    def _install_macos(self):
        """Instalacja ADB na macOS"""
        try:
            if shutil.which('brew'):
                print("🔧 Instalacja przez Homebrew...")
                result = subprocess.run(['brew', 'install', 'android-platform-tools'],
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ ADB zainstalowane przez Homebrew")
                    return True

            # Ręczna instalacja
            url = "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
            zip_path = '/tmp/platform-tools.zip'
            extract_path = os.path.expanduser('~/android-platform-tools')

            print("⬇️ Pobieranie Android SDK Platform Tools...")
            urllib.request.urlretrieve(url, zip_path)

            print("📦 Wypakowywanie...")
            subprocess.run(['unzip', '-q', zip_path, '-d', extract_path], check=True)

            adb_path = os.path.join(extract_path, 'platform-tools', 'adb')
            os.chmod(adb_path, 0o755)

            # Dodaj do ~/.zshrc lub ~/.bash_profile
            shell_config = os.path.expanduser('~/.zshrc') if os.path.exists(
                os.path.expanduser('~/.zshrc')) else os.path.expanduser('~/.bash_profile')
            with open(shell_config, 'a') as f:
                f.write(f'\nexport PATH="$PATH:{os.path.dirname(adb_path)}"\n')

            os.environ['PATH'] = os.path.dirname(adb_path) + os.pathsep + os.environ['PATH']
            self.adb_path = adb_path
            print(f"✅ ADB zainstalowane w: {adb_path}")
            return True

        except Exception as e:
            print(f"❌ Błąd instalacji: {e}")
            return False

    def _add_to_windows_path(self, path):
        """Dodaje ścieżkę do PATH Windows (trwale)"""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_ALL_ACCESS) as key:
                current_path, _ = winreg.QueryValueEx(key, 'Path')
                if path not in current_path:
                    new_path = current_path + ';' + path
                    winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
                    print(f"📝 Dodano do PATH systemowego Windows")
                    # Odśwież zmienne środowiskowe
                    subprocess.run(['setx', 'PATH', new_path], capture_output=True)
        except Exception as e:
            print(f"⚠️ Nie udało się dodać do PATH systemowego: {e}")
            print(f"   Dodaj ręcznie: {path}")

    def verify_installation(self):
        """Weryfikuje czy adb działa"""
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"\n✅ Weryfikacja udana: {result.stdout.strip()}")
                return True
        except Exception as e:
            print(f"\n❌ Weryfikacja nieudana: {e}")
        return False

    def run(self):
        """Główna metoda"""
        print("🔍 Sprawdzanie ADB (Android Debug Bridge)...")
        print("-" * 50)

        # Sprawdź czy adb jest w PATH
        if self.check_adb():
            return True

        # Sprawdź w typowych lokalizacjach
        if self.find_adb_in_common_locations():
            if self.check_adb():
                return True

        # Instaluj jeśli nie znaleziono
        if self.install_adb():
            return self.verify_installation()

        return False


def ensure_adb(func):
    """Dekorator zapewniający obecność ADB przed wykonaniem funkcji"""

    def wrapper(*args, **kwargs):
        installer = ADBAutoInstaller()
        if not installer.run():
            print("❌ Nie udało się zainstalować ADB. Przerwanie.")
            sys.exit(1)
        return func(*args, **kwargs)

    return wrapper


# Przykład użycia w Twoim main.py:

# @ensure_adb
# def main():
#     """Twoja główna funkcja z automatycznym sprawdzaniem ADB"""
#     # Tutaj reszta Twojego kodu
#     print("🚀 Kontynuacja z działającym ADB...")
#
#     # Przykład: pobierz urządzenia
#     result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
#     print(f"Podłączone urządzenia:\n{result.stdout}")
#
#
# if __name__ == "__main__":
#     # Szybkie sprawdzenie bez dekoratora
#     installer = ADBAutoInstaller()
#     if installer.run():
#         print("\n🎉 ADB jest gotowe do użycia!")
#         # Tutaj możesz kontynuować z resztą programu
#     else:
#         print("\n❌ Nie udało się przygotować ADB")
#         sys.exit(1)