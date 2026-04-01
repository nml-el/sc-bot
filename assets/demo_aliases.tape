# VHS documentation: https://github.com/charmbracelet/vhs

Output assets/demo_aliases.gif

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

# Ask about gene aliases
Type "For human genes, what are the aliases for CD16 and CD161?"
Enter
Sleep 10s

# Exit gracefully
Ctrl+C
Sleep 2s
