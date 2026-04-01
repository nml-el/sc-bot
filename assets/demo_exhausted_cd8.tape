# VHS documentation: https://github.com/charmbracelet/vhs

Output assets/demo_exhausted_cd8.gif

Set FontSize 15
Set Width 1200
Set Height 800
Set TypingSpeed 45ms
Set Theme "TokyoNight"
Set Padding 20
Set Margin 20

# Start the bot
Type "uv run sc-bot"
Enter
Sleep 3s
Sleep 3s

# Ask a biology question
Type "What are the key marker genes for exhausted CD8+ T cells?"
Enter
Sleep 11s

# Exit gracefully
Ctrl+C
Sleep 2s
