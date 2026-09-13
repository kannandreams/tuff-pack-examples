# Records demo.mp4: Claude Code reads .env, a Tuff policy denies it, and the
# same question is refused. Re-record from this directory with:  vhs demo.tape
Output demo.mp4

Require tuff
Require claude

Set Framerate 30
Set FontSize 16
Set Width 1600
Set Height 800
Set Padding 20
Set Margin 20
Set MarginFill "#12131a"
Set BorderRadius 10
Set WindowBar Colorful
Set TypingSpeed 35ms
Set CursorBlink false

Hide
Type "clear"
Enter
Show

Type "# Claude Code is asked for a secret in .env, before and after a Tuff policy."
Enter
Sleep 2s
Type "./scripts/demo.sh"
Enter

# Each gate waits for its own numbered prompt; a generic pattern would also
# match an earlier, already answered prompt and fire every gate at once.
Wait+Line@2m /Proceed with step 1\?/
Sleep 2s
Type "y"
Enter
Wait+Line@2m /Proceed with step 2\?/
Sleep 3s
Type "y"
Enter
Wait+Line@3m /Proceed with step 3\?/
Sleep 4s
Type "y"
Enter
Wait+Line@2m /Proceed with step 4\?/
Sleep 4s
Type "y"
Enter
Wait+Line@2m /Proceed with step 5\?/
Sleep 4s
Type "y"
Enter

# Claude's second answer and the closing lines, plus reading time. A fixed
# Sleep rather than Wait+Screen, which has aborted recordings at this size.
Sleep 20s
