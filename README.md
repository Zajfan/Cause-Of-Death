# Cause of Death

A Python desktop crime-solving game built with `tkinter`.

## Features

- Case list with explicit case-opening flow
- Evidence viewer with smarter photo / audio / video handling
- Suspect panel
- Notes area
- Accusation screen
- Saved progress in `progress.json`

## Run

```bash
python3 app.py
```

This launches a native desktop window.

## Notes

- Photo evidence previews directly when the file is a Tk-supported image format.
- Audio and video evidence can be opened externally from the app.
- If you add real media files later, put them next to `app.py` or in an `assets/` folder.
