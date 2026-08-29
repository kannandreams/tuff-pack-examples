# Records demo.mp4: publish a Tuff capability pack, then consume it in a
# clean container. Re-record with:  vhs demo.tape
Output demo.mp4

Require tuff
Require docker
Require gh

# 30fps rather than the default: fewer frames for the recorder to capture.
Set Framerate 30
Set FontSize 16
# 1600x800 = 149 columns x 33 rows at this font size. tuff's capability table
# is 124 columns wide, so a narrower frame wraps its borders mid-row.
Set Width 1600
Set Height 800
Set Padding 20
Set Margin 20
Set MarginFill "#12131a"
Set BorderRadius 10
Set WindowBar Colorful
Set TypingSpeed 35ms
# A blinking cursor repaints the screen twice a second for the whole run.
Set CursorBlink false

Hide
Type "clear"
Enter
Show

Type "# This demo publishes a Tuff capability pack, then consumes it in a clean runtime."
Enter
Sleep 2s
Type "# Host: build and publish the pack. Container: pull, verify, install, and run it."
Enter
Sleep 2s
Type "uv run python -m runtime.demo"
Enter

# Each prompt names its own step ("Proceed with step 4?"), so a gate can only
# match its own prompt. A generic /Proceed/ also matches the previous, already
# answered prompt line, which fires every gate at once and leaves the queued
# keystrokes stranded before the container ever reads stdin.

# Host steps: discover, install, list/check, pack build, publish, image, run
Wait+Line@10m /Proceed with step 1\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with step 2\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with step 3\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with step 4\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with step 5\?/
Sleep 3s
Type "y"
Enter

# Hold on the GitHub Packages panel the push produced
Sleep 6s
Wait+Line@10m /Proceed with step 6\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with step 7\?/
Sleep 3s
Type "y"
Enter

# Container steps: init, pull/verify, install pack, list/check, run the agent
Wait+Line@10m /Proceed with runtime step 1\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with runtime step 2\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with runtime step 3\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with runtime step 4\?/
Sleep 3s
Type "y"
Enter
Wait+Line@10m /Proceed with runtime step 5\?/
Sleep 3s
Type "y"
Enter

# A fixed Sleep, not Wait+Screen: Wait+Line gates match reliably, but every
# tape using Wait+Screen /Demo complete/ has aborted the recording at this
# frame size instead of producing a file. The agent replays a cached summary,
# so the tail is ~3s of output plus reading time.
Sleep 18s
