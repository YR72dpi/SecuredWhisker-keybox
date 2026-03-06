import JsonManager


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

def set_secrets(iv: str, public: str, private: str) -> None:
    """Écrit iv, keypair.public et keypair.private en une seule opération atomique
    et passe initialized à True. Lève PermissionError si déjà initialisé,
    ou ValueError si l'un des champs est vide."""
    if get_initialized():
        raise PermissionError("Le keybox est déjà initialisé : impossible de réécrire les secrets.")
    if not iv or not public or not private:
        raise ValueError("iv, public et private doivent tous être non vides.")
    JsonManager.update_value("iv", iv)
    JsonManager.update_value("keypair.public", public)
    JsonManager.update_value("keypair.private", private)
    JsonManager.update_value("initialized", True)
