# Keylogger - Proyecto de Hacking Ético

Trabajo parcial del curso de Hacking Ético
Semestre 2026-10 | Docente: Gianpaul Custodio

Los autores no se responsabilizan del mal uso del material.

Keylogger desarrollado en Python como demostración de:
- Captura de pulsaciones de teclado a bajo nivel
- Almacenamiento de logs con timestamp y ventana activa
- Exfiltración de información vía HTTPS a Telegram y Discord
- Empaquetado como binario ejecutable con Nuitka
- Análisis de detección por Windows Defender


- **Python 3.13**
- **pynput**: captura de eventos de teclado
- **requests**: envío HTTPS a APIs externas
- **Nuitka**: compilación a binario nativo
- **ctypes**: acceso a APIs nativas de Windows (GetKeyState, GetForegroundWindow)
