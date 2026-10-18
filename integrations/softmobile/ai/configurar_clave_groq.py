#!/usr/bin/env python3
"""Install a Groq API key securely from an interactive VPS terminal; test on fictitious input."""
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
TARGET = Path("/etc/softmobile/groq.env")
SAFE_KEY = re.compile(r"^gsk_[A-Za-z0-9_-]{16,}$")

def save_key(secret, target=TARGET):
    if not isinstance(secret, str) or not SAFE_KEY.fullmatch(secret):
        raise ValueError("Formato de clave Groq no reconocido; comprueba que la copiaste completa.")
    target = Path(target)
    os.makedirs(target.parent, mode=0o700, exist_ok=True)
    if target.parent == TARGET.parent:
        os.chmod(target.parent, 0o700)
    old_mask = os.umask(0o077)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=str(target.parent), prefix=".groq-", 
                                         delete=False) as file:
            tmp_path = file.name
            os.fchmod(file.fileno(), 0o600)
            file.write("GROQ_API_KEY=" + secret + "\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, target)
        os.chmod(target, 0o600)
    finally:
        os.umask(old_mask)
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

def stored_key(target=TARGET):
    target = Path(target)
    if not target.is_file():
        raise RuntimeError("No está guardada la clave Groq.")
    if target.stat().st_mode & 0o077:
        raise RuntimeError("Permisos inseguros en archivo de credenciales.")
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.startswith("GROQ_API_KEY="):
            secret = line.split("=", 1)[1].strip()
            if not SAFE_KEY.fullmatch(secret):
                raise RuntimeError("La clave almacenada no tiene el formato esperado.")
            return secret
    raise RuntimeError("Falta GROQ_API_KEY en el archivo.")

def verify(secret):
    env = os.environ.copy()
    env["GROQ_API_KEY"] = secret
    env["SOFTMOBILE_AI_ENABLED"] = "true"
    sample = {
        "conversation_id": 3,
        "message": "Hola, estoy buscando Samsung S22 Ultra de 256 GB, ¿qué me recomiendan?",
        "context": {"city": "Choloma"},
    }
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "groq_pilot.py"), "--live"],
            input=json.dumps(sample), text=True,
            env=env, capture_output=True, timeout=30, check=False
        )
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, ValueError) as exc:
        raise RuntimeError("Prueba de Groq no disponible; bot existente sigue intacto.") from exc
    if result.returncode != 0 or data.get("status") != "suggestion_only":
        raise RuntimeError("Proveedor Groq no validado (verifica clave, cupo y configuración).")
    assert data.get("sent_to_customer") is False
    return data["proposal"]

def main():
    if os.geteuid() != 0:
        print("Abre una terminal SSH y ejecuta: sudo python3 " + str(Path(__file__).resolve()))
        return 2
    if not sys.stdin.isatty():
        print("Por seguridad, introduce la clave únicamente en una terminal interactiva (SSH).")
        return 2
    try:
        print("Instalación segura: no se mostrará ni registrará la clave.")
        secret = getpass.getpass("Pegá tu clave API de Groq y presioná Enter: ")
        save_key(secret)
        del secret
        print("Clave guardada en el VPS con permisos 0600. El bot activo no se modifica.")
        proposal = verify(stored_key())
        print("Conexión Groq: VALIDADA. Solo sugerencia interna (NO enviada a WhatsApp).")
        print("Propuesta de prueba: " + proposal["suggested_reply"][:250])
    except (RuntimeError, ValueError, OSError) as exc:
        print(str(exc))
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
