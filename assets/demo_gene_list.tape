# VHS documentation: https://github.com/charmbracelet/vhs

Output assets/demo_gene_list.gif

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

# Ask for cell type inference from a gene list
Type "What cell type do these genes suggest: ['CD79B', 'VPREB3', 'CD74', 'CD79A', 'FCER2', 'TCL1A', 'BANK1']"
Enter
Sleep 9s

# Exit gracefully
Ctrl+C
Sleep 2s
