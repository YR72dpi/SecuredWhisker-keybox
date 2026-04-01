import JsonManager
import hashlib


def _md5(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()

def get_initialized() -> bool:
    data = JsonManager.get_all_json()
    return data.get("initialized", False)

def get_secrets() -> dict:
    """Retourne iv, keypair.public et keypair.private en une seule lecture."""
    data = JsonManager.get_all_json()
    keypair = data.get("keypair", {"public": None, "private": None})
    return {
        "initialized": data.get("initialized", False),
        "iv": data.get("iv", None),
        "public": keypair.get("public", None),
        "private": keypair.get("private", None),
    }

def set_iv(iv: str) -> None:
    if not iv:
        raise ValueError("iv ne doit pas être vide.")
    JsonManager.update_value("iv", iv)

def set_public(public: str) -> None:
    if not public:
        raise ValueError("public ne doit pas être vide.")
    current = get_secrets().get("public") or ""
    JsonManager.update_value("keypair.public", current + public)

def set_private(private: str) -> None:
    if not private:
        raise ValueError("private ne doit pas être vide.")
    current = get_secrets().get("private") or ""
    JsonManager.update_value("keypair.private", current + private)

def set_initialized(value: bool) -> None:
    JsonManager.update_value("initialized", value)

def set_hash_iv(iv: str) -> None:
    if not iv:
        raise ValueError("hash.iv ne doit pas être vide.")
    JsonManager.update_value("hash.iv", iv)

def set_hash_public(public: str) -> None:
    if not public:
        raise ValueError("hash.keypair.public ne doit pas être vide.")
    JsonManager.update_value("hash.keypair.public", public)

def set_hash_private(private: str) -> None:
    if not private:
        raise ValueError("hash.keypair.private ne doit pas être vide.")
    JsonManager.update_value("hash.keypair.private", private)

def verify_iv() -> bool:
    data = JsonManager.get_all_json()
    iv = data.get("iv")
    hashedIv = data.get("hash", {}).get("iv")
    if not iv or not hashedIv:
        return False
    return _md5(iv) == hashedIv

def verify_public() -> bool:
    data = JsonManager.get_all_json()
    public = data.get("keypair", {}).get("public")
    hashedPublic = data.get("hash", {}).get("keypair", {}).get("public")
    if not public or not hashedPublic:
        return False
    return _md5(public) == hashedPublic

def verify_private() -> bool:
    data = JsonManager.get_all_json()
    private = data.get("keypair", {}).get("private")
    hashedPrivate = data.get("hash", {}).get("keypair", {}).get("private")
    if not private or not hashedPrivate:
        return False
    return _md5(private) == hashedPrivate

