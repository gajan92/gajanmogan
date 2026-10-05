# kino for YouTube

A calmer, ambient watch page for YouTube, made of a userstyle and a userscript. It is built for Zen and works in any Firefox-based browser.

## What each file does

| Feature | `kino.user.css` | `kino.user.js` |
|---|---|---|
| Dark glass look, fonts, rounded player, restyled buttons and description | Yes | |
| Page tinted with the colors of the video | Paints it | Samples the video |
| Side panel with tabs for Up next, Comments and Chapters | Styles it | Builds it |
| Timeline of chapter frames under the player, with the most-replayed line | Styles it | Builds it |
| Comments sorted by the moment they mention | Styles it | Sorts them |
| Links and credits from the description as cards | Styles it | Reads the description |
| Player docks above the panel when you scroll past it | Styles it | Detects the scroll |
| End screen with three picks, Watch again and Stop here | Styles it | Adds the buttons |
| Autoplay switched off | | Yes |

The userstyle works on its own, so you get the look without the script. The script needs the userstyle, because all of its styling lives there.

## Install in Zen

### 1. The userstyle, with Stylus

1. Install Stylus: https://addons.mozilla.org/firefox/addon/styl-us/
2. Open the Stylus manager and choose **Write new style**.
3. Paste everything from `kino.user.css` and save. Stylus reads the header and names the style "kino for YouTube".

If the file is on GitHub, opening its **Raw** link also works. Stylus then offers to install it and can check for updates.

### 2. The userscript, with Violentmonkey

1. Install Violentmonkey: https://addons.mozilla.org/firefox/addon/violentmonkey/
2. Open the Violentmonkey dashboard, click **+** and choose **New**.
3. Replace the template with everything from `kino.user.js` and save.
4. Reload YouTube and open any video.

### Without Stylus: userContent.css

Zen can also load the style straight from your profile:

1. Open `about:support`, find **Profile Folder** and click **Open Folder**.
2. Create a folder called `chrome` there if it is missing, and save `kino.user.css` inside it as `userContent.css`.
3. In `about:config`, make sure `toolkit.legacyUserProfileCustomizations.stylesheets` is `true`. Zen usually has it on already.
4. Restart Zen.

Stylus is easier to edit and update, so use this route only if you prefer no extensions.

## Settings

The script's settings sit at the top of `kino.user.js`:

| Setting | Default | What it does |
|---|---|---|
| `autoplayOff` | `true` | Switches YouTube's autoplay off once each time YouTube loads. The switch at the bottom of the panel turns it back on. |
| `dockOnScroll` | `true` | Moves the player above the panel when you scroll past it. |
| `ambient` | `true` | Tints the page with colors from the video. Turn it off if your computer runs warm. |
| `defaultTab` | `'next'` | The tab the panel opens on the first time: `'next'`, `'comments'` or `'chapters'`. After that it remembers your last tab. |
| `scenesWithoutChapters` | `8` | How many equal parts the timeline shows when a video has no chapters. |

Colors, sizes and fonts are CSS variables at the top of `kino.user.css`. `--kino-panel-w` sets the panel width, and `--kino-accent` is the fallback accent color.

## Known limits

- Sorting by moment only covers comments that have loaded. Scroll the Comments tab to load more.
- Videos without chapters show equal parts, with frames from YouTube's seek-bar previews.
- Live streams skip the timeline.
- If the browser refuses to read frames from the video, the page keeps a fixed tint.
- Ads still play. This changes the layout, not what YouTube serves.
- Shorts, the home page and search results keep YouTube's normal look.

## When something breaks

YouTube changes its page often and shows different versions to different accounts. If a part stops working:

1. Turn Violentmonkey off for a moment and reload. If the problem goes away, it is in the script. If it stays, it is in the style.
2. Right-click the broken part, choose **Inspect**, and copy the highlighted element's tag name and its `id` or `class`.
3. Send that along with a screenshot.
