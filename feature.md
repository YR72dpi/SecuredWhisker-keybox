- Installation de sw-keybox sur raspberry pi 0 2wh
- Connexion SW à sw-keybox via pin de connexion bluetooth
- Enregistrement de la clé privée du navigateur au SW-key box :
    - Utilisateur définit un mot de passe numérique (A) 
    - Clé privée chiffrée en AES avec "A"
    - Clé privée chiffrée transmise et enregistrée dans sw-keybox
    - Vérification de la clé privée chiffrée
    - "A" chiffré avec 10 mots
    - Ces 10 mots sont présentés à l'utilisateur
    - Validation de l'utilisateur quand ces 10 mots sont enregistrés
    - Chiffrement de "A" avec concaténation de ces 10 mots
    - Enregistrement de "A" chiffré avec les 10 mots 
    - Vérifications
    - Suppression de la clé privée du localStorage

## Diagramme de flux - Configuration SW-KeyBox

```mermaid
graph TD
    A[Installation SW-KeyBox sur Raspberry Pi] --> B[Connexion Bluetooth via PIN]
    B --> C[Utilisateur définit mot de passe numérique A]
    
    subgraph "Chiffrement et transmission"
        C --> D[Chiffrement clé privée avec A en AES]
        D --> E[Transmission clé privée chiffrée vers SW-KeyBox]
        E --> F[Enregistrement dans SW-KeyBox]
        F --> G[Vérification clé privée chiffrée]
    end
    
    subgraph "Protection du mot de passe"
        G --> H[Génération de 10 mots aléatoires]
        H --> I[Présentation des 10 mots à l'utilisateur]
        I --> J{Utilisateur valide les 10 mots ?}
        J -->|Non| I
        J -->|Oui| K[Concaténation des 10 mots]
        K --> L[Chiffrement de A avec les 10 mots concaténés]
        L --> M[Enregistrement de A chiffré dans SW-KeyBox]
    end
    
    subgraph "Finalisation"
        M --> N[Vérifications finales]
        N --> O{Tout est correct ?}
        O -->|Non| G
        O -->|Oui| P[Suppression clé privée du localStorage]
        P --> Q[Configuration terminée]
    end
    
    style A fill:#e1f5fe
    style Q fill:#c8e6c9
    style J fill:#fff3e0
    style O fill:#fff3e0
```
