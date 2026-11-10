# FM27 Tactics Lab

A tactics board for **Football Manager 27** that reads your squad straight from your save file.

- **Tactic board:** separate in-possession and out-of-possession shapes and roles, team instructions, and a transition view.
- **Squad fit:** every player is scored against every role, using his attributes and his position ratings from the save (left and right sides included). Auto-pick finds your best XI.
- **Load from FM save:** pick a `.fm` save and the Lab reads every player's attributes, position ratings, age and CA/PA. After FM autosaves, press **Refresh from save** to update.

Everything runs on your own computer. Your save is never uploaded.

## Download

Get **FM27TacticsLab.exe** from [Releases](../../releases/latest) and double-click it. A small window opens and the Lab loads in your browser. Keep that window open while you use the Lab, and close it to quit.

Windows may warn you the first time ("Windows protected your PC") because the exe isn't code-signed. Click **More info → Run anyway**.

## Where it finds your saves

It looks in `Documents\Sports Interactive\Football Manager 27\games` (including OneDrive-redirected Documents), and in any folder FM last saved to. To use a different folder, set the environment variable `FM_SAVES_DIR`.

**Cloud saves:** Game Pass and Steam cloud saves aren't stored as normal files. In FM, save a copy to your computer and it will appear in the list.

## Run from source

```
pip install -r requirements.txt
python app/tactics_lab.py
```

## Build the exe

Every push to `main` builds `FM27TacticsLab.exe` on Windows with GitHub Actions and publishes it as a new Release (`v0.1.<build number>`).

## Notes

- In-possession role names match FM27. Out-of-possession roles are approximations.
- FM27 support in the save reader is new. If a save won't load, try a fresh copy, and update to the newest release after FM patches.
- The Assistant tab (Claude) only works when the Lab is opened inside Claude.

## Credits

Save reading uses [fmsave](https://github.com/rhiever/fmsave) by Randal S. Olson (MIT license). Not affiliated with Sports Interactive or SEGA.
