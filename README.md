# Droite de régression & bandes ±σ (auto)

1. Crée un repo GitHub, pousse ces fichiers.
2. Settings → Pages → Deploy from branch → `main` / `(root)`.
3. Actions → « Mise à jour TTE.PA » → Run workflow (1re exécution, puis automatique chaque jour ouvré).
4. Ouvre `https://<user>.github.io/<repo>/` : l'historique se charge seul.

Test local : `pip install yfinance pandas requests && python scripts/fetch.py && python -m http.server`
