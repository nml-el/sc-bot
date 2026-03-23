# VHS documentation: https://github.com/charmbracelet/vhs

Output assets/demo.gif

Set FontSize 15
Set Width 1200
Set Height 800
Set TypingSpeed 50ms
Set Theme "TokyoNight"
Set Padding 20
Set Margin 20

# Start the bot
Type "uv run sc-bot"
Enter
Sleep 4s

# Ask a biology question
Type "What are the key marker genes for exhausted CD8+ T cells?"
Enter

# Give the bot time to "think" and stream the response
Sleep 10s

# Ask a follow up question to show context
Type "Can you give me markers for memory B cells as well?"
Enter

# Wait for response
Sleep 8s

# Exit gracefully
Ctrl+C
Sleep 2s
